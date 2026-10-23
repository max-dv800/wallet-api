import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import requests
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from wallet_api.core.database import SessionLocal
from wallet_api.models.enums import Currency
from wallet_api.models.exchanges import ExchangeRate
from wallet_api.schemas.transactions import MSK
from wallet_api.utils.cache import sync_redis_cache

KEY_RATES_HASH = "currency:v1"

logger = logging.getLogger(__name__)


def set_cache_all(pairs: list[dict[str, Any]], ex=600):
    pipe = sync_redis_cache.pipeline()
    pipe.delete(KEY_RATES_HASH)
    pipe.hset(
        KEY_RATES_HASH,
        mapping={
            f"{val['from_currency']}:{val['to_currency']}": str(val["rate"])
            for val in pairs
        },
    )
    pipe.expire(KEY_RATES_HASH, ex)
    pipe.execute()


def get_cache_all():
    data = sync_redis_cache.hgetall(KEY_RATES_HASH)
    if not data:
        data_s = load_from_database()
        return {
            f"{v['from_currency']}:{v['to_currency']}": str(v["rate"]) for v in data_s
        }
    return data


def load_from_database():
    with SessionLocal() as session:
        data = session.scalars(select(ExchangeRate)).all()

        if not data:
            load_currency_rate()
            data = session.scalars(select(ExchangeRate)).all()

        payload = [
            {
                "from_currency": r.from_currency,
                "to_currency": r.to_currency,
                "rate": r.rate,
            }
            for r in data
        ]

        set_cache_all(payload)
        return payload


def get_cbr():
    response = requests.get(
        url="https://www.cbr-xml-daily.ru/daily_json.js", timeout=5.0
    )
    response.raise_for_status()

    data = response.json().get("Valute") or {}
    all_val = {}
    for code in ["USD", "EUR"]:
        valute = data.get(code)

        if not valute or valute.get("Value") in (None, 0):
            raise RuntimeError("CBR payload invalid")
        all_val.update({code: valute["Value"]})

    return all_val


def load_currency_rate():
    usd = get_cbr().get("USD")
    eur = get_cbr().get("EUR")

    rub_usd = Decimal(1) / Decimal(str(usd))
    rub_eur = Decimal(1) / Decimal(str(eur))
    usd_eur = Decimal(str(usd)) / Decimal(str(eur))

    val_currency = [
        {
            "from_currency": Currency.RUB,
            "to_currency": Currency.USD,
            "rate": rub_usd.quantize(Decimal("1E-8")),
        },
        {
            "from_currency": Currency.RUB,
            "to_currency": Currency.EUR,
            "rate": rub_eur.quantize(Decimal("1E-8")),
        },
        {
            "from_currency": Currency.USD,
            "to_currency": Currency.EUR,
            "rate": usd_eur.quantize(Decimal("1E-8")),
        },
    ]

    with SessionLocal() as session:
        try:
            stmt = insert(ExchangeRate).values(val_currency)
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["from_currency", "to_currency"],
                    set_={
                        "rate": stmt.excluded.rate,
                        "updated_at": datetime.now(timezone(MSK)),
                    },
                )
            )
            session.commit()
        except Exception:
            logger.exception("Ошибка записи в базу данных")
            raise
    try:
        set_cache_all(val_currency)
    except RedisError:
        logger.exception("Ошибка записи в Redis")
        try:
            sync_redis_cache.delete(KEY_RATES_HASH)
        except RedisError:
            logger.exception("Ошибка очистки базы Redis")
