"""URLs intended for humans"""


from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import SubmitField

from .auth import login_require_role
from .fetch import fetch_contacts, fetch_customer_data
from .db import get_db
from .format_calldata import call_sessions_between, get_call_session_data
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
def my_ip_address():
    return '<pre>You have reached: ' + str(request.scheme) + '://' + str(request.host) + str(request.path) + '\nYour ip address: ' + str(request.remote_addr)


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
        to_epoch = request.args.get('to') + 1
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
