"""
FIFA WC 2034 — Model Microservice (port 8001)
Loads ONLY LightGBM + TensorFlow — no YOLO, no PyTorch.
The main api.py calls this via HTTP to get predictions.
"""

import os
import numpy as np
import joblib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MODELS_DIR  = "models"
LGBM_MODEL  = os.path.join(MODELS_DIR, "lgbm_forecast.pkl")
LGBM_SCALER = os.path.join(MODELS_DIR, "lgbm_scaler.pkl")
TF_MODEL    = os.path.join(MODELS_DIR, "tf_density_classifier.keras")
TF_SCALER   = os.path.join(MODELS_DIR, "tf_scaler.pkl")
TF_ENCODER  = os.path.join(MODELS_DIR, "tf_label_encoder.pkl")

# ── Load models ───────────────────────────────────────────────────
lgbm_model, lgbm_scaler = None, None
tf_model, tf_scaler, tf_encoder = None, None, None

if os.path.exists(LGBM_MODEL):
    print("[model-server] Loading LightGBM …")
    lgbm_model  = joblib.load(LGBM_MODEL)
    lgbm_scaler = joblib.load(LGBM_SCALER)
    print("[model-server] LightGBM ready.")
else:
    print("[model-server] LightGBM not found — run train.py first.")

if os.path.exists(TF_MODEL):
    print("[model-server] Loading TensorFlow …")
    import tensorflow as tf
    tf_model   = tf.keras.models.load_model(TF_MODEL)
    tf_scaler  = joblib.load(TF_SCALER)
    tf_encoder = joblib.load(TF_ENCODER)
    print("[model-server] TensorFlow ready.")
else:
    print("[model-server] TensorFlow not found — run train.py first.")

# ── App ───────────────────────────────────────────────────────────
app = FastAPI(title="Crowd AI Model Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Features(BaseModel):
    count:        float
    density:      float
    time_of_day:  float
    cx_std:       float
    cy_std:       float
    avg_box_area: float


@app.get("/health")
def health():
    return {
        "status":      "ok",
        "lgbm_loaded": lgbm_model is not None,
        "tf_loaded":   tf_model   is not None,
    }


@app.post("/predict")
def predict(f: Features):
    X = np.array([[f.count, f.density, f.time_of_day,
                   f.cx_std, f.cy_std, f.avg_box_area]])

    # LightGBM — 15-min density forecast
    if lgbm_model is not None:
        Xs = lgbm_scaler.transform(X)
        pred_density = float(round(lgbm_model.predict(Xs)[0], 1))
    else:
        pred_density = round(min(9.0, f.density + 0.6), 1)

    # TensorFlow — risk classification
    if tf_model is not None:
        Xs2 = tf_scaler.transform(X).astype("float32")
        probs = tf_model.predict(Xs2, verbose=0)[0]
        risk  = str(tf_encoder.inverse_transform([int(np.argmax(probs))])[0])
    else:
        if f.count <= 10:   risk = "Normal"
        elif f.count <= 25: risk = "Busy"
        else:               risk = "Critical"

    return {"predictedDensity": pred_density, "predictedRisk": risk}
