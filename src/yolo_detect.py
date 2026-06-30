"""
src/yolo_detect.py
Runs YOLOv8 object detection on all downloaded Telegram images,
classifies them into categories, and saves results to a CSV.
"""

import csv
import re
from pathlib import Path
from datetime import datetime

from ultralytics import YOLO
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "data" / "raw" / "images"
OUTPUT_CSV = BASE_DIR / "data" / "yolo_detections.csv"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    str(LOG_DIR / f"yolo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    rotation="10 MB"
)

# Classes from the COCO dataset (what yolov8n.pt was trained on)
PERSON_CLASS = "person"
PRODUCT_CLASSES = {"bottle", "cup", "bowl", "box", "vase", "cell phone", "book"}


def classify_image(detected_classes: set) -> str:
    """
    Categorize an image based on detected object classes.

    promotional    -> person + product-like object
    product_display -> product-like object, no person
    lifestyle      -> person, no product
    other          -> neither
    """
    has_person = PERSON_CLASS in detected_classes
    has_product = bool(detected_classes & PRODUCT_CLASSES)

    if has_person and has_product:
        return "promotional"
    elif has_product and not has_person:
        return "product_display"
    elif has_person and not has_product:
        return "lifestyle"
    else:
        return "other"


def extract_message_id(image_path: Path) -> str:
    """Extract message_id from filename (e.g. '12345.jpg' -> '12345')."""
    match = re.match(r"(\d+)", image_path.stem)
    return match.group(1) if match else image_path.stem


def main():
    logger.info("🚀 Starting YOLO object detection")

    # Load the lightweight YOLOv8 nano model (auto-downloads on first run)
    model = YOLO("yolov8n.pt")
    logger.info("✅ Model loaded: yolov8n.pt")

    image_files = list(IMAGES_DIR.rglob("*.jpg"))
    logger.info(f"Found {len(image_files)} images to process")

    if not image_files:
        logger.warning("No images found. Run the scraper first.")
        return

    results_rows = []

    for i, img_path in enumerate(image_files, 1):
        channel_name = img_path.parent.name
        message_id = extract_message_id(img_path)

        try:
            results = model(str(img_path), verbose=False)
            result = results[0]

            detected_classes = set()
            detections = []

            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                confidence = float(box.conf[0])
                detected_classes.add(cls_name)
                detections.append((cls_name, confidence))

            category = classify_image(detected_classes)

            if detections:
                for cls_name, confidence in detections:
                    results_rows.append({
                        "message_id": message_id,
                        "channel_name": channel_name,
                        "image_path": str(img_path.relative_to(BASE_DIR)),
                        "detected_class": cls_name,
                        "confidence_score": round(confidence, 4),
                        "image_category": category,
                    })
            else:
                results_rows.append({
                    "message_id": message_id,
                    "channel_name": channel_name,
                    "image_path": str(img_path.relative_to(BASE_DIR)),
                    "detected_class": "none",
                    "confidence_score": 0.0,
                    "image_category": "other",
                })

        except Exception as exc:
            logger.warning(f"Failed on {img_path}: {exc}")
            continue

        if i % 50 == 0:
            logger.info(f"  …processed {i}/{len(image_files)} images")

    # Write results to CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "message_id", "channel_name", "image_path",
                "detected_class", "confidence_score", "image_category",
            ],
        )
        writer.writeheader()
        writer.writerows(results_rows)

    logger.success(f"✅ Saved {len(results_rows)} detection records → {OUTPUT_CSV}")

    # Quick summary
    categories = {}
    for row in results_rows:
        cat = row["image_category"]
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("📊 Category breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        logger.info(f"   {cat}: {count}")


if __name__ == "__main__":
    main()
