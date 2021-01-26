#! /usr/bin/env python


import datetime
import itertools
import json

import fire
import requests


DATE_TEMPLATE = "%Y%m%d"
DATE_YESTERDAY = (
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
).strftime(DATE_TEMPLATE)

URL_OHLCV = "https://cex.io/api/ohlcv/hd/{date}/{symbol1}/{symbol2}"

DEFAULT_PAIRS = ["USD", "BTC", "ETH"]


def _get_ohlcv(date, pair, is_reversed=False):
    date_str = date.strftime(DATE_TEMPLATE)
    url = URL_OHLCV.format(date=date_str, symbol1=pair[0], symbol2=pair[1])
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        if is_reversed:
            raise Exception("this pair isn't available for history: {}".format(pair))
        return _get_ohlcv(date, list(reversed(pair)), is_reversed=True)

    return pair, json.loads(data["data1m"])


def download_history(start=DATE_YESTERDAY, days=1, pairs=DEFAULT_PAIRS):
    start_date = datetime.datetime.strptime(start, DATE_TEMPLATE)
    for diff in range(days):
        crt_date = start_date + datetime.timedelta(days=diff)
        for pair in itertools.combinations(pairs, 2):
            pair, data = _get_ohlcv(crt_date, sorted(pair))
            fname = "{}_{}_{}.json".format(
                crt_date.strftime(DATE_TEMPLATE), pair[0], pair[1]
            )
            with open(fname, "w") as stream:
                json.dump(data, stream)


if __name__ == "__main__":
    fire.Fire()
