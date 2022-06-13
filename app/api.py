"""URLS intended for APIs"""


from flask import Blueprint, current_app, request

from app.zisson_api import email_to_current_phone

from .auth import api_require_role
from .db import get_db, transaction
from .model.call_data import upsert_call_channels, upsert_call_sessions, upsert_recordings
from .parse_xml import parse_call_data
from .live_view import push_updates
from .zisson_api import email_to_current_phone, dial
from .utils import get_conversion


api = Blueprint('api', __name__)


@api.route('/api/zisson/push', methods=['POST'])
@api_require_role('zisson_push')
def receive_zisson_data():
    try:
        call_sessions, call_channels, recordings = parse_call_data(request.data)
    except SyntaxError:
        current_app.logger.warn('Zisson push message is malformed')
        return "malformed data'n", 400

    db = get_db()
    with transaction(db):
        db.executemany(upsert_call_sessions, call_sessions)
        db.executemany(upsert_call_channels, call_channels)
        db.executemany(upsert_recordings, recordings)
    push_updates()
    return "ok\n"


@api.route('/api/dial', methods=['POST'])
@api_require_role('workstation')
def handle_dial():
    to_number = get_conversion(int, request.args.get('to_number'))
    operator_phone = get_conversion(int, request.args.get('operator_phone'))
    operator_email = request.args.get('operator_email')
    operator_fallback_number = get_conversion(int, request.args.get('operator_fallback_number'))

    from_number = None
    if operator_phone is not None:
        from_number = operator_phone
    if operator_email is not None:
        from_number = email_to_current_phone(operator_email)
    if operator_fallback_number is not None and from_number is None:
        from_number = operator_fallback_number

    if from_number is None or to_number is None:
        return "error\n", 400

    dial(from_number, to_number)
    return "success\n"

