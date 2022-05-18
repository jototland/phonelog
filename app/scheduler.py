"""A simple scheduler for periodic tasks

This is a separate process, and should not be included in webapp

To run: python -m app.scheduler
"""

import rq


if __name__ == "__main__":

    from datetime import datetime
    from functools import wraps
    import schedule
    import time

    from .fetch import fetch_call_data, fetch_customer_data, fetch_contacts
    from .jobs import enqueue, redis_wait_ready
    from . import create_app


    _app = create_app(minimal_app = True)


    def rq_enqueue_with_app_context(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with _app.app_context():
                enqueue(func, *args, **kwargs)
        return wrapper


    with _app.app_context():
        redis_wait_ready()

    rq_enqueue_with_app_context(fetch_call_data)
    schedule.every(2).minutes.do(rq_enqueue_with_app_context(fetch_call_data))
    schedule.every(7).hours.do(rq_enqueue_with_app_context(fetch_customer_data))
    schedule.every(7).hours.do(rq_enqueue_with_app_context(fetch_contacts))

    while True:
        schedule.run_pending()
        time.sleep(5)
