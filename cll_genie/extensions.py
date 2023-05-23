"""
This module stores variables/objects that need to be accessed all over
the app. e.g. mongo : MongoClient.
"""
from flask import current_app as cll_app
from flask_login import LoginManager, current_user  # type: ignore
from flask_pymongo import PyMongo  # type: ignore
from functools import wraps

from cll_genie.blueprints.models.clarity import Clarity
from cll_genie.blueprints.models.cll_samples import SampleHandler
from cll_genie.blueprints.models.cll_vquest import ResultsHandler


login_manager = LoginManager()
mongo = PyMongo()
clarity_api = Clarity()
sample_handler = SampleHandler()
results_handler = ResultsHandler()

