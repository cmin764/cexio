#! /usr/bin/env python


import datetime
import functools
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

DEFAULT_PAIRS = ["USD", "BTC", "ETH", "EUR"]
FIAT = ["USD", "EUR"]
DIMS = [[1], [4], [2, 3]]
MIN_WIN = 0.04  # x% minimum win threshold


def _get_ohlcv(date, pair, is_reversed=False):
    date_str = date.strftime(DATE_TEMPLATE)
    url = URL_OHLCV.format(date=date_str, symbol1=pair[0], symbol2=pair[1])
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        if is_reversed:
            raise Exception(f"this pair isn't available for history: {pair}")
        return _get_ohlcv(date, list(reversed(pair)), is_reversed=True)

    return pair, json.loads(data["data1m"])


def download_history(start=DATE_YESTERDAY, days=1, pairs=DEFAULT_PAIRS):
    start_date = datetime.datetime.strptime(str(start), DATE_TEMPLATE)
    for diff in range(days):
        crt_date = start_date + datetime.timedelta(days=diff)
        for pair in itertools.combinations(pairs, 2):
            if len(set(pair) - set(FIAT)) == 0:
                continue

            pair, data = _get_ohlcv(crt_date, sorted(pair))
            date_str = crt_date.strftime(DATE_TEMPLATE)
            fname = "{}_{}_{}.json".format(
                date_str, pair[0], pair[1]
            )
            with open(fname, "w") as stream:
                print(f"Dumping on {date_str} {pair[0]}/{pair[1]}: {len(data)} timestamps")
                json.dump(data, stream)


def _get_factor(ohlcv, dimensions):
    assert 0 < len(dimensions) <= 2
    if len(dimensions) == 1:
        return ohlcv[dimensions[0]]

    return sum(ohlcv[dim] for dim in dimensions) / len(dimensions)


@functools.lru_cache(maxsize=None)
def _open_pair(crt_date, first, second, reverse=False):
    fname = f"{crt_date}_{first}_{second}.json"
    # print(f"Trying to open {fname}...")
    if os.path.isfile(fname):
        with open(fname) as stream:
            data = json.load(stream)
            min_date = data[0][0]
            max_date = data[-1][0]
            data = {tick[0]: tick for tick in data}
            return {"reverse": reverse, "data": data, "min_date": min_date, "max_date": max_date}

    if reverse is True:
        raise Exception(f"pair {first}/{second} for {crt_date} not found at all")
    return _open_pair(crt_date, second, first, reverse=True)


def find_margins(cur_chain, crt_date_str, min_win=MIN_WIN):
    if not isinstance(cur_chain, list):
        cur_chain = cur_chain.split()
    assert len(cur_chain) > 3
    assert cur_chain[0] == cur_chain[-1]
    tran_chain = []
    for time_idx in range(len(cur_chain) - 1):
        tran_chain.append(_open_pair(crt_date_str, *cur_chain[time_idx:time_idx + 2]))

    start_time = max([item["min_date"] for item in tran_chain])
    end_time = min([item["max_date"] for item in tran_chain])
    max_ts = min([len(item["data"]) for item in tran_chain])

    wins = []
    ts = 0
    for time_idx in range(start_time, end_time + 60, 60):
        win_by_dims = {tuple(dims): 1.0 for dims in DIMS}
        for tran_item in tran_chain:
            tick = tran_item["data"].get(time_idx)
            if not tick:
                break
            oper = operator.truediv if tran_item["reverse"] else operator.mul
            for dims in win_by_dims:
                factor = _get_factor(tick, dims)
                win_by_dims[dims] = oper(win_by_dims[dims], factor)
        else:
            ts += 1
            max_win_dims = max(win_by_dims, key=lambda k: win_by_dims[k])
            max_win = win_by_dims[max_win_dims]
            if max_win - 1.0 > min_win:
                wins.append((time_idx, max_win, max_win_dims))

    if wins:
        max_win = max(wins, key=lambda win: win[1])
        print(f"Configuration: {crt_date_str} {cur_chain}")
        print(f"Analyzed timestamps of total: {ts}/{max_ts}")
        print("Wins: ", wins)
        print("Max win: ", max_win)
        print("=" * 30 + "\n")
        return max_win

    return None


def find_all_margins(start=DATE_YESTERDAY, days=1, pairs=DEFAULT_PAIRS, download=True):
    if download:
        download_history(start=start, days=days, pairs=pairs)

    crypto = set(pairs) - set(FIAT)
    start_date = datetime.datetime.strptime(str(start), DATE_TEMPLATE)
    max_win = None
    max_chain = None
    for diff in range(days):
        crt_date = start_date + datetime.timedelta(days=diff)
        crt_date_str = crt_date.strftime(DATE_TEMPLATE)
        for begin in pairs:
            if begin not in FIAT:
                continue

            for length in range(2, len(pairs)):
                for inner_tran in itertools.permutations(crypto, length):
                    cur_chain = [begin] + list(inner_tran) + [begin]
                    ret_win = find_margins(cur_chain, crt_date_str)
                    if ret_win:
                        max_win = max_win or ret_win
                        max_chain = max_chain or cur_chain
                        if ret_win[1] > max_win[1]:
                            max_win = ret_win
                            max_chain = cur_chain

    print("Global max win: ", max_win)
    print("Global max config: ", max_chain)


if __name__ == "__main__":
    fire.Fire()
