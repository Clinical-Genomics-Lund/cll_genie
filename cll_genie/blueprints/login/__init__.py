from flask import Blueprint

login_bp = Blueprint("login_bp", __name__)

from cll_genie.blueprints.login import views