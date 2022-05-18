"""flask_login helpers, authentication, authorization"""


from base64 import b64decode, b85decode, b85encode
from datetime import datetime
from flask import current_app
from functools import wraps
import os
from urllib.parse import urljoin, urlparse
from zxcvbn import zxcvbn

import click
from flask import abort, flash, redirect, render_template, request, url_for
from flask.blueprints import Blueprint
from flask.cli import with_appcontext
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    fresh_login_required,
    login_fresh,
    login_required,
    login_user,
    logout_user,
)
from flask_login.utils import confirm_login
from flask_wtf import FlaskForm
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.fields.simple import HiddenField
from wtforms.validators import DataRequired

from .db import add_to_schema, get_db
from .model.utils import generate_create_table_sql, generate_namedtuple, generate_upsert_sql


TOKEN_SIZE=32 # number of bytes in random user identifier stored in cookies
USER_ROLES=['admin', 'agent', 'zisson_push']
MAX_LOGIN_ATTEMPTS=20

User_fields = (
    ('username', str, 'text primary key'),
    ('password_hash', str, 'text not null'),
    ('roles', str, "text not null default ''"),
    ('token', str|None, 'text unique'),)


add_to_schema(generate_create_table_sql('users',
                                        User_fields))


add_to_schema("""\
create index users_token_idx on users (token);""")


BlockedIpAddr_fields = (
    ('ip_address', str, 'string primary key'),
    ('num_failed_attempts', int, 'integer'),
    ('last_failed_attempt', float, 'real'),
)

BlockedIpAddr = generate_namedtuple('BlockedIpAddr', BlockedIpAddr_fields)

add_to_schema(generate_create_table_sql('blocked_ip_addr', BlockedIpAddr_fields))

add_to_schema("""\
create index blocked_ip_addr_last_failed_attempt_idx
on blocked_ip_addr (last_failed_attempt);""")

def bin2text(blob):
    return b85encode(blob).decode(encoding='ascii')
def text2bin(text):
    return b85decode(text.encode(encoding='ascii'))


def normalize_roles(roles):
    roles = roles.split(',')
    roles = [role.strip() for role in roles]
    roles = [role for role in roles if role in USER_ROLES]
    roles.sort()
    return ', '.join(roles)


class User(UserMixin):
    def __init__(self, username, token, roles):
        self.username = username
        self.token = token
        self.roles = roles
    def get_id(self):
        return self.token
    def __str__(self):
        return f"<User: {self.id}, roles: {', '.join(self.roles)}>"
    def has_authorization(self, roles):
        """Check if user is authorized with a choice of one or more roles.

        A user has authorization for the operation in question if he/she has
        one of the roles in the argument `roles`.

        If an element of `roles` is itself a sequence, the user
        must have all the roles in that inner sequence to be authorized.

        Example: user.has_authorization(['a', ['b', 'c']])
        will return True if user either has role 'a' or roles 'b' and 'c'
        """
        if any(
            (isinstance(role, str) and role in self.roles or
             all((r in self.roles) for r in role))
                for role in roles):
            return True
        return False


upsert_user = generate_upsert_sql('users',
                                  User_fields,
                                  ('username', ))


auth = Blueprint('auth', __name__)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.refresh_view = 'auth.refresh'
login_manager.needs_refresh_message = 'Please reauthenticate'


@login_manager.user_loader
def user_loader(token):
    if not (results := get_db().execute(
        "select username, roles from users "
        "where token = ?",
            (token,)).fetchone()):
        return None
    username, roles = results
    return User(username, token, [role.strip() for role in roles.split(',')])


@login_manager.request_loader
def request_loader(request):
    try:
        username, password = (
            b64decode(
                request.headers.get('Authorization')
                .replace('Basic ', '', 1))
            .decode(encoding='utf-8')
            .split(':', maxsplit=1)
        )
        password_hash, roles = get_db().execute(
            "select password_hash, roles from users where username = ?",
            (username, )).fetchone()
        if check_password_hash(password_hash, password):
            return User(username, None, [role.strip() for role in roles.split(',')])
    except (AttributeError, ValueError, TypeError, KeyError):
        pass
    return None


def login_require_role(*roles, require_fresh=False):
    def require_role_inner(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if current_user.is_authenticated:
                if not require_fresh or login_fresh():
                    if current_user.has_authorization(roles):
                        return f(*args, **kwargs)
                    return abort(403, f"""
                                {current_user.username}: You must be logged in with one of the
                                 following rights to do this: {list(roles)}, but only
                                 have {current_user.roles}.
                                 """)
                return login_manager.needs_refresh()
            return login_manager.unauthorized()
        return decorated
    return require_role_inner


def api_require_role(*roles):
    def require_role_inner(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if current_user.is_authenticated:
                if current_user.has_authorization(roles):
                    return f(*args, *kwargs)
                return "forbidden", 403
            return "unauthorized", 401, {'WWW-Authenticate': 'Basic'}
        return decorated
    return require_role_inner


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def safe_redirect(url):
    if is_safe_url(url):
        return redirect(url or url_for('main.index'))
    return abort(400, f"Redirect to '{escape(url)}' blocked")


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    persistent = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return safe_redirect(request.args.get('next'))
    form = LoginForm()
    if form.validate_on_submit():
        if get_db().execute(
                "select 1 from blocked_ip_addr "
                "where ip_address = ? "
                "and num_failed_attempts >= ?",
                (request.remote_addr, MAX_LOGIN_ATTEMPTS)).fetchone():
            return "ip blocked", 403
        if (result := get_db().execute(
            "select password_hash, roles, token "
            "from users where username = ?",
                (form.username.data, )).fetchone()):
            password_hash, roles, token = result
            roles = [role.strip() for role in roles.split(',')]
            if check_password_hash(password_hash, form.password.data):
                if token is None:
                    get_db().execute(
                        "update users set token = ? where username = ?",
                        (token := bin2text(os.urandom(TOKEN_SIZE)),
                         form.username.data))
                get_db().execute(
                    "delete from blocked_ip_addr where ip_address = ?",
                    (request.remote_addr, ))
                login_user(User(form.username.data, token, roles),
                           remember=form.persistent.data)
                return safe_redirect(request.args.get('next'))
        get_db().execute(
            "insert into blocked_ip_addr "
            "(ip_address, num_failed_attempts, last_failed_attempt) "
            "values (?, ?, ?) "
            "on conflict (ip_address) do update set "
            "num_failed_attempts = num_failed_attempts + 1, "
            "last_failed_attempt = excluded.last_failed_attempt",
            (request.remote_addr, 1, datetime.utcnow().timestamp()))
        flash("Invalid username and/or password")
        return redirect(url_for('auth.login'))
    return render_template('auth/login.html', form=form)


class RefreshForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])


