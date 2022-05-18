"""URLS intended for APIs"""


from flask import Blueprint, current_app, request

from .auth import api_require_role
from .db import get_db, transaction
from .model.call_data import upsert_call_channels, upsert_call_sessions
from .parse_xml import parse_call_data
from .live_view import push_updates


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
    push_updates()
