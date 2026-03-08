"""
Build the 2020 validation set CSV using the exact same cleaning
pipeline from binary_2020_7_modelz.ipynb.
"""
import pandas as pd
import os

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "datasets", "validation_2020.csv")


def build():
    tracks = pd.read_csv(os.path.join(DATASETS_DIR, "tracks.csv"))
    tracks = tracks.dropna(subset=["name"])
    tracks = tracks.sort_values("popularity", ascending=False)
    tracks = tracks.drop_duplicates(subset=["name", "id_artists"], keep="first")
    tracks = tracks[
        (tracks["duration_ms"] > 0)
        & (tracks["tempo"] > 0)
        & (tracks["time_signature"] > 0)
        & (tracks["popularity"] > 0)
    ]
    tracks["release_date"] = pd.to_datetime(tracks["release_date"], format="mixed")
    tracks["year"] = tracks["release_date"].dt.year
    tracks = tracks[tracks["year"] >= 1950]
    tracks = tracks[
        (tracks["release_date"] >= "2010-01-01")
        & (tracks["release_date"] <= "2020-12-31")
    ]

    validation = tracks[tracks["year"] == 2020].copy()

    # Keep only columns needed by the frontend/backend
    keep_cols = [
        "name", "artists", "popularity", "danceability", "energy", "loudness",
        "speechiness", "acousticness", "instrumentalness", "liveness", "valence",
        "tempo", "explicit", "time_signature", "duration_ms", "key", "mode",
    ]
    validation = validation[keep_cols]
    validation.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(validation)} rows to {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    build()
