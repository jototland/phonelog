from datetime import datetime

from flask import current_app
import requests

from .model.keyvalue import get_value, set_value
from .db import get_db, transaction
from .model.call_data import upsert_call_channels, upsert_call_sessions
from .model.contacts import upsert_contacts
from .model.customer_data import (
    upsert_agents,
    upsert_internal_phones,
    upsert_service_numbers,
)
from .parse_xml import parse_call_data
from .parse_xml import parse_contacts
from .parse_xml import parse_customer_data
from .utils import uuid_expand


def zisson_api_get(path, params=None):
    hostname = current_app.config['ZISSON_API_HOST']
    username = current_app.config['ZISSON_API_USERNAME']
    password = current_app.config['ZISSON_API_PASSWORD']
    try:
        response = requests.get(f'https://{hostname}/api/simple/{path}',
                                params=params,
                                auth=(username, password))
        response.raise_for_status()
        return response.content
    except requests.RequestException as err:
        current_app.logger.warn(str(err))
        return None


def get_float(s, fallback=0.0):
    try:
        return float(s)
    except (ValueError, TypeError):
        return fallback

def periodic_fetch():
    last_update_call_data = get_float(get_value('last_update_call_data'))
    last_update_other_data = get_float(get_value('last_update_other_data'))
    now = datetime.utcnow().timestamp()
    changed = False

    if now - last_update_call_data > 2 * 60: # 2 minutes
        changed = fetch_call_data()
        if changed:
            set_value('last_update_call_data', str(now))
    if now - last_update_other_data > 23 * 60 * 60: # 23 hours
        fetch_contacts()
        fetch_customer_data()
        set_value('last_update_other_data', str(now))
        changed = True
    if changed:
        from . import push_updates
        push_updates()


def fetch_call_data():
    db = get_db()
    last_call_session_id = get_value('last_call_session_id')
    updated = False

    while True:
        content = zisson_api_get('XmlExport',
                                 {'LastCallSessionId': last_call_session_id})
        if not content:
            break
        call_sessions, call_channels = parse_call_data(content)
        if len(call_sessions) == 0:
            break
        current_app.logger.info(f'Read {len(call_sessions)} new call sessions from zisson')
        last_call_session_id = uuid_expand(call_sessions[-1].call_session_id)
        set_value('last_call_session_id', last_call_session_id)
        updated = True
        with transaction(db):
            db.executemany(upsert_call_sessions, call_sessions)
            db.executemany(upsert_call_channels, call_channels)
        if (datetime.utcnow().timestamp()
                - call_sessions[-1].start_timestamp
                <= 5 * 60):
            break
    return updated


def fetch_contacts():
    content = zisson_api_get('GetContacts')
    if not content:
        return
    contacts = parse_contacts(content)
    db = get_db()
    with transaction(db):
        db.executemany(upsert_contacts, contacts)
    current_app.logger.info('Contacts updated from zisson')
    from . import push_updates
    push_updates()


def fetch_customer_data():
    content = zisson_api_get('CustomerExport')
    if not content:
        return
    agents, internal_phones, service_numbers = (
        parse_customer_data(content))

    db = get_db()
    with transaction(db):
        db.executemany(upsert_agents, agents)
        db.executemany(upsert_internal_phones, internal_phones)
        db.executemany(upsert_service_numbers, service_numbers)
    current_app.logger.info('Customer data updated from zisson')
    from . import push_updates
    push_updates()
