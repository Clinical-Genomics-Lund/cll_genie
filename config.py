"""
Class-based Flask app configuration.

Config vars set from env variables should be set using a dotenv file passed to do
"""

import os


class Config:
    # Application-wide settings
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_NAME = "cll_genie"
    VQUEST_URL = "https://www.imgt.org/IMGT_vquest/analysis"
    APP_VERSION = os.environ.get("CLL_GENIE_VERSION") or None

    # Main page settings
    PAGE_SIZE = 25

    # Set from ENV:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "notsosecret"

    # Mongo database details
    DB_NAME = os.getenv("DB_NAME", "cll_genie")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "27017")
    DB_SAMPLES_COLLECTION = os.getenv("DB_SAMPLES_COLLECTION", "samples_test")
    DB_RESULTS_COLLECTION = os.getenv("DB_RESULTS_COLLECTION", "vquest_results_test")
    MONGO_URI = f"mongodb://{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # User groups with permission to delete cll_genie samples and vquest_results
    # All users granted permission to edit if DEBUG = True
    CLL_GENIE_SUPER_PERMISSION_GROUPS = ["admin", "lymphotrack_admin"]

    # Report and analysis setting
    ANALYSIS_OUTDIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "results", "saved_cll_analysis"
    )
    REPORT_OUTDIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "results", "saved_cll_reports"
    )

    # REPORT_OUTDIR = "/data/bnf/dev/ram/Pipelines/Web_Developement/cll_genie/results/saved_cll_reports"

    # PDF Report related settings and variables
    PDF_ANALYSIS_RUN_AT = "Centrum för molekylär diagnostik (CMD), Klinisk genetik och patologi"  # PDF REPORT FOOTER INFO

    # LOGO
    LOGO_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "cll_genie",
        "static",
        "images",
        "RSKlogo-rgb.png",
    )

    ANTIBODY_LOGO_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "cll_genie",
        "static",
        "images",
        "group_antibodies.png",
    )

    HYPER_MUTATION_BORDERLINE_UPPER_CUTOFF = 97.98
    HYPER_MUTATION_BORDERLINE_LOWER_CUTOFF = 97.00
    CLL_SUBSETS = [
        "#1",
        "#2",
        "#3",
        "#4",
        "#5",
        "#6",
        "#7",
        "#8",
    ]  # '#2' and '#4' are supported for now


class ProductionConfig(Config):
    LOG_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "logs", "cll_genie_prod.log"
    )
    LOG_LEVEL = "INFO"


class DevelopmentConfig(Config):
    # CLARITY_HOST="http://127.0.0.1/api/v2/"
    DEBUG = True
    SECRET_KEY = "secretkeynotsodisguised"
    _FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "logs", "cll_genie_dev.log"
    )
    LOG_LEVEL = "DEBUG"


class TestConfig(Config):
    """
    For future test code.
    """

    MONGO_URI = None
    TESTING = True
    SECRET_KEY = "rollercosterappdevelopment"
    REPORT_OUTDIR = ANALYSIS_OUTDIR = "/tmp"
