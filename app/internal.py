"""URLS and caller functions intended for internal use within the webapp/scheduler/etc

(protected by timestamp and cryptographic hash of secret key)
"""


from flask import Blueprint, current_app, request, abort, current_app
from hashlib import sha256
import requests
from datetime import datetime
import os

from .live_view import push_updates


internal = Blueprint('internal', __name__)


def _secret_key_as_bytes() -> bytes:
    secret_key = current_app.config['SECRET_KEY']
    if isinstance(secret_key, bytes):
        return secret_key
    if isinstance(secret_key, str):
        return secret_key.encode(encoding='utf-8')
    # never happens: this hash will always be rejected by verify_hash
    return os.urandom(32)


def hash(value: str, salt: bytes) -> str:
    return sha256(
        salt +
        _secret_key_as_bytes() +
        value.encode(encoding='utf-8')
    ).hexdigest()


def verify_hash(value: str, salt: bytes, hashed: str) -> bool:
    return hash(value, salt) == hashed


def call_internal(path: str) -> None:
    timestamp = str(datetime.utcnow().timestamp())
    salt = os.urandom(8)
    headers = {
        'X-Internal-Path': path,
        'X-Internal-Timestamp': timestamp,
        'X-Internal-Salt': salt.hex(),
        'X-Internal-Hash': hash(path + timestamp, salt),
    }
    fullpath = current_app.config['INTERNAL_URL'] + 'internal/' + path
    requests.post(fullpath, headers=headers)


def verify_internal(path: str) -> bool:
    now = datetime.utcnow().timestamp()
    if path != request.headers.get('X-Internal-Path'):
        return False
    timestamp = float(request.headers.get('X-Internal-Timestamp', '0.0'))
    if timestamp < now - 5 or timestamp > now:
        return False
    salt = bytes.fromhex(request.headers.get('X-Internal-Salt'))
    hash = request.headers.get('X-Internal-Hash')
    return verify_hash(path + str(timestamp), salt, hash)


def send_push_updates():
    call_internal('push_updates')


@internal.route('/internal/push_updates', methods=['POST'])
def on_push_updates():
    if verify_internal('push_updates'):
        push_updates()
        return "ok"
    return abort(404)
