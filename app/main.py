"""URLs intended for humans"""


from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_wtf import FlaskForm
from wtforms import SubmitField

from .auth import login_require_role
from .db import get_db
from .fetch import fetch_contacts, fetch_customer_data
from .format_calldata import call_sessions_between, get_call_session_data
from .model.call_data import recording_local_file
from .utils import uuid_compact


main = Blueprint('main', __name__)


@main.route('/')
@login_require_role('agent')
def index():
    return redirect(url_for('main.live_view'))


@main.route('/call_session_id/<call_session_id>')
@login_require_role('agent')
def call_session_view(call_session_id):
    call_session = get_call_session_data(uuid_compact(call_session_id))
    return render_template('call_session.html', call_session_id=call_session_id, call_session=call_session)


@main.route('/check_ip_config')
@login_require_role('admin')
def my_ip_address():
    orig_env = request.environ
    if 'werkzeug.proxy_fix.orig' in request.environ:
        orig_env = request.environ['werkzeug.proxy_fix.orig']

    return (
        f"<pre>You have reached: {request.scheme}://{request.host}{request.path}\n"
        f"This server runs on host {orig_env['SERVER_NAME']} port {orig_env['SERVER_PORT']} and serves {orig_env['wsgi.url_scheme']}\n\n"
        f"The current request originated from: {orig_env['REMOTE_ADDR']} port {request.environ['REMOTE_PORT']}\n\n"
        "Each proxy adds the requests origin to the end (right) of X-Forwarded-XXX headers. Their current values are:\n"
        f"X-Forwarded-For is: {request.headers['X-Forwarded-For']}\n"
        f"X-Forwarded-Proto is: {request.headers['X-Forwarded-Proto']}\n"
        f"X-Forwarded-Host is: {request.headers['X-Forwarded-Host']}\n\n"
        f"This server is configured to trust {current_app.config['TRUSTED_PROXIES_COUNT']} proxies\n"
        f"Therefore I conclude that your IP address really is: {request.remote_addr}\n"
        "</pre>"
    )


@main.route('/history')
@login_require_role('agent')
def history_view():
    lowest_timestamp = (
        get_db()
        .execute('select min(start_timestamp) from call_sessions')
        .fetchone()[0]
        or datetime.utcnow().timestamp()
    ) - 24 * 60 * 60
    lowest_date = datetime.fromtimestamp(lowest_timestamp).date().isoformat()

    highest_timestamp = datetime.utcnow().timestamp() + 24 * 60 * 60
    highest_date = datetime.fromtimestamp(highest_timestamp).date().isoformat()

    try:
        from_epoch = float(request.args.get('from'))
        assert lowest_timestamp <= from_epoch <= highest_timestamp
    except (ValueError, AssertionError, TypeError):
        from_epoch = datetime.utcnow().timestamp() - 24*60*60 + 1

    try:
        to_epoch = float(request.args.get('to')) + 1
        assert from_epoch <= to_epoch <= from_epoch
    except (ValueError, AssertionError, TypeError):
        to_epoch = from_epoch + 24*60*60

    data = list(map(get_call_session_data, call_sessions_between(from_epoch, to_epoch)))
    return render_template('history.html',
                           call_sessions=data,
                           from_epoch=from_epoch,
                           to_epoch=to_epoch,
                           lowest_date=lowest_date,
                           highest_date=highest_date,
                           container_classes="container-sm")


@main.route('/live')
@login_require_role('agent')
def live_view():
    return render_template('live_view.html', container_classes="container-sm")


@main.route('/rickroll')
def rickroll():
    return redirect('https://www.youtube.com/watch?v=dQw4w9WgXcQ')


class UpdateButtonForm(FlaskForm):
    submit = SubmitField('Update')


@main.route('/customer_data', methods=['GET', 'POST'])
@login_require_role('admin')
def view_customer_data():
    form = UpdateButtonForm()
    if form.validate_on_submit():
        fetch_customer_data()
        flash('Customer data updated')
        return redirect(url_for('main.view_customer_data'))
    agents = [dict(row) for row in get_db().execute("select * from agents").fetchall()]
    internal_phones = [dict(row) for row in
                       get_db().execute("select * from internal_phones").fetchall()]
    service_numbers = [dict(row) for row in
                       get_db().execute("select * from service_numbers").fetchall()]
    return render_template('customer_data.html',
                           form=form,
                           agents=agents,
                           internal_phones=internal_phones,
                           service_numbers=service_numbers)


@main.route('/contacts', methods=['GET', 'POST'])
@login_require_role('admin')
def view_contacts():
    form = UpdateButtonForm()
    if form.validate_on_submit():
        fetch_contacts()
        flash('Contacts updated')
        return redirect(url_for('main.view_contacts'))
    contacts = [dict(row) for row
                in get_db().execute("select * from contacts").fetchall()]
    return render_template('contacts.html',
                           form=form,
                           contacts=contacts)


@main.route('/play_recording/<recording_id>', methods=['GET', 'POST'])
@login_require_role('recording')
def play_recording(recording_id):
    recording_start, recording_end = get_db().execute(
        'select start_timestamp, stop_timestamp from recordings '
        'where recording_id = ? and completed = 1',
        (uuid_compact(recording_id),)).fetchone()
    return render_template('modal_player.html',
                           recording_start = recording_start,
                           recording_end = recording_end,
                           recording_id = recording_id)


@main.route('/recording/<recording_id>')
@login_require_role('recording')
def recording(recording_id):
    current_app.logger.info(f"Downloading recording {recording_id}")
    return send_file(recording_local_file(recording_id),
                     mimetype='audio/mpeg',
                     attachment_filename=f"{recording_id}.mp3")
