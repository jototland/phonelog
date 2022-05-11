#! /bin/sh
env $(xargs < secrets.txt) ./start-rq.sh
