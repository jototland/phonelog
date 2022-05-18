"""This modules contains the class `FlaskWorker` for use with rq

Flaskworker should only be used by rq, it should not be included in webapp.

To use with rq add to rq command line the arguments
  -w app.rq_worker.FlaskWorker
"""


from rq.worker import Worker
from . import create_app


_app = create_app(minimal_app = True)


class FlaskWorker(Worker):
    """rq worker class specialized for Flask applications"""
    def work(self, *args, **kwargs):
        with _app.app_context():
            return super().work(*args, **kwargs)

