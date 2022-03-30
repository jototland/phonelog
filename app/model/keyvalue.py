import click
from flask.cli import with_appcontext

from ..db import add_to_schema, get_db
from .utils import generate_create_table_sql, generate_namedtuple, generate_upsert_sql

KeyValue_fields = (
    ('key', str, 'text primary key'),
    ('value', str, 'text not null'))


KeyValue = generate_namedtuple('KeyValue',
                               KeyValue_fields)


add_to_schema(generate_create_table_sql('KeyValue',
                                        KeyValue_fields))



upsert_keyvalue = generate_upsert_sql('keyvalue',
                                      KeyValue_fields,
                                      ('key', ))


def get_value(key, fallback=None):
    result = get_db().execute(
        'select value from keyvalue where key = ?',
        (key,)).fetchone()
    if not result:
        return fallback
    return result[0]


def set_value(key, value):
    get_db().execute(upsert_keyvalue,
                     (key, value))


@click.command('set_value')
@click.argument('key')
@click.argument('value')
@with_appcontext
def cmd_set(key, value):
    set_value(key, value)


@click.command('del_value')
@click.argument('key')
@with_appcontext
def cmd_del(key):
    get_db().execute("delete from keyvalue where key = ?",
                     (str(key), ))


def init_app(app):
    app.cli.add_command(cmd_set)
    app.cli.add_command(cmd_del)
