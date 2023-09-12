from cll_genie.blueprints.main import main_bp
from datetime import datetime
import dateutil
import arrow


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


@main_bp.app_template_filter()
def human_date(value):
    time_zone = "CET"
    return arrow.get(value).replace(tzinfo=dateutil.tz.gettz(time_zone)).humanize()


@main_bp.app_template_filter()
def format_comment(st):
    if st:
        st = st.replace("\n", "<br />")
        return st
    else:
        return st
