from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import (
    roc_curve,
    roc_auc_score,
    accuracy_score,
    classification_report,
)
from sklearn.inspection import permutation_importance
import os

app = Flask(__name__)
CORS(app)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "final model", "models")

model = joblib.load(os.path.join(MODEL_DIR, "hit_detector.pkl"))
scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
meta = joblib.load(os.path.join(MODEL_DIR, "meta.pkl"))

feature_names = meta["feature_names"]
THRESHOLD = meta["t_balanced_f1"]
HIT_POP_THRESHOLD = meta["hit_threshold"]
TARGET_NAMES = ["Not a Hit", "Hit"]

RAW_FEATURES = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "explicit",
    "time_signature",
    "duration_ms",
]

batch_state = {"y_true": None, "y_proba": None, "X_scaled": None}
metrics_cache = None


def clean_report(report):
    return {
        k: {mk: round(mv, 4) if isinstance(mv, float) else mv for mk, mv in v.items()}
        for k, v in report.items()
        if isinstance(v, dict)
    }


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    feat_df = pd.DataFrame(0, index=df.index, columns=feature_names)
    for f in RAW_FEATURES:
        if f in df.columns:
            feat_df[f] = df[f].values
    if "key" in df.columns:
        for i in range(12):
            feat_df[f"key_{i}"] = (df["key"] == i).astype(int).values
    if "mode" in df.columns:
        for i in range(2):
            feat_df[f"mode_{i}"] = (df["mode"] == i).astype(int).values
    return feat_df


def build_single_row(raw: dict) -> pd.DataFrame:
    row = {f: [float(raw[f])] for f in RAW_FEATURES}
    row["key"] = [int(raw["key"])]
    row["mode"] = [int(raw["mode"])]
    return build_feature_matrix(pd.DataFrame(row))


def invalidate_metrics():
    global metrics_cache
    metrics_cache = None


@app.route("/predict_single", methods=["POST"])
def predict_single():
    data = request.json

    df = build_single_row(data)
    X_scaled = scaler.transform(df)

    proba = model.predict_proba(X_scaled)[0, 1]
    is_hit = bool(proba >= THRESHOLD)

    return jsonify(
        {
            "gb_probability": round(float(proba), 4),
            "gb_is_hit": is_hit,
        }
    )


@app.route("/predict_batch", methods=["POST"])
def predict_batch():
    file = request.files["file"]

    df = pd.read_csv(file)

    df = df.dropna(subset=["name"])
    df = df[df["duration_ms"] > 0]
    df = df[df["tempo"] > 0]

    names = df["name"].tolist()
    has_popularity = "popularity" in df.columns
    if has_popularity:
        y_true = (df["popularity"] > HIT_POP_THRESHOLD).astype(int).values

    feat_df = build_feature_matrix(df)

    X_scaled = scaler.transform(feat_df)

    probas = model.predict_proba(X_scaled)[:, 1]

    if has_popularity:
        batch_state["y_true"] = y_true
        batch_state["y_proba"] = probas
        batch_state["X_scaled"] = X_scaled
        invalidate_metrics()

    results = [
        {
            "name": n,
            "gb_probability": round(float(p), 4),
            "gb_is_hit": bool(p >= THRESHOLD),
        }
        for n, p in zip(names, probas)
    ]
    return jsonify({"results": results, "has_metrics": has_popularity})


@app.route("/get_metrics", methods=["GET"])
def get_metrics():
    global metrics_cache

    if batch_state["y_true"] is None:
        return jsonify(
            {"error": "No batch prediction with popularity data available"}
        ), 400

    if metrics_cache is not None:
        return jsonify(metrics_cache)

    y_true = batch_state["y_true"]
    y_proba = batch_state["y_proba"]

    fpr, tpr, _ = roc_curve(y_true, y_proba)
    auc = roc_auc_score(y_true, y_proba)

    result = permutation_importance(
        model, batch_state["X_scaled"], y_true, n_repeats=5, random_state=42, n_jobs=-1
    )
    importance = {
        name: round(float(score), 4)
        for name, score in zip(feature_names, result.importances_mean)
    }

    # Classification report and accuracy
    y_pred_gb = (y_proba >= THRESHOLD).astype(int)

    gb_accuracy = round(float(accuracy_score(y_true, y_pred_gb)), 4)

    gb_report = classification_report(
        y_true, y_pred_gb, target_names=TARGET_NAMES, output_dict=True, zero_division=0
    )

    gb_auc = round(float(auc), 4)

    metrics_cache = {
        "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "auc": gb_auc},
        "feature_importance": importance,
        "threshold": round(float(THRESHOLD), 2),
        "gb_holdout": {
            "accuracy": gb_accuracy,
            "roc_auc": gb_auc,
            "report": clean_report(gb_report),
        },
    }
    return jsonify(metrics_cache)


VALIDATION_CSV = os.path.join(
    os.path.dirname(__file__), "..", "datasets", "validation_2020.csv"
)


@app.route("/run_validation", methods=["POST"])
def run_validation():
    df = pd.read_csv(VALIDATION_CSV)

    names = df["name"].tolist()
    artists = df["artists"].tolist()
    y_true = (df["popularity"] > HIT_POP_THRESHOLD).astype(int).values

    feat_df = build_feature_matrix(df)

    X_scaled = scaler.transform(feat_df)

    probas = model.predict_proba(X_scaled)[:, 1]

    batch_state["y_true"] = y_true
    batch_state["y_proba"] = probas
    batch_state["X_scaled"] = X_scaled
    invalidate_metrics()

    results = [
        {
            "name": n,
            "artists": a,
            "popularity": int(p),
            "gb_probability": round(float(pr), 4),
            "gb_is_hit": bool(pr >= THRESHOLD),
            "actual_hit": bool(int(p) > HIT_POP_THRESHOLD),
        }
        for n, a, p, pr in zip(names, artists, df["popularity"], probas)
    ]
    return jsonify({"results": results, "total": len(results), "has_metrics": True})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
