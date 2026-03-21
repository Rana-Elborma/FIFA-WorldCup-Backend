from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import os, time, threading, random
from collections import deque

# --------------------
# CONFIG (YOUR PATHS)
# --------------------
IMAGE_FOLDER = "/Users/ranamahmoud/Downloads/People Detection.v11-rf-detr-medium.yolov8/test/images"
LABEL_FOLDER = "/Users/ranamahmoud/Downloads/People Detection.v11-rf-detr-medium.yolov8/test/labels"

MODEL_PATH = "yolov8n.pt"   # if you have best.pt, replace with "best.pt"
CONF = 0.35
UPDATE_EVERY_SEC = 3

# thresholds for demo alert level
NORMAL_MAX = 10
BUSY_MAX = 25

def risk_from_count(count: int) -> str:
    if count <= NORMAL_MAX:
        return "Normal"
    if count <= BUSY_MAX:
        return "Busy"
    return "Critical"

def density_from_count(count: int) -> float:
    return round(min(7.5, count / 12.0), 1)

def count_lines(path: str) -> int:
    try:
        with open(path, "r") as f:
            return sum(1 for line in f if line.strip())
    except FileNotFoundError:
        return 0


app = FastAPI(
    title="FIFA WC 2034 Crowd AI Backend",
    version="1.0.0",
    description="YOLOv8-based crowd detection + density metrics + 15-minute forecasting"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5178",
        "http://127.0.0.1:5178",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO(MODEL_PATH)

image_files = sorted([
    os.path.join(IMAGE_FOLDER, f)
    for f in os.listdir(IMAGE_FOLDER)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
])

latest = {
    "timestamp": "",
    "image": "",
    "peoplePred": 0,
    "peopleGT": 0,
    "avgDensity": 0.0,
    "riskLevel": "Normal",
    "activeIncidents": 0,
    "accuracy": 0.0
}

history = deque(maxlen=30)

def compute_accuracy(pred: int, gt: int) -> float:
    if gt <= 0:
        return 1.0 if pred == 0 else 0.0
    err = abs(pred - gt)
    return round(max(0.0, 1.0 - (err / gt)), 2)

def loop():
    global latest
    while True:
        if not image_files:
            time.sleep(1)
            continue

        # ✅ RANDOM IMAGE SELECTION (instead of sequential idx)
        img_path = random.choice(image_files)
        print(f"Selected image: {os.path.basename(img_path)}")

        base = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(LABEL_FOLDER, base + ".txt")

        gt_people = count_lines(label_path)

        results = model.predict(source=img_path, conf=CONF, verbose=False)
        boxes = results[0].boxes
        cls = boxes.cls.tolist() if boxes is not None else []

        # NOTE: for yolov8n.pt (COCO), person class = 0
        pred_people = sum(1 for c in cls if int(c) == 0)

        risk = risk_from_count(pred_people)
        density = density_from_count(pred_people)

        incidents = 0
        if risk == "Busy":
            incidents = 1
        elif risk == "Critical":
            incidents = 3

        acc = compute_accuracy(pred_people, gt_people)
        timestamp = time.strftime("%H:%M:%S")

        latest = {
            "timestamp": timestamp,
            "image": os.path.basename(img_path),
            "peoplePred": pred_people,
            "peopleGT": gt_people,
            "avgDensity": density,
            "riskLevel": risk,
            "activeIncidents": incidents,
            "accuracy": acc
        }

        pred_density_15 = round(min(9.0, density + 0.6), 1)

        history.append({
            "t": timestamp,
            "density": density,
            "predDensity15": pred_density_15,
            "peoplePred": pred_people,
            "peopleGT": gt_people
        })

        time.sleep(UPDATE_EVERY_SEC)

threading.Thread(target=loop, daemon=True).start()

@app.get("/api/v1/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "crowd-ai-backend"}

@app.get("/api/v1/metrics/latest", tags=["Metrics"])
def metrics_latest():
    return latest

@app.get("/api/v1/metrics/history", tags=["Metrics"])
def metrics_history():
    return list(history)

@app.get("/api/v1/predictions/15min", tags=["Predictions"])
def prediction_15min():
    if len(history) == 0:
        return {"forecastHorizon": "15 minutes", "predictedDensity": 0.0, "predictedRisk": "Normal"}
    last = history[-1]
    return {
        "forecastHorizon": "15 minutes",
        "predictedDensity": last["predDensity15"],
        "predictedRisk": "Critical" if last["predDensity15"] >= 5.0 else "Busy" if last["predDensity15"] >= 3.0 else "Normal"
    }