#! /bin/sh
pip-compile requirements.in
requirements="$(echo $(grep -v '^\s*#' requirements.txt))"
version=$(cut -d '"' -f 2 app/version.py)

grep -v '^\s*#' .gitignore | grep -v '^\s*$' | awk '{print "**/" $1}' > .dockerignore

cat <<- EOF> Dockerfile.phonelog
	FROM python:3.10-slim-bullseye
	RUN useradd -M -d /nonexistent app && pip install $requirements && mkdir /app && mkdir /app/instance && chown app:app /app/instance
	COPY app /app/app
	USER app
	WORKDIR /app
	EXPOSE 5000
        CMD gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 -b 0.0.0.0:5000 'app:create_app()'
EOF
docker build -t jototland/phonelog:$version -f Dockerfile.phonelog .
