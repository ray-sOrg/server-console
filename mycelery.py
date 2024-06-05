from api.image_api import fetch_images_from_oss
from api.test_api import test_celery_task
from celery import Celery


# 创建celery对象
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config.get('CELERY_RESULT_BACKEND'),
        broker=app.config.get('CELERY_BROKER_URL')
    )

    # 用于在任务执行时激活应用程序上下文
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    app.celery = celery

    celery.task(name="test_celery_task")(test_celery_task)
    celery.task(name="fetch_images_from_oss")(fetch_images_from_oss)

    return celery
