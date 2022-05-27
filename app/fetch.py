"""Periodic tasks run from scheduler"""

from datetime import datetime
import os

from flask import current_app
from paramiko.ssh_exception import SSHException
from paramiko import RSAKey
from base64 import b64decode
import pysftp
import requests

from .db import get_db, transaction
from .internal import send_push_updates
from .model.call_data import (
    upsert_call_channels,
    upsert_call_sessions,
    upsert_recordings,
)
from .model.contacts import upsert_contacts
from .model.customer_data import (
    upsert_agents,
    upsert_internal_phones,
    upsert_service_numbers,
)
from .model.keyvalue import get_value, set_value
from .parse_xml import parse_call_data
from .parse_xml import parse_contacts
from .parse_xml import parse_customer_data
from .utils import uuid_expand


def zisson_api_get(path, params=None):
    if 'ZISSON_API_PASSWORD' not in current_app.config:
        return

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


def fetch_call_data():
    db = get_db()
    last_call_session_id = get_value('last_call_session_id')
    updated = False

    while True:
        content = zisson_api_get('XmlExport',
                                 {'LastCallSessionId': last_call_session_id})
        if not content:
            break
        call_sessions, call_channels, recordings = parse_call_data(content)
        if len(call_sessions) == 0:
            break
        current_app.logger.info(f'Read {len(call_sessions)} new call sessions from zisson')
        last_call_session_id = uuid_expand(call_sessions[-1].call_session_id)
        set_value('last_call_session_id', last_call_session_id)
        updated = True
        with transaction(db):
            db.executemany(upsert_call_sessions, call_sessions)
            db.executemany(upsert_call_channels, call_channels)
            db.executemany(upsert_recordings, recordings)
        if (datetime.utcnow().timestamp()
                - call_sessions[-1].start_timestamp
                <= 5 * 60):
            break
    if updated:
        send_push_updates()


def fetch_contacts():
    content = zisson_api_get('GetContacts')
    if not content:
        return
    contacts = parse_contacts(content)
    db = get_db()
    with transaction(db):
        db.executemany(upsert_contacts, contacts)
    current_app.logger.info('Contacts updated from zisson')
    send_push_updates()


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
    send_push_updates()


MAX_RECORDING_AGE = 60 * 60 * 24 * 7 # 1 week, in seconds

def recording_local_file(recording_id):
    recording_file_storage = os.path.join(current_app.instance_path, 'recordings')
    return os.path.join(
        recording_file_storage,
        recording_id[0:2],
        recording_id[0:4],
        recording_id)

def fetch_recordings():
    if 'ZISSON_SFTP_PASSWORD' not in current_app.config:
        return

    now = datetime.utcnow().timestamp()
    earliest_timestamp = now - MAX_RECORDING_AGE

    recording_ids = list(
        filter(
            lambda rec_id: not os.path.exists(recording_local_file(rec_id)),
            map(
                lambda x: uuid_expand(x[0]),
                get_db().execute(
                    'select recording_id from recordings '
                    'where start_timestamp >= ? '
                    'and completed = 1 '
                    'order by start_timestamp',
                    (earliest_timestamp,)).fetchall()
            )
        )
    )

    if len(recording_ids) == 0:
        return

    sftp_host_key = RSAKey(data=b64decode(current_app.config['ZISSON_SFTP_HOST_KEY']))
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys.add(current_app.config['ZISSON_SFTP_HOST'],
                        'ssh-rsa',
                        sftp_host_key)
    with pysftp.Connection(host=current_app.config['ZISSON_SFTP_HOST'],
                           username=current_app.config['ZISSON_SFTP_USERNAME'],
                           password=current_app.config['ZISSON_SFTP_PASSWORD'],
                           cnopts=cnopts
                           ) as sftp:
        for recording_id in recording_ids:
            local_file = recording_local_file(recording_id)
            remote_file = 'recording/' + recording_id
            if not sftp.exists(remote_file):
                continue
            os.makedirs(os.path.dirname(local_file), mode=0o700, exist_ok=True)
            try:
                current_app.logger.info(f'Downloading recording {recording_id}')
                sftp.get(remote_file, local_file, preserve_mtime=True)
                os.chmod(local_file, 0o600)
                #sftp.remove(remote_file) # FIXME: activate later
            except SSHException:
                try:
                    os.remove(local_file)
                except FileNotFoundError:
                    pass
