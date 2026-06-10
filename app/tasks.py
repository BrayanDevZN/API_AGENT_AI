from app.manager import Manager
from core.celery_app import celery_app


@celery_app.task(name="ai.generate_dashboard")
def generate_dashboard_task(data: dict) -> dict:
    return Manager().generate_dashboard(data)


@celery_app.task(name="ai.analyze_dashboard_refresh")
def analyze_dashboard_refresh_task(data: dict) -> dict:
    return Manager().analyze_dashboard_refresh(data)
