from cll_genie import create_app
from version import __version__

cll_app = create_app()

if cll_app.config["APP_VERSION"] is None:
    cll_app.config["APP_VERSION"] = __version__

if __name__ == "__main__":
    cll_app.run(host="0.0.0.0")
