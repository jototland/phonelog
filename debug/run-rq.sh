#! /bin/sh
env $(xargs < secrets.txt) INTERNAL_URL='http://localhost:5000/' ./scripts/start-rq.sh
