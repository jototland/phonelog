import sqlite3
from contextlib import contextmanager

from flask import current_app, g


APPLICATION_ID=0xfeeb1e
USER_VERSION=20220127

_schema = ""


def add_to_schema(sql):
    global _schema
    _schema += sql + '\n'
    return sql


@contextmanager
def transaction(conn):
    conn.execute('begin')
    try:
        yield
    except:
        conn.rollback()
        raise
    else:
        conn.commit()


def open_db(filename):
    db = sqlite3.connect(filename,
                         isolation_level=None,
                         detect_types=sqlite3.PARSE_DECLTYPES)
    application_id = db.execute('pragma application_id').fetchone()[0]
    user_version = db.execute('pragma user_version').fetchone()[0]
    db.execute('pragma journal_mode=WAL')
    if application_id == 0 and user_version == 0:
        with transaction(db):
            db.executescript(_schema)
            db.execute(f'pragma application_id={APPLICATION_ID}')
            db.execute(f'pragma user_version={USER_VERSION}')
    db.row_factory = sqlite3.Row
    db.execute('pragma foreign_keys = on')
    return db


def get_db():
    if 'db' not in g:
        g.db = open_db(current_app.config['DATABASE'])
    return g.db


def close_db(_=None): # ignore exception argument
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        get_db()
