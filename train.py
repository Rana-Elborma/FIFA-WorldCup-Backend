"""
Training pipeline for FIFA WC 2034 Crowd Management System

Run as:  python train.py
Internally splits into two subprocesses so YOLO/PyTorch exits completely
before LightGBM/TensorFlow load (prevents OpenMP segfault on Apple Silicon).
"""

import os
import sys

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
VIDEO_FOLDER = "/Users/ranamahmoud/Downloads/Stadiums videos "
MODEL_PATH   = "yolo11n.pt"
FRAME_SKIP   = 30
CONF         = 0.15
DEVICE       = "cpu"
NORMAL_MAX   = 10
BUSY_MAX     = 25
MODELS_DIR   = "models"


# ══════════════════════════════════════════════════════════════════
# PHASE 1 — Feature extraction with YOLO  (own subprocess)
# ══════════════════════════════════════════════════════════════════
def phase_extract():
    import cv2
    import numpy as np
    import pandas as pd
    from ultralytics import YOLO

    os.makedirs(MODELS_DIR, exist_ok=True)

    def risk_label(count):
        if count <= NORMAL_MAX: return "Normal"
        if count <= BUSY_MAX:   return "Busy"
        return "Critical"

    def density_from_count(count):
        return round(min(7.5, count / 12.0), 1)

    print("\n[1/3] Loading YOLO model …", flush=True)
    model = YOLO(MODEL_PATH)

    videos = sorted([
        os.path.join(VIDEO_FOLDER, f)
        for f in os.listdir(VIDEO_FOLDER)
        if f.lower().endswith(".mp4")
    ])
    print(f"      Found {len(videos)} videos", flush=True)

    all_records = []
    for i, vp in enumerate(videos, 1):
        print(f"      Processing [{i}/{len(videos)}] {os.path.basename(vp)} …", flush=True)
        cap = cv2.VideoCapture(vp)
        if not cap.isOpened():
            print(f"        [!] Cannot open", flush=True)
            continue

        fps        = cap.get(cv2.CAP_PROP_FPS) or 25
        total      = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_area = max(1, width * height)
        records    = []
        fi         = 0

        while fi < total:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ret, frame = cap.read()
            if not ret:
                break

            results = model.predict(source=frame, conf=CONF, verbose=False,
                                    classes=[0], device=DEVICE)
            boxes   = results[0].boxes
            xyxy    = boxes.xyxy.tolist() if boxes is not None else []
            count   = len(xyxy)
            density = density_from_count(count)

            centres = [(0.5*(x1+x2), 0.5*(y1+y2)) for x1,y1,x2,y2 in xyxy]
            cx_std  = float(np.std([c[0] for c in centres])) if centres else 0.0
            cy_std  = float(np.std([c[1] for c in centres])) if centres else 0.0
            avg_box_area = 0.0
            if xyxy:
                areas = [(x2-x1)*(y2-y1) for x1,y1,x2,y2 in xyxy]
                avg_box_area = float(np.mean(areas)) / frame_area

            time_of_day = (fi / max(1, total)) * 12 + 8

            records.append({
                "frame_idx":    fi,
                "time_s":       fi / max(1, fps),
                "time_of_day":  round(time_of_day, 2),
                "count":        count,
                "density":      density,
                "cx_std":       cx_std,
                "cy_std":       cy_std,
                "avg_box_area": avg_box_area,
                "risk":         risk_label(count),
            })
            fi += FRAME_SKIP

        cap.release()
        all_records.extend(records)
        print(f"        → {len(records)} frames extracted", flush=True)

    df = pd.DataFrame(all_records)
    csv_path = os.path.join(MODELS_DIR, "dataset.csv")
    df.to_csv(csv_path, index=False)
    print(f"      Dataset saved — {len(df)} rows → {csv_path}", flush=True)


