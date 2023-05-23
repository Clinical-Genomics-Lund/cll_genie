from cll_genie import create_app
from version import __version__

cll_app = create_app()
cll_app.config['APP_VERSION'] = __version__

if __name__ == '__main__':
    cll_app.run(host="0.0.0.0")