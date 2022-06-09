#! /bin/sh
env $(cat secrets/*.env | xargs) FLASK_ENV=development WERKZEUG_DEBUG_PIN=off FLASK_APP=app INTERNAL_URL='http://localhost:5000/' MIN_PASSWORD_SCORE=1 flask run
