#! /usr/bin/env python


import datetime
import itertools
import json
import operator
import os

import fire
import requests


DATE_TEMPLATE = "%Y%m%d"
DATE_YESTERDAY = (
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
).strftime(DATE_TEMPLATE)

URL_OHLCV = "https://cex.io/api/ohlcv/hd/{date}/{symbol1}/{symbol2}"

DEFAULT_PAIRS = ["USD", "BTC", "ETH"]
MIN_WIN = 0.01  # x% minimum win threshold


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


def _get_factor(ohlcv, dimensions):
    assert 0 <= len(dimensions) < 2
    if len(dimensions) == 1:
        return ohlcv[dimensions[0]]

    return sum(ohlcv[dim] for dim in dimensions) / len(dimensions)


def find_margins(cur_chain, crt_date, dimensions=[1]):
    cur_chain = cur_chain.split()
    assert len(cur_chain) > 3
    assert cur_chain[0] == cur_chain[-1]
    data_chain = []
    for idx in range(len(cur_chain) - 1):
        reverse = False
        for curs in itertools.permutations(cur_chain[idx:idx+2], 2):
            fname = f"{crt_date}_{curs[0]}_{curs[1]}.json"
            print(f"Trying to open {fname}...")
            if os.path.isfile(fname):
                with open(fname) as stream:
                    data = json.load(stream)
                    data_chain.append({"reverse": reverse, "data": data})
                    break
            else:
                reverse = True

    max_time = max([item["data"][0][0] for item in data_chain])
    for data_item in data_chain:
        while data_item["data"][0][0] < max_time:
            data_item["data"].pop(0)
    assert len(set([item["data"][0][0] for item in data_chain])) == 1

    min_length = min([len(item["data"]) for item in data_chain])
    wins = []
    for idx in range(min_length):
        win = 1.0
        for data_item in data_chain:
            oper = operator.truediv if data_item["reverse"] else operator.mul
            factor = _get_factor(data_item["data"][idx], dimensions)
            win = oper(win, factor)
        if win - 1.0 > MIN_WIN:
            wins.append((data_item["data"][idx][0], win))
    print("Wins: ", wins)
    if wins:
        print("Max win: ", max(wins, key=lambda win: win[1]))


if __name__ == "__main__":
    fire.Fire()
