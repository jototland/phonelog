if __name__ == "__main__":

    import atexit
    from functools import wraps

    from apscheduler.schedulers.blocking import BlockingScheduler

    from .fetch import fetch_call_data, fetch_customer_data, fetch_contacts
    from .jobs import enqueue, redis_wait_ready

    from . import create_app


    _app = create_app(minimal_app = True)
    scheduler = BlockingScheduler(job_defaults = {'coalesce': True})
    atexit.register(lambda: scheduler.shutdown())


    def enqueue_with_app_context(func):
        @wraps(func)
        def wrapper():
            with _app.app_context():
                enqueue(func)
        return wrapper


    def schedule(func, **kwargs):
        fn = enqueue_with_app_context(func)
        fn()
        scheduler.add_job(func=fn, trigger="interval", **kwargs)


    redis_wait_ready()

    schedule(fetch_call_data, minutes=2)
    schedule(fetch_customer_data, hours=7)
    schedule(fetch_contacts, hours=7)

    scheduler.start()
