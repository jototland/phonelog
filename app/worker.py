from rq.worker import Worker
from . import create_app


_app = create_app(minimal_app = True)


class FlaskWorker(Worker):
    def work(self, *args, **kwargs):
        with _app.app_context():
            return super().work(*args, **kwargs)

