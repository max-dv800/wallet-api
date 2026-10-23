from celery import shared_task

from wallet_api.utils.currency_rate import load_currency_rate

from .celery_app import celery_app

celery_app.conf.beat_schedule = {
    "task_ever_hour": {
        "task": "wallet_api.tasks.update_currency_task.task_for_update_currency_rate",
        "schedule": 3600.0,
    }
}


@shared_task
def task_for_update_currency_rate():
    load_currency_rate()
    return {"status": "complite"}
