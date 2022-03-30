#! /bin/sh
env $(xargs < secrets.txt) FLASK_ENV=development WERKZEUG_DEBUG_PIN=off FLASK_APP=app flask run
