import datetime
import logging
import os

import requests
from celery import Celery
from celery.schedules import crontab
from models import CURRENCIES, Stock
from sqlalchemy import create_engine, tuple_
from sqlalchemy.orm import Session

_logger = logging.getLogger(__name__)
HEADERS = {
    "x-cg-demo-api-key": os.environ["COINGECKO_API_KEY"],
    "accept": "application/json",
}
engine = create_engine(os.environ["SQLALCHEMY_DATABASE_URI"])

app = Celery("tasks", broker=os.environ["REDIS_URL"])

app.conf.update(
    {
        "beat_schedule": {
            "management": {
                "task": "tasks.get_current_prices_kickoff",
                "schedule": crontab(minute="*"),
            }
        },
    }
)


@app.task(bind=True, max_retries=3)
def get_current_prices_kickoff(self):
    coin_ids = requests.get(
        "https://api.coingecko.com/api/v3/coins/list", headers=HEADERS
    )
    if coin_ids.status_code <= 100 or coin_ids.status_code >= 400:
        raise ValueError(
            f"Recieved status_code {coin_ids.status_code} from /coins/list"
        )
    coin_ids = coin_ids.json()
    coin_id_symbol_map = [(c["id"], c["symbol"]) for c in coin_ids]
    # Sort list of (id, symbol) tuples in order to get info for the same stocks each
    # time. Take the first and last 500 coins in order to get a reasonable sample size.
    # In production this limit should be removed but for now, in order to avoid the 30
    # request/minute rate limit we take a sample set of all the data.
    coin_id_symbol_map.sort(key=lambda tup: tup[0])
    coin_id_symbol_map = dict(coin_id_symbol_map[:500] + coin_id_symbol_map[-500:])
    coin_ids = list(coin_id_symbol_map.keys())
    coin_ids = [
        ",".join(coin_ids[n : min(n + 100, len(coin_ids))])
        for n in range(0, len(coin_ids), 100)
    ]

    for c_ids in coin_ids:
        get_current_prices_for_ids.delay(c_ids, coin_id_symbol_map)


@app.task(bind=True, max_retries=3)
def get_current_prices_for_ids(self, coin_ids, coin_id_symbol_map):
    with Session(engine) as session:
        currencies = ",".join(CURRENCIES)
        coin_data = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin_ids}&vs_currencies={currencies}&include_last_updated_at=true",
            headers=HEADERS,
        )
        if coin_data.status_code == 429:
            # Since our dev token is limited to 30 calls/minute, wait 1 minute before retrying.
            # This will scew the data but it's somewhat unavoidable without more calls
            # per minute.
            self.retry(countdown=60)
        if coin_data.status_code <= 100 or coin_data.status_code >= 400:
            raise ValueError(
                f"Recieved status_code {coin_data.status_code} from /simple/price"
            )

        coin_data = coin_data.json()
        _logger.debug(f"{coin_ids}")
        # Query for existing table for matching stale stocks.
        # Stale stocks will have the same id and timestamp (last updated CoinGecko date).
        stocks_to_be_updated = [
            (
                c_id,
                datetime.datetime.fromtimestamp(
                    c_data["last_updated_at"], datetime.UTC
                ),
            )
            for c_id, c_data in coin_data.items()
        ]
        existing_stocks = (
            session.query(Stock)
            .filter(tuple_(Stock.id, Stock.timestamp).in_(stocks_to_be_updated))
            .all()
        )
        existing_stocks = {(stock.id, stock.timestamp) for stock in existing_stocks}
        _logger.debug(f"{existing_stocks}")
        stock_data = []
        for c_id, c_data in coin_data.items():
            last_updated = datetime.datetime.utcfromtimestamp(c_data["last_updated_at"])
            # If this stock id and timestamp already exist (meaning the latest stock
            # price is stale) do not insert this same info again.
            if (c_id, last_updated) in existing_stocks:
                continue
            symbol = coin_id_symbol_map.get(c_id)
            if not symbol:
                _logger.warn(f"Skipping {c_id} due to missing value for symbol.")
                continue

            cols = {"name": symbol, "id": c_id, "timestamp": last_updated}
            cols.update({c: c_data[c] for c in c_data if c in CURRENCIES})
            stock_data.append(Stock(**cols))

        session.bulk_save_objects(stock_data)
        session.commit()
