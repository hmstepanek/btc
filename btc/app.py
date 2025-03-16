import datetime
import os

import pandas as pd
from flask import Flask
from models import CURRENCIES, Stock
from sqlalchemy import and_, create_engine, func
from sqlalchemy.orm import Session, load_only

app = Flask(__name__)
engine = create_engine(os.environ["SQLALCHEMY_DATABASE_URI"])


@app.route("/")
def home():
    return [
        "/stock",
        "/stock/<stock_id>/<currency>",
        "/stock/<stock_id>/<currency>/volatility_rank",
    ]


@app.route("/stock/<stock_id>/<currency>")
def stock_price_since_24hrs_ago(stock_id, currency):
    with Session(engine) as session:
        if currency not in CURRENCIES:
            return f"{currency} not found", 404
        # We are always 1 minute behind the current time so that we aren't pulling
        # partially loaded data from the current minute.
        current_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        since_time = current_time - datetime.timedelta(hours=24, minutes=1)
        # Grab data where currency is not NULL.
        btcs = (
            session.query(Stock.timestamp, getattr(Stock, currency))
            .filter(
                and_(
                    Stock.timestamp.between(since_time, current_time),
                    getattr(Stock, currency) != None,
                )
            )
            .where(Stock.id == stock_id)
            .order_by(Stock.timestamp.asc())
            .all()
        )
        btcs = [(int(timestamp.timestamp()), currency) for timestamp, currency in btcs]
        if not btcs:
            return f"Data for stock_id={stock_id} currency={currency} not found.", 404
        return btcs


@app.route("/stock/<stock_id>/<currency>/volatility_rank")
def stock_rank(stock_id, currency):
    with Session(engine) as session:
        if currency not in CURRENCIES:
            return f"{currency} not found", 404
        # We are always 1 minute behind the current time so that we aren't pulling
        # partially loaded data from the current minute.
        current_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        since_time = current_time - datetime.timedelta(hours=24, minutes=1)
        # Only calculate rank for currencies that have > 1 data points and a value
        # for the currency type.
        stocks_to_calc_stddev = (
            session.query(Stock.id, func.count(Stock.timestamp))
            .filter(
                and_(
                    Stock.timestamp.between(since_time, current_time),
                    getattr(Stock, currency) != None,
                )
            )
            .group_by(Stock.id)
            .all()
        )
        stocks_to_calc_stddev = [
            id_ for id_, n_values in stocks_to_calc_stddev if n_values > 1
        ]
        if stock_id not in stocks_to_calc_stddev:
            return (
                f"Insufficient data found for stock_id={stock_id} currency={currency}.",
                404,
            )

        # Calculate volatility inside database for each stock.
        stock_stddevs = (
            session.query(Stock.id, func.stddev(getattr(Stock, currency)))
            .filter(
                and_(
                    and_(
                        Stock.timestamp.between(since_time, current_time),
                        getattr(Stock, currency) != None,
                    ),
                    Stock.id.in_(stocks_to_calc_stddev),
                )
            )
            .group_by(Stock.id)
            .all()
        )
        # Sort the results by volatility value such that the index is the rank.
        stock_stddevs.sort(key=lambda tup: tup[1], reverse=True)
        for idx, tup in enumerate(stock_stddevs):
            if tup[0] == stock_id:
                return {"volatility_rank": idx}, 200
        return (
            f"Unable to determine volatility rank for stock_id={stock_id} currency={currency}.",
            500,
        )


@app.route("/stock")
def btc():
    with Session(engine) as session:
        stocks = session.query(Stock.id).distinct().all()
        stocks = [stock[0] for stock in stocks]
        return stocks, 200
