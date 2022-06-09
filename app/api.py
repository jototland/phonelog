"""URLS intended for APIs"""


from flask import Blueprint, current_app, request

from app.zisson_api import email_to_current_phone

from .auth import api_require_role
from .db import get_db, transaction
from .model.call_data import upsert_call_channels, upsert_call_sessions, upsert_recordings
from .parse_xml import parse_call_data
from .live_view import push_updates
from .zisson_api import email_to_current_phone, dial


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


@api.route('/api/zisson/dial/<int:from_number>/<int:to_number>')
def zisson_dial(from_number, to_number):
    current_app.logger.info(f"======================================")
    current_app.logger.info(f"testing123 what1={from_number} what2={to_number}")
    current_app.logger.info(f"======================================")
    dial(from_number, to_number)
    return "success\n"

import re
@api.route('/api/dial/<int:a>/<int:b>')
@api_require_role('workstation')
def dial_from_number(a, b):
    current_app.logger.info(f"======================================")
    current_app.logger.info(f"Dial from {a} to {b} 2+2={2+2}")
    current_app.logger.info(f"======================================")
    if not all([
        re.match(r'\+\d+$', a),
        re.match(r'\+\d+$', b),
    ]):
        return "wrong number format\n", 400
    dial(from_number=a, to_number=b)
    return "ok\n"


@api.route('/api/call/from_email/<email>/to/<to_number>')
@api_require_role('workstation')
def dial_from_email(email, to_number):
    from_number = email_to_current_phone(email)
    if from_number == None:
        return "not logged in to zisson\n", 400
    dial(from_number=from_number, to_number=to_number)
    return "ok\n"
