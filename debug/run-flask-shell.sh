#! /bin/sh
env $(cat secrets/*.env | xargs) FLASK_ENV=development WERKZEUG_DEBUG_PIN=off FLASK_APP=app flask shell
