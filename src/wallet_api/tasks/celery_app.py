import celery

from wallet_api.core.config import settings

celery_app = celery.Celery(
    "wallet_api", broker=settings.rabbitmq.rabbit_url, backend=settings.redis.redis_url
)

celery_app.autodiscover_tasks(packages=["wallet_api.tasks"], related_name="")
