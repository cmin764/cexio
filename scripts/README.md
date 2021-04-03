# Finding arbitrage in cex.io

1. Install Python 3 and requirements.
2. Run `./cexio.py find_all_margins --start "20210222" --days 3`

This means the following:
- Starting with `22th of February` for `3 days` scan arbitrage time windows starting
and ending with fiat money and crypto in between.
- This downloads first the OHLCV history and stores it on disk for each date.
- Then the history is analyzed given various transaction chains.
  (use `--download False` for not re-downloading the same history again)

3. Observe output:
```console
Configuration: 20210222 ['EUR', 'ETH', 'BTC', 'EUR']
Analyzed timestamps of total: 93/287
Wins:  [(1614003480, 1.0586923075180275, (4,)), (1614003540, 1.0612315236207828, (1,)), (1614003600, 1.0528898957861348, (4,))]
Max win:  (1614003540, 1.0612315236207828, (1,))
```
- Configuration: _date_ _currency-chain_
- Timestamps: _overlapping-timestamps_ / _maximum-timestamps_
- Wins: [(timestamp, factor, dimensions), ...]
- Max win: _max from above_

Structure of a win:
- timestamp: seconds since Epoch
- factor: for **1.06x** if you invest $100, you end up with $106 for each round
- dimensions: used OHLC index [1]-Open, [2,3]-avg(High,Low), [4]-Close
