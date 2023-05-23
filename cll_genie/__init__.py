"""Initialize Flask app."""
from flask import Flask
from pprint import pformat
import config
from .logging_setup import configure_logging


def create_app():
    cll_app = Flask(__name__, instance_relative_config=True)

    if not cll_app.debug or cll_app.testing:
        cll_app.config.from_object(config.ProductionConfig())
    else:
        if cll_app.debug:
            cll_app.logger.debug("Loading dev config:")
            cll_app.config.from_object(config.DevelopmentConfig())
            conf_copy = dict(cll_app.config)
            conf_copy["CLARITY_PASSWORD"] = "REDACTED"
            cll_app.logger.debug(pformat(conf_copy))
        elif cll_app.testing:
            cll_app.config.from_object(config.TestConfig())

    cll_app.logger = configure_logging(
        cll_app.config["LOG_LEVEL"], cll_app.config["LOG_FILE"]
    )

    with cll_app.app_context():
        cll_app.logger.info("Initializing app blueprints.")
        register_blueprints(cll_app)
        cll_app.logger.info("Finished initializing app blueprints.")
        cll_app.logger.info("Initializing app extensions.")
        init_login_manager(cll_app)
        init_mongodb(cll_app)
        init_claritydb(cll_app)
        init_samples_handler(cll_app)
        init_results_handler(cll_app)
        cll_app.logger.info("Finished initializing app extensions.")

    cll_app.logger.info("App initialization finished. Returning app.")

    return cll_app


def register_blueprints(app: Flask) -> None:
    """
    Register Flask blueprints
    """

    app.logger.info("Initializing blueprints")

    def bp_debug_msg(msg):
        app.logger.info(f"Blueprint added: {msg}")

    # Main views:
    bp_debug_msg("main_bp")
    from cll_genie.blueprints.main import main_bp

    app.register_blueprint(main_bp)

    # Login module:
    bp_debug_msg("login_bp")
    from cll_genie.blueprints.login import login_bp

    app.register_blueprint(login_bp)


def init_mongodb(app: Flask) -> None:
    """
    Initialize pymongo.MongoClient extension
    """
    app.logger.info("Initializing mongodb at: " f"{app.config['MONGO_URI']}")
    from cll_genie.extensions import mongo

    mongo.init_app(app)


def init_login_manager(app: Flask) -> None:
    """
    Initialize login manager
    """
    from cll_genie.extensions import login_manager

    app.logger.info("Initializing login_manager")
    login_manager.init_app(app)
    login_manager.login_view = "login_bp.login"


def init_samples_handler(app: Flask) -> None:
    """
    Initialize samples handler
    """
    app.logger.info("Initializing SampleHandler")
    from cll_genie.extensions import sample_handler, mongo

    sample_handler.initialize(
        mongo.cx, app.config["DB_NAME"], app.config["DB_SAMPLES_COLLECTION"]
    )


def init_results_handler(app: Flask) -> None:
    """
    Initialize samples handler
    """
    app.logger.info("Initializing Results handler")
    from cll_genie.extensions import results_handler, mongo

    results_handler.initialize(
        mongo.cx, app.config["DB_NAME"], app.config["DB_RESULTS_COLLECTION"]
    )


def init_claritydb(app: Flask) -> None:
    """
    Initialize Clarity API
    """
    from cll_genie.extensions import clarity_api

    app.logger.info(f"Initializing clarityAPI at: {app.config['CLARITY_HOST']}")
    clarity_api.init_from_app(app)
