from flask import Blueprint, current_app, request, abort
from hashlib import sha256
import requests
from datetime import datetime

from .auth import api_require_role
from .db import get_db, transaction
from .model.call_data import upsert_call_channels, upsert_call_sessions
from .parse_xml import parse_call_data


api = Blueprint('api', __name__)


@api.route('/api/zisson/push', methods=['POST'])
@api_require_role('zisson_push')
def receive_zisson_data():
    try:
        call_sessions, call_channels = parse_call_data(request.data)
    except SyntaxError:
        current_app.logger.warn('Zisson push message is malformed')
        return "malformed data", 400

    db = get_db()
    with transaction(db):
        db.executemany(upsert_call_sessions, call_sessions)
        db.executemany(upsert_call_channels, call_channels)
    send_push_updates()
    return "ok"


def _hash(timestamp):
    return sha256(
        b'whatever' +
        current_app.config['SECRET_KEY'].encode(encoding='utf-8') +
        b'something random here' +
        str(timestamp).encode(encoding='utf-8') +
        b".hi there").hexdigest()


def send_push_updates():
    url = current_app.config['INTERNAL_URL'] + '/internal/push_updates'
    timestamp = datetime.utcnow().timestamp()
    headers = {
        'X-Internal-Timestamp': str(timestamp),
        'X-Internal-Signature': _hash(timestamp),
    }
    print(f"headers={headers}")
    requests.post(url, headers=headers)


@api.route('/internal/push_updates', methods=['POST'])
def push_updates():
    from . import live_view
    now = datetime.utcnow().timestamp()
    timestamp = request.headers.get('X-Internal-Timestamp')
    signature = request.headers.get('X-Internal-Signature')
    print(f"timestamp={timestamp}, signature={signature}")
    if (signature is not None
            and timestamp is not None
            and now - 5 <= float(timestamp) <= now
            and _hash(timestamp) == signature):
        live_view.push_updates()
        return "ok"
    else:
        return abort(404)
