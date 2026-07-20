---
source_url: https://www.investopedia.com/articles/technical/073001.asp
fetched: 2026-07-14
fetch_status: blocked (WebFetch could not retrieve investopedia.com)
filed_from: canonical Lane (1950s) reference — content below reconstructed from standard indicator literature, not the article itself. Re-ingest when Investopedia is accessible.
---
# Stochastic Oscillator — canonical reference (filed pending re-fetch)

**Author**: George C. Lane (developed late 1950s at Investment Educators, Chicago).

**Definition**: Momentum indicator that compares a security's closing price to its trading range over a lookback window. Premise (Lane): "In an uptrend, prices tend to close near the high of the recent range; in a downtrend, near the low."

## Formulas
- **raw %K** = `100 × (Close − Lowest Low(n)) / (Highest High(n) − Lowest Low(n))`
- **%K** (slow / smoothed) = `SMA(raw %K, kSmooth)`
- **%D** (signal line)     = `SMA(%K, dSmooth)`

## Variants
| Variant | %K length | %K smoothing | %D smoothing | Typical spec |
|---------|-----------|--------------|--------------|--------------|
| Fast Stochastic | n | 1 (raw) | 3 | (14, 1, 3) |
| Slow Stochastic | n | 3 | 3 | (14, 3, 3) |
| Full Stochastic | n | k | d | user-defined |

`(14, 3, 3)` is the most-taught default.

## Thresholds
- **Overbought** > 80
- **Oversold** < 20
- **Zero line / centreline** = 50 (used for trend regime — above 50 = bullish momentum)

## Signals
1. **%K / %D crossover** — %K crossing %D from below in the oversold zone → buy signal; %K crossing %D from above in the overbought zone → sell signal.
2. **Overbought / oversold exit** — many practitioners wait for the line to cross back out of the extreme zone (e.g. %K crosses back below 80) rather than trading the extreme itself.
3. **Divergence** — price makes a higher high but %K makes a lower high → bearish divergence; opposite → bullish divergence.
4. **Bull/Bear setup** (Lane): a divergence followed by a return to the extreme zone that fails at a lower peak (bearish) or higher trough (bullish) → higher-quality signal than a raw crossover.

## Common Mistakes
- **Fighting the trend**: in a strong uptrend, stochastic can stay >80 for weeks. Overbought ≠ sell in trending markets. Always pair with a trend filter (SMA200, PMax, ADX).
- **Trading every crossover**: on 14/3/3, whipsaws are frequent in choppy conditions. Filter by higher-TF alignment.
- **Ignoring the closing bias**: since the formula uses Close (not intraday high/low of the current bar), the reading updates only at candle close on the timeframe you're viewing.
