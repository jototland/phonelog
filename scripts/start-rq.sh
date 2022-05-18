#! /bin/sh

if [ -z "$REDIS_HOST" ]; then
    REDIS_HOST="localhost"
fi

if [ -z "$REDIS_PORT" ]; then
    REDIS_PORT="6379"
fi

if [ -z "$REDIS_URL" ]; then
    REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}"
fi

until rq worker -u "${REDIS_URL}" --with-scheduler -w app.rq_worker.FlaskWorker; do
    sleep 1
done
