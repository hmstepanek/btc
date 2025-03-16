"""create stock table

Revision ID: cb46d60820d0
Revises:
Create Date: 2025-03-17 09:42:52.465944

"""

import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cb46d60820d0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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


def upgrade() -> None:
    """Upgrade schema."""
    cols = [
        sa.Column("internal_id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("id", sa.String),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "timestamp", sa.DateTime, nullable=False, default=datetime.datetime.utcnow
        ),
        sa.Column(
            "last_updated",
            sa.DateTime,
            nullable=False,
            default=datetime.datetime.utcnow,
        ),
    ]
    cols.extend(
        [sa.Column(currency, sa.Float, nullable=True) for currency in CURRENCIES]
    )
    op.create_table("stock", *cols)
    op.create_unique_constraint(
        "uix_stock_id_timestamp",
        "stock",
        ["id", "timestamp"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uix_stock_id_timestamp", "stock")
    op.drop_table("stock")
