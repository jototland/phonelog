from base64 import b85encode
import logging
import os
import sys

from flask import Flask
from flask_login import login_required
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from jinja2 import StrictUndefined

from . import api, auth, db, error, main
from .format_calldata import lookup_number
from .model import keyvalue
from .utils import phone_number_lookup_link, pretty_print_phone_no


socketio = SocketIO()
csrf = CSRFProtect()


def envconfig(app, key, envvar=None, required=False, nonempty=False):
    if envvar is None:
        envvar = key
    if envvar in os.environ:
        if key in app.config:
            app.logger.info(f"overriding {key} from environment variable {envvar}")
        app.config[key] = os.environ[key]
    if required and key not in app.config:
        app.logger.warn(f'missing required value for {key}')
        sys.exit(1)
    if nonempty and not app.config[key]:
        app.logger.warn(f'missing nonempty value for {key}')
        sys.exit(1)


def create_app(test_config=None):

    logging.basicConfig(
        format="%(levelname)s %(module)s %(name)s %(asctime)s: %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S")

    app = Flask(__name__, instance_relative_config=True)

    # hardcoded config defaults, can be overrided
    app.config.from_mapping(
        SECRET_KEY=b85encode(os.urandom(32)).decode(encoding='ascii'),
        DATABASE=os.path.join(app.instance_path, 'data.sqlite'),
        SESSION_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=not app.debug,
        REMEMBER_COOKIE_SECURE=not app.debug,
        ZISSON_API_HOST='api.zisson.com',
        ZISSON_STATUS_URL='https://zisson-kva.statuspage.io/',
    )
    # config from config.py (or test_config) overrides hardcoded values
    if test_config is not None:
        app.config.from_mapping(test_config)
    else:
        app.config.from_pyfile('config.py', silent=True)

    # environment variables overrides config.py and hardcoded values
    envconfig(app, 'SECRET_KEY', required=True, nonempty=True)
    envconfig(app, 'ZISSON_API_HOST', required=True, nonempty=True)
    envconfig(app, 'ZISSON_STATUS_URL', required=True, nonempty=True)
    envconfig(app, 'ZISSON_API_USERNAME', required=True, nonempty=True)
    envconfig(app, 'ZISSON_API_PASSWORD', required=True, nonempty=True)
    envconfig(app, 'SESSION_COOKIE_INSECURE')
    if 'SESSION_COOKIE_INSECURE' in app.config:
        app.config['SESSION_COOKIE_SECURE'] = False
    envconfig(app, 'REMEMBER_COOKIE_INSECURE')
    if 'REMEMBER_COOKIE_INSECURE' in app.config:
        app.config['REMEMBER_COOKIE_SECURE'] = False

    if app.debug:
        app.jinja_env.undefined = StrictUndefined

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    socketio.init_app(app)
    if 'adduser' not in sys.argv:
        socketio.start_background_task(worker, app)

    auth.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(api.api)
    app.register_blueprint(main.main)
    csrf.exempt(api.api)
    error.init_app(app)
    keyvalue.init_app(app)

    app.add_template_global(phone_number_lookup_link)
    app.add_template_global(pretty_print_phone_no)
    app.add_template_global(lookup_number)

    # app.jinja_env.trim_blocks = True
    # app.jinja_env.lstrip_blocks = True

    return app


@socketio.on('connect')
@login_required
def on_connect():
    pass


def run(app):
    socketio.run(app)


def push_updates():
    from . import live_view
    live_view.push_updates()


def worker(app):
    from .fetch import periodic_fetch
    with app.app_context():
        app.logger.info('Starting background thread')
    while True:
        with app.app_context():
            periodic_fetch()
        socketio.sleep(2 * 60) # 2 minutes


from . import live_view, model
