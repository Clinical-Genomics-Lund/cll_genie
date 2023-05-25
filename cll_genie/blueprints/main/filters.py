from cll_genie.blueprints.main import main_bp
from datetime import datetime


@main_bp.app_template_filter()
def list_max(list):
    return max(list)


@main_bp.app_template_filter()
def list_min(list):
    return min(list)


@main_bp.app_template_filter()
def simple_date(date: str) -> str:
    date = date.split("T").pop(0)
    return date
