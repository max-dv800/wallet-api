from unittest.mock import patch

from wallet_api.tasks.update_currency_task import task_for_update_currency_rate


@patch(
    "wallet_api.utils.currency_rate.get_cbr",
    return_value={"USD": 81.1255, "EUR": 91.1364},
)
def test_task(mock_get_cbr, test_celery_app):
    task = task_for_update_currency_rate.delay()

    assert task.ready() is True

    assert task.status == "SUCCESS"

    mock_get_cbr.assert_called()
