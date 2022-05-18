import time

from flask import current_app, g
from flask import g
from redis import ConnectionError, Redis
from rq import Queue


def get_redis():
    if 'redis' not in g:
        host = current_app.config.get('REDIS_HOST', 'localhost')
        port = int(current_app.config.get('REDIS_PORT', 6379))
        db = int(current_app.config.get('REDIS_DB', 0))
        g.redis = Redis(host=host, port=port, db=db)
    return g.redis


def redis_wait_ready():
    redis = get_redis()
    ready = False
    while not ready:
        try:
            redis.ping()
            ready = True
        except ConnectionError:
            current_app.logger.info("Waiting for Redis")
            time.sleep(1)


def get_queue():
    if 'queue' not in g:
        g.queue = Queue(connection = get_redis())
    return g.queue


def enqueue(func, *args, **kwargs):
    get_queue().enqueue(func, *args, **kwargs)
