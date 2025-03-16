# BTC
Service for polling and returning bit coin data from CoinGecko.


This service polls bit coin data from CoinGecko every minute. It utilizes a Celery Redis queue to schedule a cron task to grab the first 500 and last 500 bit coin names in alphanumeric order (so primarily As and Zs). The reason this does not currently poll all bit coins is the developer key has a limit of 30 requests per minute, which is not enough requests to poll all bit coin records. In order to poll the same bit coin data each minute the bit coin types were sorted alphanumericly and a subset was chosen based on providing a diverse set of samples (various target sample types are listed below under the [Test](#test) section). This cron task kicks off a series of subtasks that actually poll the data for 100 bit coin types at a time. This data is recorded using the last updated timestamp on the data from CoinGecko. I felt this choice resulted in less data drift between the time that the cron task kicked off and the actual time the data was polled resulting in a more accurate timestamp overall. The data is then stored inside of a PostgresSQL database.


The REST API is built using gunicorn and flask and querying is done via the sqlalchemy ORM. One concern I have is in regards to the volatility rank calculation; as more stocks are added, the querying and calculation done on this endpoint may need to be moved to a task scheduled onto the task queue that runs after the cron poll job. I say this because I could see it crashing or becoming massively slow with a bunch more records and it's probably something you would want to calculate once and cache for lookup the next time as opposed to calculating it every time it's requested. I deemed solving this scalability problem out of scope for now though. I would expect in a production application users might want to query additional timestamps than just the last 24 hours and storing every minute worth of each stock for all time can become an unreasonable amount of data. Typically in cases like this, data is archived overtime such that it becomes less and less fine grained overtime. For example; after a week data is averaged over an hour at a time and older data is averaged at a day over time, etc in order to compress the data as it becomes older and older and reduce storage space requirements. 


This implementation lacks some extra services and layers that you would need for a production application including a proxy server, DNS, load balancer, etc. The workers for the task queue and application would also likely need to be scaled up significantly.


Bit coin's that are stale, meaning when polled they have an old last updated date so the current price is from an older time than the current time, are still recorded. Since the PostgresSQL database table has a unique contraint defined on the bit coin and the timestamp, older prices can only be recorded once (not each time).


The currency types were polled from CoinGecko and are currently hardcoded as columns in the database table. This means that if CoinGecko adds a new supported currency, this table will have to be migrated accordingly. Database migrations are already enabled in this repo via alembic and thus alembic is used to initially setup the database when running the project. If this was deemed unacceptable there are probably ways of dynamically updating the table with additional currencies without manual intervention but I deemed that out of scope at this time.


Additional considerations need to be made for response codes returned by the REST API in certain situations, as well as REST API authentication and rate limiting to prevent common attack vectors. Monitoring should also be added before deploying this to production. 


I did not use any AI generated code for this project.


# Initial Setup
1. Checkout the repo:
   ```
   git clone git@github.com:hmstepanek/btc.git
   cd btc
   ```
1. Set your [CoinGecko API key](https://www.coingecko.com/en/api) via: `export COINGECKO_API_KEY="<Your API key>"`
1. Create a volume for postgres to store data:
   `docker volume create --name=btc_postgres`
1. Build all the docker containers:
   `docker compose build` 
1. Setup the database by running alembic database migrations inside the web container:
   ```
   docker compose up postgres -d
   docker compose run --service-ports --remove-orphans web sh
   >>> alembic upgrade head
1. Type exit to exit the container:
   ```
    >>> exit
   ```
1. Now that the database is setup, we can run all containers:
   `docker compose up -d`
1. If you find the web server is giving internal server errors (this may happen after a certain period of time due to missing production level configuration) simply run the following to restart it:
   ```
   docker compose down web
   docker compose up -d web
   ```


# Looking at data inside the database
If, for whatever reason, you would like to view data inside the database, you can run the
[psql](https://www.postgresql.org/docs/current/app-psql.html) command inside the web
container. This will dump you out into PostgresSQL's commandline tool which will allow 
you to explore data and run raw queries on the database. Type `\q` to exit and `exit` to
exit the container when you are done.
   ```
   docker compose run --service-ports --remove-orphans web sh
   >>> psql postgresql://btc@postgres:5432/btc
   >>>>> SELECT * FROM stock; 
   ```


# REST API Documentation
1. Stock data is queried by currency. The following are a list of supported currencies:
    ```
    ["btc","eth","ltc","bch","bnb","eos","xrp","xlm","link","dot","yfi","usd","aed","ars","aud","bdt","bhd","bmd","brl","cad","chf","clp","cny","czk","dkk","eur","gbp","gel","hkd","huf","idr","ils","inr","jpy","krw","kwd","lkr","mmk","mxn","myr","ngn","nok","nzd","php","pkr","pln","rub","sar","sek","sgd","thb","try","twd","uah","vef","vnd","zar","xdr","xag","xau","bits","sats"]
    ```

1. The following query will list supported REST API endpoints:
    `http://127.0.0.1:8000/`


    Returns a list of supported endpoints:
    ```
    ["/stock","/stock/<stock_id>/<currency>","/stock/<stock_id>/<currency>/volatility_rank"]
    ```

1. Stocks are queried by CoinGecko ID. A list of all IDs can be found via:
    `http://127.0.0.1:8000/stock`

    Returns a list of supported CoinGecko bit coin IDs:
    ```
    ["neoxa","popcorn-meme","benqi", ...]
    ```

1. To list the stock prices each minute for the last 24 hours for a given stock id and currency type:
    `http://127.0.0.1:8000/stock/<stock_id>/<currency>`
    Where `stock_id` is the CoinGecko bit coin id and `currency` is one of the supported currency types.


    When returning data for the last 24 hours for a given bit coin and currency pair, the data is only returned if the currency has valid data in it for that stock over the given time period. The data is returned in timestamp and price pairs.
    ```
    [
      [1742341798, 0.04330565],
      [1742341864, 0.04330414],
      [1742341965, 0.04332429],
      [1742342094, 0.0433487],
      ...
    ]
    ```

1. To list the volatility rank over the last 24 hours for a given stock id and currency type:
    `http://127.0.0.1:8000/stock/<stock_id>/<currency>/volatility_rank`
    Where `stock_id` is the CoinGecko bit coin id and `currency` is one of the supported currency types.


    When calculating the volatility rank, only bit coins that have more than one data point for the last 24 hours and valid values for the given currency are compared. This is because volatility doesn't really mean much when there's only one data point and could yield inaccurate results with lots of ties. Ties in rank are not handled. In cases where there is insufficient data or a bit coin or currency type does not exist, a 404 is returned. A 500 is returned if for some reason there is sufficient data to compute the volatility but for whatever reason it fails to find the rank.
    ```
    {"volatility_rank":447}
    ```

# Test cases
I did not add tests or CI for this project. I deemed that out of scope at this time and instead focused on architecture and design and manual testing. Certainly for a production application testing and CI would need to be added.


The following are some test endpoints that I found useful as I was manually validating:

1. The following endpoints can be used to validate a stock that has suffiencient data.
   ```
   http://127.0.0.1:8000/stock/acala/usd
   http://127.0.0.1:8000/stock/acala/usd/volatility_rank
   ```
1. The following endpoints can be used to validate a stock that is missing currency information but has current last updated dates. 
   ```
   http://127.0.0.1:8000/stock/zoey-your-longevity-coach-by-netmind-xyz/usd
   http://127.0.0.1:8000/stock/zoey-your-longevity-coach-by-netmind-xyz/usd/volatility_rank
   ```
1. The following endpoints can be used to validate a stock that is missing currency information and has a very old last updated date.
```
http://127.0.0.1:8000/stock/alxai/usd
http://127.0.0.1:8000/stock/alxai/usd/volatility_rank
```
