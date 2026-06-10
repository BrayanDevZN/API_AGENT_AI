import os


try:
    from celery import Celery
except ImportError:
    Celery = None


class _LocalTask:
    def __init__(self, func):
        self.func = func

    def delay(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def apply_async(self, args=None, kwargs=None, **_options):
        return self.func(*(args or ()), **(kwargs or {}))

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class _LocalCelery:
    def task(self, *_args, **_kwargs):
        def decorator(func):
            return _LocalTask(func)

        return decorator


def _build_celery():
    if Celery is None:
        return _LocalCelery()

    broker_url = os.getenv("CELERY_BROKER_URL")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)

    app = Celery(
        "datapilot_ai_agent",
        broker=broker_url or "memory://",
        backend=result_backend or "cache+memory://",
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("TZ", "America/Sao_Paulo"),
        enable_utc=True,
        task_always_eager=not bool(broker_url),
    )
    return app


celery_app = _build_celery()