# ══════════════════════════════════════════════════════════════════
# PHASE 2 — Model training  (own subprocess, no YOLO in memory)
# ══════════════════════════════════════════════════════════════════
def phase_train():
    import numpy as np
    import pandas as pd
    import joblib
    import lightgbm as lgb
    from tensorflow import keras
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split

    csv_path = os.path.join(MODELS_DIR, "dataset.csv")
    df = pd.read_csv(csv_path)
    print(f"\n      Loaded dataset: {len(df)} rows", flush=True)

    features = ["count", "density", "time_of_day", "cx_std", "cy_std", "avg_box_area"]

    # ── LightGBM ──────────────────────────────────────────────────
    print("\n[2/3] Training LightGBM forecasting model …", flush=True)
    HORIZON = 20
    dfl = df.copy().reset_index(drop=True)
    dfl["target_density"] = dfl["density"].shift(-HORIZON)
    dfl.dropna(inplace=True)

    X = dfl[features].values
    y = dfl["target_density"].values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler_lgb = StandardScaler()
    X_train = scaler_lgb.fit_transform(X_train)
    X_test  = scaler_lgb.transform(X_test)

    lgb_model = lgb.LGBMRegressor(
        n_estimators=300, learning_rate=0.05,
        max_depth=6, num_leaves=31, random_state=42,
    )
    lgb_model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],
                  callbacks=[lgb.early_stopping(30, verbose=False),
                             lgb.log_evaluation(50)])

    mae = float(np.mean(np.abs(lgb_model.predict(X_test) - y_test)))
    print(f"      LightGBM MAE: {mae:.4f}", flush=True)

    joblib.dump(lgb_model, os.path.join(MODELS_DIR, "lgbm_forecast.pkl"))
    joblib.dump(scaler_lgb, os.path.join(MODELS_DIR, "lgbm_scaler.pkl"))
    print("      Saved lgbm_forecast.pkl + lgbm_scaler.pkl", flush=True)

    # ── TensorFlow ────────────────────────────────────────────────
    print("\n[3/3] Training TensorFlow density classifier …", flush=True)
    le = LabelEncoder()
    dft = df.copy()
    dft["risk_enc"] = le.fit_transform(dft["risk"])

    X2 = dft[features].values.astype("float32")
    y2 = dft["risk_enc"].values
    X2_train, X2_test, y2_train, y2_test = train_test_split(
        X2, y2, test_size=0.2, random_state=42, stratify=y2)

    scaler_tf = StandardScaler()
    X2_train = scaler_tf.fit_transform(X2_train).astype("float32")
    X2_test  = scaler_tf.transform(X2_test).astype("float32")

    model = keras.Sequential([
        keras.layers.Input(shape=(len(features),)),
        keras.layers.Dense(64, activation="relu"),
        keras.layers.BatchNormalization(),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(32, activation="relu"),
        keras.layers.BatchNormalization(),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(len(le.classes_), activation="softmax"),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3),
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    model.fit(X2_train, y2_train,
              validation_data=(X2_test, y2_test),
              epochs=40, batch_size=32,
              callbacks=[keras.callbacks.EarlyStopping(patience=5,
                                                       restore_best_weights=True)],
              verbose=1)

    _, acc = model.evaluate(X2_test, y2_test, verbose=0)
    print(f"      TensorFlow accuracy: {acc:.4f}", flush=True)

    model.save(os.path.join(MODELS_DIR, "tf_density_classifier.keras"))
    joblib.dump(scaler_tf, os.path.join(MODELS_DIR, "tf_scaler.pkl"))
    joblib.dump(le,        os.path.join(MODELS_DIR, "tf_label_encoder.pkl"))
    print("      Saved tf_density_classifier.keras + tf_scaler.pkl + tf_label_encoder.pkl",
          flush=True)

    print("\n✓ Training complete. All models saved to ./models/", flush=True)


# ══════════════════════════════════════════════════════════════════
# ORCHESTRATOR — runs both phases as separate subprocesses
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if "--phase" in sys.argv:
        phase = sys.argv[sys.argv.index("--phase") + 1]
        if phase == "extract":
            phase_extract()
        elif phase == "train":
            phase_train()
        else:
            print(f"Unknown phase: {phase}")
            sys.exit(1)
    else:
        import subprocess
        python = sys.executable

        print("═" * 55)
        print("  FIFA WC 2034 — Crowd AI Training Pipeline")
        print("═" * 55)

        # Phase 1: YOLO feature extraction (isolated process)
        print("\n▶ Phase 1: Feature extraction …")
        r1 = subprocess.run([python, __file__, "--phase", "extract"],
                            check=False)
        if r1.returncode != 0:
            print(f"\n[ERROR] Feature extraction failed (exit {r1.returncode})")
            sys.exit(1)

        # Phase 2: Model training (YOLO fully gone from memory)
        print("\n▶ Phase 2: Model training …")
        r2 = subprocess.run([python, __file__, "--phase", "train"],
                            check=False)
        if r2.returncode != 0:
            print(f"\n[ERROR] Model training failed (exit {r2.returncode})")
            sys.exit(1)

        print("\n✓ All done!")
