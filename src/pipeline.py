"""
src/pipeline.py
Dagster pipeline orchestrating the full medical Telegram data pipeline:
scrape -> load to postgres -> dbt transform -> YOLO enrichment -> load YOLO results.
"""

import subprocess
import sys
from pathlib import Path

from dagster import job, op, OpExecutionContext, ScheduleDefinition, Definitions

BASE_DIR = Path(__file__).resolve().parent.parent


def run_script(context: OpExecutionContext, script_path: str, description: str):
    """Helper to run a Python script as a subprocess and stream output to Dagster logs."""
    context.log.info(f"Starting: {description}")
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    context.log.info(result.stdout[-3000:] if result.stdout else "(no stdout)")
    if result.returncode != 0:
        context.log.error(result.stderr[-3000:] if result.stderr else "(no stderr)")
        raise Exception(f"{description} failed with exit code {result.returncode}")
    context.log.info(f"✅ Completed: {description}")
    return True


@op
def scrape_telegram_data(context: OpExecutionContext) -> bool:
    """Run the Telegram scraper to pull new messages and images."""
    return run_script(context, "src/scraper.py", "Telegram scraping")


@op
def load_raw_to_postgres(context: OpExecutionContext, scrape_done: bool) -> bool:
    """Load the scraped JSON data lake into the raw PostgreSQL schema."""
    return run_script(context, "src/load_to_postgres.py", "Load raw data to PostgreSQL")


@op
def run_dbt_transformations(context: OpExecutionContext, load_done: bool) -> bool:
    """Run dbt to build staging and mart models from raw data."""
    context.log.info("Starting: dbt run")
    result = subprocess.run(
        ["dbt", "run"],
        cwd=str(BASE_DIR / "medical_warehouse"),
        capture_output=True,
        text=True,
        shell=True,
    )
    context.log.info(result.stdout[-3000:] if result.stdout else "(no stdout)")
    if result.returncode != 0:
        context.log.error(result.stderr[-3000:] if result.stderr else "(no stderr)")
        raise Exception("dbt run failed")
    context.log.info("✅ Completed: dbt transformations")
    return True


@op
def run_yolo_enrichment(context: OpExecutionContext, dbt_done: bool) -> bool:
    """Run YOLO object detection on all scraped images."""
    return run_script(context, "src/yolo_detect.py", "YOLO image detection")


@op
def load_yolo_results(context: OpExecutionContext, yolo_done: bool) -> bool:
    """Load YOLO detection results into PostgreSQL and rebuild dbt mart."""
    run_script(context, "src/load_yolo_to_postgres.py", "Load YOLO results to PostgreSQL")
    context.log.info("Starting: dbt run (rebuild with YOLO data)")
    result = subprocess.run(
        ["dbt", "run"],
        cwd=str(BASE_DIR / "medical_warehouse"),
        capture_output=True,
        text=True,
        shell=True,
    )
    if result.returncode != 0:
        context.log.error(result.stderr[-3000:] if result.stderr else "(no stderr)")
        raise Exception("dbt run (post-YOLO) failed")
    context.log.info("✅ Pipeline complete!")
    return True


@job
def medical_warehouse_pipeline():
    """
    Full pipeline: scrape -> load -> transform -> enrich -> reload.
    Each op depends on the previous one completing successfully.
    """
    scraped = scrape_telegram_data()
    loaded = load_raw_to_postgres(scraped)
    transformed = run_dbt_transformations(loaded)
    enriched = run_yolo_enrichment(transformed)
    load_yolo_results(enriched)


# Daily schedule at 6 AM
daily_schedule = ScheduleDefinition(
    job=medical_warehouse_pipeline,
    cron_schedule="0 6 * * *",
    execution_timezone="Africa/Addis_Ababa",
)

defs = Definitions(
    jobs=[medical_warehouse_pipeline],
    schedules=[daily_schedule],
)
