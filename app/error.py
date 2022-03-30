from traceback import format_exception

from flask import current_app, render_template
from flask_login import current_user


def not_found(_):
    return (
        render_template(
            '/404.html',
            header="Error:404 Not Found"),
        404)


def forbidden(_):
    return (
        render_template(
            '/403.html',
            header="Error:403 Forbidden"),
        403)


def error_gen(errcode, errmsg):
    def generic_error(e):
        traceback = ""
        if e:
            if current_app.debug:
                traceback = "\n".join(format_exception(e))
            elif current_user.is_authenticated:
                traceback = str(e)
            else:
                traceback = ''
        return (
            render_template(
                '/error.html',
                header=f"Error:{errcode} {errmsg}",
                traceback=traceback),
            errcode)
    return generic_error


def init_app(app):
    app.register_error_handler(404, not_found)
    app.register_error_handler(403, forbidden)
    app.register_error_handler(400, error_gen(400, "Bad Request"))
    if not app.debug:
        app.register_error_handler(500, error_gen(500, "Internal server error"))
