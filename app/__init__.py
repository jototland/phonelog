from base64 import b85encode
import logging
import os
import sys

from flask import Flask
from jinja2 import StrictUndefined
from werkzeug.middleware.proxy_fix import ProxyFix

from . import (
    api,
    auth,
    db,
    error,
    extensions,
    format_calldata,
    internal,
    jobs,
    live_view,
    main,
    model,
    parse_xml,
    utils,
    version,
)
from .extensions import csrf, socketio
from .format_calldata import lookup_number
from .model import keyvalue
from .utils import phone_number_lookup_link, pretty_print_phone_no


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
    if nonempty and key in app.config and not app.config[key]:
        app.logger.warn(f'missing nonempty value for {key}')
        sys.exit(1)


def create_app(test_config=None, minimal_app=False):

    logging.basicConfig(
        format="%(levelname)s %(module)s %(name)s %(asctime)s: %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S")

    app = Flask(__name__, instance_relative_config=True)

    # hardcoded config defaults, can be overrided
    app.config.from_mapping(
        SECRET_KEY=b85encode(os.urandom(32)).decode(encoding='ascii'),
        INTERNAL_URL='http://localhost:5000/',
        DATABASE=os.path.join(app.instance_path, 'data.sqlite'),
        SESSION_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=not app.debug,
        REMEMBER_COOKIE_SECURE=not app.debug,
        ZISSON_SFTP_HOST='ftp.zisson.com',
        ZISSON_API_HOST='api.zisson.com',
        ZISSON_STATUS_URL='https://zisson-kva.statuspage.io/',
        MIN_PASSWORD_SCORE=3,
    )
    # config from config.py (or test_config) overrides hardcoded values
    if test_config is not None:
        app.config.from_mapping(test_config)
    else:
        app.config.from_pyfile('config.py', silent=True)

    # environment variables overrides config.py and hardcoded values
    envconfig(app, 'SECRET_KEY', required=True, nonempty=True)
    envconfig(app, 'INTERNAL_URL')
    envconfig(app, 'ZISSON_API_HOST', required=True, nonempty=True)
    envconfig(app, 'ZISSON_STATUS_URL', required=True, nonempty=True)
    envconfig(app, 'ZISSON_API_USERNAME', required=False, nonempty=True)
    envconfig(app, 'ZISSON_API_PASSWORD', required=False, nonempty=True)
    envconfig(app, 'ZISSON_SFTP_USERNAME', required=False, nonempty=True)
    envconfig(app, 'ZISSON_SFTP_PASSWORD', required=False, nonempty=True)
    envconfig(app, 'ZISSON_SFTP_HOST_KEY', required=False, nonempty=True)
    envconfig(app, 'REDIS_HOST')
    envconfig(app, 'REDIS_PORT')
    envconfig(app, 'REDIS_DB')
    envconfig(app, 'SESSION_COOKIE_INSECURE')
    if 'SESSION_COOKIE_INSECURE' in app.config:
        app.config['SESSION_COOKIE_SECURE'] = False
    envconfig(app, 'REMEMBER_COOKIE_INSECURE')
    if 'REMEMBER_COOKIE_INSECURE' in app.config:
        app.config['REMEMBER_COOKIE_SECURE'] = False
    envconfig(app, 'TRUSTED_PROXIES_COUNT')
    envconfig(app, 'MIN_PASSWORD_SCORE')

    if ('TRUSTED_PROXIES_COUNT' in app.config):
        trusted_proxies_count = int(app.config['TRUSTED_PROXIES_COUNT'])
        app.wsgi_app = ProxyFix(app.wsgi_app,
                                x_proto=trusted_proxies_count,
                                x_host=trusted_proxies_count,
                                x_for=trusted_proxies_count)

    if app.debug:
        app.jinja_env.undefined = StrictUndefined

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    if minimal_app:
        return app

    socketio.init_app(app)

    auth.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(api.api)
    app.register_blueprint(main.main)
    app.register_blueprint(internal.internal)
    csrf.exempt(api.api)
    csrf.exempt(internal.internal)
    error.init_app(app)
    keyvalue.init_app(app)

    app.add_template_global(phone_number_lookup_link)
    app.add_template_global(pretty_print_phone_no)
    app.add_template_global(lookup_number)
    app.add_template_global(float)

    return app
