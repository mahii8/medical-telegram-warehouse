# Medical Telegram Warehouse

An end-to-end ELT data pipeline built for the **10 Academy x Kifiya Week 8 Challenge**.

Scrapes Ethiopian medical business data from public Telegram channels (CheMed, Lobelia Cosmetics, Tikvah Pharma), transforms it into a star schema data warehouse using dbt, enriches images with YOLOv8 object detection, exposes insights via a FastAPI REST API, and orchestrates the full pipeline with Dagster.

## Stack

`Python` · `Telethon` · `PostgreSQL` · `dbt` · `YOLOv8` · `FastAPI` · `Dagster` · `Docker`

## Run

```bash
python src/scraper.py           # Extract from Telegram
python src/load_to_postgres.py  # Load to warehouse
dbt run && dbt test             # Transform
python src/yolo_detect.py       # Enrich images
uvicorn api.main:app --reload   # Start API → http://localhost:8000/docs
dagster dev -f src/pipeline.py  # Orchestrate all → http://localhost:3000
```
