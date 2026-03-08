from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import roc_curve, roc_auc_score
from sklearn.inspection import permutation_importance
import os
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hit-predictor")

app = Flask(__name__)
CORS(app)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "final model", "models")

log.info("Loading model artifacts...")
t0 = time.time()
model = joblib.load(os.path.join(MODEL_DIR, "hit_detector.pkl"))
log.info("  hit_detector.pkl loaded (%.2fs)", time.time() - t0)
t0 = time.time()
scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
log.info("  scaler.pkl loaded (%.2fs)", time.time() - t0)
t0 = time.time()
meta = joblib.load(os.path.join(MODEL_DIR, "meta.pkl"))
log.info("  meta.pkl loaded (%.2fs)", time.time() - t0)

feature_names = meta["feature_names"]
THRESHOLD = meta["t_balanced_f1"]
HIT_POP_THRESHOLD = meta["hit_threshold"]
log.info("Ready — %d features, threshold=%.2f, hit_pop=%d", len(feature_names), THRESHOLD, HIT_POP_THRESHOLD)

RAW_FEATURES = [
    "danceability", "energy", "loudness", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo", "explicit",
    "time_signature", "duration_ms",
]

# Store batch results for metrics endpoint; metrics_cache avoids recomputing permutation importance
batch_state = {"y_true": None, "y_proba": None, "X_scaled": None}
metrics_cache = None


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build a feature matrix from a DataFrame with raw columns (key, mode, etc.)."""
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
    """Build a 1-row DataFrame from a JSON dict with raw feature values."""
    row = {f: [float(raw[f])] for f in RAW_FEATURES}
    row["key"] = [int(raw["key"])]
    row["mode"] = [int(raw["mode"])]
    return build_feature_matrix(pd.DataFrame(row))


def invalidate_metrics():
    global metrics_cache
    metrics_cache = None


@app.route("/predict_single", methods=["POST"])
def predict_single():
    t0 = time.time()
    data = request.json
    log.info("POST /predict_single — key=%s, mode=%s, tempo=%s", data.get("key"), data.get("mode"), data.get("tempo"))

    df = build_single_row(data)
    log.info("  Feature vector built")

    X_scaled = scaler.transform(df)
    log.info("  Scaled")

    proba = model.predict_proba(X_scaled)[0, 1]
    is_hit = bool(proba >= THRESHOLD)
    log.info("  Prediction: %.4f (%s) — %.0fms", proba, "HIT" if is_hit else "miss", (time.time() - t0) * 1000)

    return jsonify({"probability": round(float(proba), 4), "is_hit": is_hit})


@app.route("/predict_batch", methods=["POST"])
def predict_batch():
    t0 = time.time()
    file = request.files["file"]
    log.info("POST /predict_batch — file: %s", file.filename)

    df = pd.read_csv(file)
    log.info("  CSV loaded: %d rows, %d columns", len(df), len(df.columns))

    before = len(df)
    df = df.dropna(subset=["name"])
    df = df[df["duration_ms"] > 0]
    df = df[df["tempo"] > 0]
    log.info("  Cleaned: %d → %d rows (%d dropped)", before, len(df), before - len(df))

    names = df["name"].tolist()
    has_popularity = "popularity" in df.columns
    if has_popularity:
        y_true = (df["popularity"] > HIT_POP_THRESHOLD).astype(int).values
        log.info("  Popularity column found — %d hits, %d non-hits", y_true.sum(), len(y_true) - y_true.sum())

    log.info("  Building feature matrix...")
    feat_df = build_feature_matrix(df)
    log.info("  Feature matrix: %d x %d", *feat_df.shape)

    log.info("  Scaling features...")
    X_scaled = scaler.transform(feat_df)

    log.info("  Running predictions...")
    probas = model.predict_proba(X_scaled)[:, 1]
    n_hits = int((probas >= THRESHOLD).sum())
    log.info("  Predicted %d hits out of %d tracks (%.1f%%)", n_hits, len(probas), n_hits / len(probas) * 100)

    if has_popularity:
        batch_state["y_true"] = y_true
        batch_state["y_proba"] = probas
        batch_state["X_scaled"] = X_scaled
        invalidate_metrics()

    results = [
        {"name": n, "probability": round(float(p), 4), "is_hit": bool(p >= THRESHOLD)}
        for n, p in zip(names, probas)
    ]
    log.info("  Done — %.0fms total", (time.time() - t0) * 1000)
    return jsonify({"results": results, "has_metrics": has_popularity})


@app.route("/get_metrics", methods=["GET"])
def get_metrics():
    global metrics_cache
    t0 = time.time()
    log.info("GET /get_metrics")

    if batch_state["y_true"] is None:
        log.warning("  No batch data available")
        return jsonify({"error": "No batch prediction with popularity data available"}), 400

    if metrics_cache is not None:
        log.info("  Returning cached metrics — %.0fms", (time.time() - t0) * 1000)
        return jsonify(metrics_cache)

    y_true = batch_state["y_true"]
    y_proba = batch_state["y_proba"]

    log.info("  Computing ROC curve (%d samples)...", len(y_true))
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    auc = roc_auc_score(y_true, y_proba)
    log.info("  AUC = %.4f", auc)

    log.info("  Computing permutation importance (5 repeats)... this may take a moment")
    t1 = time.time()
    result = permutation_importance(model, batch_state["X_scaled"], y_true, n_repeats=5, random_state=42, n_jobs=-1)
    importance = {name: round(float(score), 4) for name, score in zip(feature_names, result.importances_mean)}
    log.info("  Permutation importance computed — %.1fs", time.time() - t1)

    top3 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
    log.info("  Top features: %s", ", ".join(f"{n}={v}" for n, v in top3))

    metrics_cache = {
        "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "auc": round(float(auc), 4)},
        "feature_importance": importance,
    }
    log.info("  Done — %.0fms total", (time.time() - t0) * 1000)
    return jsonify(metrics_cache)


VALIDATION_CSV = os.path.join(os.path.dirname(__file__), "..", "datasets", "validation_2020.csv")


@app.route("/run_validation", methods=["POST"])
def run_validation():
    """Run the model on the pre-built 2020 validation set."""
    t0 = time.time()
    log.info("POST /run_validation")

    log.info("  Loading validation CSV...")
    df = pd.read_csv(VALIDATION_CSV)
    log.info("  Loaded %d tracks from 2020 validation set", len(df))

    names = df["name"].tolist()
    artists = df["artists"].tolist()
    y_true = (df["popularity"] > HIT_POP_THRESHOLD).astype(int).values
    log.info("  Ground truth: %d hits, %d non-hits", y_true.sum(), len(y_true) - y_true.sum())

    log.info("  Building feature matrix...")
    feat_df = build_feature_matrix(df)

    log.info("  Scaling %d x %d feature matrix...", *feat_df.shape)
    X_scaled = scaler.transform(feat_df)

    log.info("  Running predictions...")
    probas = model.predict_proba(X_scaled)[:, 1]

    batch_state["y_true"] = y_true
    batch_state["y_proba"] = probas
    batch_state["X_scaled"] = X_scaled
    invalidate_metrics()

    preds = (probas >= THRESHOLD).astype(int)
    correct = int((preds == y_true).sum())
    accuracy = correct / len(y_true) * 100
    log.info("  Predicted %d hits out of %d tracks", int(preds.sum()), len(preds))
    log.info("  Accuracy: %.1f%% (%d/%d correct)", accuracy, correct, len(y_true))

    results = [
        {"name": n, "artists": a, "popularity": int(p),
         "probability": round(float(pr), 4), "is_hit": bool(pr >= THRESHOLD),
         "actual_hit": bool(int(p) > HIT_POP_THRESHOLD)}
        for n, a, p, pr in zip(names, artists, df["popularity"], probas)
    ]
    log.info("  Done — %.0fms total", (time.time() - t0) * 1000)
    return jsonify({"results": results, "total": len(results), "has_metrics": True})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
