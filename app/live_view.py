from flask import request
from flask.templating import render_template
from flask_socketio import disconnect, emit, join_room
from flask_wtf.csrf import ValidationError, validate_csrf

from .extensions import socketio
from .auth import login_require_role
from .format_calldata import get_call_session_data, newest_call_session_ids


def push_updates(recipient='live_view_clients'):
    html = render_template(
        'call_sessions.html',
        call_sessions=map(get_call_session_data,
                          newest_call_session_ids()))
    socketio.emit('replace_content', html, to=recipient)


@socketio.on('connect')
@login_require_role('agent')
def on_connect():
    pass


@socketio.on('join_live_view_clients')
@login_require_role('agent')
def on_join_live_view_clients(csrf_token):
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        disconnect()
        return
    emit('joined_live_view_clients')
    join_room('live_view_clients')
    push_updates(request.sid)
