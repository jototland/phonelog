#! /bin/sh
env $(xargs < secrets.txt) INTERNAL_URL='http://localhost:5000/' python -m app.scheduler
