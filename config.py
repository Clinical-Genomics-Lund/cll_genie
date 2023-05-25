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

    # Main page settings
    PAGE_SIZE = 25

    # Set from ENV:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "notsosecret"
    CLARITY_USER = os.getenv("CLARITY_USER", None)
    CLARITY_PASSWORD = os.getenv("CLARITY_PASSWORD", None)
    CLARITY_HOST = os.getenv("CLARITY_HOST", None)

    # Mongo database details
    DB_NAME = os.getenv("DB_NAME", "cll_genie")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "27017")
    DB_SAMPLES_COLLECTION = os.getenv("DB_SAMPLES_COLLECTION", "samples")
    DB_RESULTS_COLLECTION = os.getenv("DB_RESULTS_COLLECTION", "vquest_results")
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

    REPORT_SUMMARY_COLUMNS = [  # DO NOT CHANGE THIS UNLESS YOU KNOW WHAT YOU ARE DOING
        "V-DOMAIN Functionality",
        "V-GENE and allele",
        "V-REGION score",
        "V-REGION identity %",
        "V-REGION identity nt",
        "V-REGION identity % (with ins/del events)",
        "V-REGION identity nt (with ins/del events)",
        "J-GENE and allele",
        "J-REGION score",
        "J-REGION identity %",
        "J-REGION identity nt",
        "D-GENE and allele",
        "D-REGION reading frame",
        "CDR-IMGT lengths",
        "FR-IMGT lengths",
        "AA JUNCTION",
        "V-DOMAIN Functionality comment",
        "V-REGION insertions",
        "V-REGION deletions",
        "Analysed sequence length",
        "Sequence analysis category",
        "CLL subset",
        "Merge Count",
        "Total Reads Per",
    ]

    REPORT_JUNCTION_COLUMNS = [
        "JUNCTION-nt nb",
        "JUNCTION decryption",
    ]  # DO NOT CHANGE THIS UNLESS YOU KNOW WHAT YOU ARE DOING

    # PDF Report related settings and variables
    PDF_ANALYSIS_RUN_AT = "Centrum för molekylär diagnostik (CMD) och Klinisk genetik och patologi"  # PDF REPORT FOOTER INFO

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
        os.path.dirname(os.path.abspath(__file__)), "logs", "main_logs.log"
    )
    LOG_LEVEL = "INFO"


class DevelopmentConfig(Config):
    # CLARITY_HOST="http://127.0.0.1/api/v2/"
    DEBUG = True
    SECRET_KEY = "secretkeynotsodisguised"
    LOG_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "logs", "dev_logs.log"
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
