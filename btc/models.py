import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, mapped_column

# We could probably generate this dynamically each time we pull data but I don’t expect it to change very much.
CURRENCIES = [
    "btc",
    "eth",
    "ltc",
    "bch",
    "bnb",
    "eos",
    "xrp",
    "xlm",
    "link",
    "dot",
    "yfi",
    "usd",
    "aed",
    "ars",
    "aud",
    "bdt",
    "bhd",
    "bmd",
    "brl",
    "cad",
    "chf",
    "clp",
    "cny",
    "czk",
    "dkk",
    "eur",
    "gbp",
    "gel",
    "hkd",
    "huf",
    "idr",
    "ils",
    "inr",
    "jpy",
    "krw",
    "kwd",
    "lkr",
    "mmk",
    "mxn",
    "myr",
    "ngn",
    "nok",
    "nzd",
    "php",
    "pkr",
    "pln",
    "rub",
    "sar",
    "sek",
    "sgd",
    "thb",
    "try",
    "twd",
    "uah",
    "vef",
    "vnd",
    "zar",
    "xdr",
    "xag",
    "xau",
    "bits",
    "sats",
]


class Model(DeclarativeBase):
    pass


@declared_attr
def __table_args__(cls):
    return (UniqueConstraint("id", "timestamp"),)


cols = {
    "__tablename__": "stock",
    "internal_id": mapped_column(Integer, autoincrement=True, primary_key=True),
    "id": mapped_column(String),
    "name": mapped_column(String, nullable=False),
    "timestamp": mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    ),
    "last_updated": mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    ),
    "__table_args__": __table_args__,
}
cols.update({currency: mapped_column(Float, nullable=True) for currency in CURRENCIES})
Stock = type("Stock", (Model,), cols)
