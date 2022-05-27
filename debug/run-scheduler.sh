#! /bin/sh
env $(cat secrets/*.env | xargs) INTERNAL_URL='http://localhost:5000/' python -m app.scheduler