@auth.route('/refresh', methods=['GET', 'POST'])
@login_required
def refresh():
    if login_fresh():
        return safe_redirect(request.args.get('next'))
    form = RefreshForm()
    if form.validate_on_submit():
        if (result := get_db().execute(
            "select password_hash from users where username = ?",
            (current_user.username,)).fetchone()):
            password_hash = result[0]
            if check_password_hash(password_hash, form.password.data):
                confirm_login()
                return safe_redirect(request.args.get('next'))
        flash('Incorrect password, you are logged out')
        logout_user()
        return login_manager.unauthorized()
    return render_template('auth/refresh_session.html', form=form)


@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    get_db().execute("update users set token = NULL where username = ?",
                     (current_user.username,))
    logout_user()
    flash('You have successfully logged out')
    return redirect(url_for('auth.login'))


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password_1 = PasswordField('New Password', validators=[DataRequired()])
    new_password_2 = PasswordField('New Password Again', validators=[DataRequired()])


@auth.route('/changepass', methods=['GET', 'POST'])
@login_required
def change_password():
    print("-----------------change password ------------------------")
    form = ChangePasswordForm()
    if (form.validate_on_submit()
            and form.new_password_1.data == form.new_password_2.data):
        db = get_db()
        print(f"New password: {form.new_password_1.data}")
        (old_password_hash,) = db.execute(
            "select password_hash from users where username = ?",
            (current_user.username, )).fetchone()
        if not check_password_hash(old_password_hash, form.old_password.data):
            flash('Incorrect (old) password')
            return redirect(url_for('auth.change_pasword'))
        if form.new_password_1.data != form.new_password_1.data:
            flash('Passwords fail to match')
            return redirect(url_for('auth.change_pasword'))
        if (zxcvbn(form.new_password_1.data)['score'] <
                int(current_app.config['MIN_PASSWORD_SCORE'])):
            flash('New password does not meet minimum requirements')
            return redirect(url_for('auth.change_pasword'))
        db.execute(
            "update users set password_hash = ? "
            "where username = ?",
            (generate_password_hash(form.new_password_1.data),
             current_user.username))
        flash('Password changed')
        return redirect(url_for('main.index'))
    return render_template('/auth/changepass.html', form=form)


class NewUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    roles = StringField('Roles', validators=[DataRequired()])
    password1 = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Password (again)', validators=[DataRequired()])
    submit = SubmitField('Add user')


@auth.route('/add_user', methods=['GET', 'POST'])
@login_require_role('admin', require_fresh=True)
def add_user():
    form = NewUserForm()
    if form.validate_on_submit():
        if (zxcvbn(form.password1.data)['score'] <
                int(current_app.config['MIN_PASSWORD_SCORE'])):
            flash('Password does not meet minimum requirements')
            return redirect(url_for('auth.add_user'))
        if form.password1.data != form.password2.data:
            flash('passwords do not match')
            return redirect(url_for('auth.add_user'))
        password_hash = generate_password_hash(form.password1.data)
        get_db().execute(
            upsert_user,
            (form.username.data,
             password_hash,
             normalize_roles(form.roles.data),
             None))
        flash(f"Added or modified user: {form.username.data}")
        return redirect(url_for('auth.view_users'))
    return render_template('/auth/new_user.html', form=form, legal_roles=USER_ROLES)

class DeleteUserForm(FlaskForm):
    username = HiddenField('username', validators=[DataRequired()])

@auth.route('/del_user', methods=['POST'])
@login_require_role('admin')
@fresh_login_required
def del_user():
    form = DeleteUserForm()
    if form.validate():
        flash(f"Deleted user '{form.username.data}'")
        get_db().execute('delete from users where username = ?',
                         (form.username.data,))
    else:
        flash("An error occured")
    return redirect(url_for('auth.view_users'))


@auth.route('/users', methods=['GET'])
@login_require_role('admin')
def view_users():
    users = get_db().execute('select username, roles from users').fetchall()
    return render_template('/auth/users.html', users=users, form=DeleteUserForm())


@click.command('adduser')
@click.argument('username')
@click.argument('password')
@click.argument('roles', nargs=-1)
@with_appcontext
def cmd_adduser(username, password, roles):
    roles = normalize_roles(", ".join(roles))
    if (zxcvbn(password)['score'] <
            int(current_app.config['MIN_PASSWORD_SCORE'])):
        print(f"Password does not meet minimum requirements")
        exit(1)
    password_hash = generate_password_hash(password)
    get_db().execute(upsert_user,
                     (username, password_hash, roles, None))
    print(f"Added user {username} with roles: {roles}")


def init_app(app):
    app.cli.add_command(cmd_adduser)
    login_manager.init_app(app)
    app.register_blueprint(auth, prefix='/auth')
