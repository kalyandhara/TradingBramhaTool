---
title: "Indicator Catalogue — draft for review (B-149)"
category: analysis
tags: [chart-tool, indicator-panel, beginner, review, b-149]
timeframe: milestone-plan
created: 2026-10-14
updated: 2026-10-14
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/Design-Review-2026-10-13-Look-And-Feel.md
---

# Indicator Catalogue — draft for owner review (B-149)

**Status: DRAFT — Claude wrote it, the owner reviews before any panel shows it.** Source of truth is
`tools/indicator_catalogue.js`; this page is generated from it, so edit the JS (or tell Claude what to
change) rather than this page. Nothing on screen reads these fields yet — the card layout is B-150.

**What to check per entry:** is the *short* line right for a beginner · is the *desc* accurate for how
THIS desk draws it · is the *level* fair · do the *goals* chips fit.

- 59 entries · levels: 23 Beginner, 22 Intermediate, 14 Advanced · 44 link a concept page.
- **Goals (B-156 chips):** `trend` = Which way is it trending? · `stretched` = Is it stretched / overbought? · `levels` = Where is support or resistance? · `volume` = Is real volume behind the move? · `target` = Where could price go next? · `stop` = Where should my stop be?
- **added** comes from `git log -S"key:'<key>'"`. **2026-07-20 is the day the chart file entered git**, so it means "on or before".
- **No evidence claims in the text.** What the desk has measured (e.g. Liquidity Sweep, the astro nulls) belongs to B-154's verdict line; a test rejects "guaranteed / high probability / winning / best" until B-154 gives a key a positive verdict.
- **Judgement calls to look at:** `reversal_calendar` has no goal chip (it is not a price read); `mabias` and `cpr` are rated Beginner because their card/levels are self-explanatory even though the logic behind them is not; `liquidity` mentions that only a BUY side is drawn.

## Moving Averages

### SMA (20) · `sma20`
- **Short:** Average close of the last 20 bars — the short-term trend line.
- **Desc:** Draws the plain average of the last 20 closes as a line on price. Price holding above a rising line is a short-term uptrend; below a falling one, a downtrend. In a sideways market price crosses it back and forth and every cross is noise.
- **Level:** Beginner · **Goals:** trend · **Added:** 2026-07-20 · **Concept:** —

### SMA (50) · `sma50`
- **Short:** Average close of the last 50 bars — the medium-term trend most traders watch.
- **Desc:** Draws the average of the last 50 closes. Many swing traders treat it as the line a healthy uptrend should hold on pullbacks. It reacts slowly, so by the time price clearly breaks it a good part of the move is often over.
- **Level:** Beginner · **Goals:** trend, levels · **Added:** 2026-07-20 · **Concept:** —

### SMA (200) · `sma200`
- **Short:** Average close of the last 200 bars — the long-term trend divider.
- **Desc:** Draws the average of the last 200 closes, roughly a year of daily bars. Above it is broadly read as a long-term uptrend, below it as a downtrend. It is very slow: it says little about the next few weeks and needs 200 bars of history before it appears at all.
- **Level:** Beginner · **Goals:** trend, levels · **Added:** 2026-07-20 · **Concept:** —

### EMA (9) · `ema9`
- **Short:** Fast exponential average of 9 bars — hugs price, shows short swings.
- **Desc:** An average that weights recent closes more, so it turns faster than a simple average. Useful for seeing whether the latest swing is still pushing in one direction. Because it is fast it whipsaws often; on its own it is not a trend filter.
- **Level:** Beginner · **Goals:** trend · **Added:** 2026-07-23 · **Concept:** [[concepts/EMA]]

### EMA (20) · `ema20`
- **Short:** 20-bar exponential average — the line strong trends tend to pull back to.
- **Desc:** A 20-bar average weighted toward recent closes. In a steady trend, pullbacks often stop near it, which is why it is a common pullback reference. In choppy markets price slices through it repeatedly and the line goes flat.
- **Level:** Beginner · **Goals:** trend, levels · **Added:** 2026-07-20 · **Concept:** [[concepts/EMA]]

### EMA (50) · `ema50`
- **Short:** 50-bar exponential average — medium-term trend, turns sooner than the SMA 50.
- **Desc:** A 50-bar average weighted toward recent closes. Read it like the SMA 50: price above a rising line is a medium-term uptrend. It turns earlier than the simple version, which also means it gives more false turns.
- **Level:** Beginner · **Goals:** trend, levels · **Added:** 2026-07-20 · **Concept:** [[concepts/EMA]]

### EMA (200) · `ema200`
- **Short:** 200-bar exponential average — the long-term trend line, weighted to recent bars.
- **Desc:** A 200-bar average weighted toward recent closes. Above it is the long-term up side, below it the down side. It needs a long history to settle and on a young listing it is little more than a guess.
- **Level:** Beginner · **Goals:** trend, levels · **Added:** 2026-07-20 · **Concept:** [[concepts/EMA]]

### VWAP (session · intraday only) · `vwap`
- **Short:** Average price paid today, weighted by volume — intraday charts only.
- **Desc:** Draws the running volume-weighted average price for each session. Price above it means today's buyers are, on average, in profit; below it, in loss. It only means something on intraday bars: on a daily chart each bar is its own session and the line is just the bar's typical price, and on feeds with no volume (index spot) it cannot be computed.
- **Level:** Beginner · **Goals:** levels, volume · **Added:** 2026-07-20 · **Concept:** [[concepts/VWAP]]

### Anchored VWAP (last major swing low) · `avwap`
- **Short:** Average price paid since the last major swing low, weighted by volume.
- **Desc:** Starts a volume-weighted average at the most recent major swing low and carries it forward. It shows whether everyone who bought since that low is, on average, in profit; a close back under it says they are not. The anchor is chosen automatically, so if you read a different low as the important one, the line answers a different question.
- **Level:** Intermediate · **Goals:** levels, volume · **Added:** 2026-08-02 · **Concept:** [[concepts/Anchored-VWAP-Pyramiding]]

### VWAP Mean Reversion ±σ bands + BUY/SELL · `vwmr`
- **Short:** Bands around VWAP; BUY/SELL marks when price snaps back from a band with volume.
- **Desc:** Draws bands a set number of standard deviations above and below VWAP, and marks a BUY or SELL when price stretches to an outer band and turns back with volume confirmation. It is a fade-the-stretch tool for range-bound sessions. In a strong trend price can ride the outer band for a long time and every counter-trend marker loses.
- **Level:** Intermediate · **Goals:** stretched, levels · **Added:** 2026-09-06 · **Concept:** [[concepts/VWAP]]

### MA Bias (9/20 cross · 50/200 regime) + card · `mabias`
- **Short:** One card that sums up the moving averages: trend regime, stack, trigger and caveats.
- **Desc:** Reads the 50/200 averages for the regime, the 9/20 cross for a trigger and the order of the averages (the stack), then prints a verdict card with crosses marked on the chart. Choppy conditions veto the verdict first, and a separate 'distrust' tier lists reasons not to believe it. It summarises averages, so it inherits their lag: it confirms trends rather than calling turns.
- **Level:** Beginner · **Goals:** trend · **Added:** 2026-07-23 · **Concept:** [[concepts/EMA]]

## Trend & Bands

### Bollinger (20, 2) · `bollinger`
- **Short:** A band two standard deviations around the 20-bar average — shows how stretched price is.
- **Desc:** Draws a 20-bar average with bands two standard deviations above and below. Price at the upper band is stretched relative to its recent range; bands narrowing (a squeeze) means volatility is low and often comes before a bigger move. In a strong trend price can walk along one band for weeks, so touching it is not a reversal signal by itself.
- **Level:** Beginner · **Goals:** stretched · **Added:** 2026-07-20 · **Concept:** [[concepts/Bollinger-Bands-Squeeze]]

### Donchian (20) · `donchian`
- **Short:** Highest high and lowest low of the last 20 bars — the breakout channel.
- **Desc:** Draws the highest high and lowest low of the last 20 bars, with the midline between. A close above the top line is a 20-bar breakout; the bottom line is a simple trailing exit for longs. Many breakouts fail and pull back inside, so the line marks where to look, not a confirmed move.
- **Level:** Beginner · **Goals:** levels, stop · **Added:** 2026-07-20 · **Concept:** —

### Keltner (20, 1.5) · `keltner`
- **Short:** A channel 1.5 ATR either side of the 20-bar average — volatility-sized bands.
- **Desc:** Draws a 20-bar average with bands set 1.5 times the average true range above and below. Closes outside the channel suggest a strong push; the far band is a volatility-sized reference for stops. Bands widen after big bars, so right after a shock the channel looks wide and calm-market rules do not apply.
- **Level:** Intermediate · **Goals:** stretched, stop · **Added:** 2026-07-20 · **Concept:** —

### PMax (EMA10, ATR10 × 3) + signals · `pmax`
- **Short:** Trend line that trails price by 3 ATR and flips side when the trend turns.
- **Desc:** Builds a trailing line from a 10-bar EMA plus or minus three times the 10-bar ATR, and marks buy and sell flips when the average crosses it. It keeps you on one side of the trend and gives an obvious stop level. In sideways markets it flips back and forth and each flip costs a small loss.
- **Level:** Intermediate · **Goals:** trend, stop · **Added:** 2026-07-20 · **Concept:** [[concepts/PMax]]

### SuperTrend AI (adaptive factor via K-means) + signals · `stai`
- **Short:** SuperTrend whose distance from price is picked automatically from recent performance.
- **Desc:** A SuperTrend trailing line whose ATR multiplier is chosen by grouping (K-means) how different multipliers performed recently, with buy and sell flips marked. The aim is a line that adapts to the market instead of a fixed setting. The choice is fitted on the past, so when conditions change it adapts after the fact, and flips in a range still cost money.
- **Level:** Advanced · **Goals:** trend, stop · **Added:** 2026-08-23 · **Concept:** [[concepts/SuperTrend]]

### Parabolic SAR (0.02, 0.20) · `psar`
- **Short:** Dots that trail price and jump to the other side when the trend reverses.
- **Desc:** Wilder's Parabolic SAR: dots below price in an uptrend, above in a downtrend, accelerating toward price as the trend runs (step 0.02, cap 0.20). The dots work as a trailing stop that tightens over time. In sideways markets the dots flip side constantly.
- **Level:** Beginner · **Goals:** trend, stop · **Added:** 2026-09-07 · **Concept:** —

### Ichimoku Cloud (9, 26, 52) · `ichimoku`
- **Short:** Japanese all-in-one view: trend, momentum and support in a shaded cloud.
- **Desc:** Draws the Tenkan (9) and Kijun (26) lines, the lagging line, and a cloud built from them and the 52-bar midpoint, shifted forward. Price above a rising cloud is an uptrend and the cloud is support; inside the cloud is no clear trend. Five lines and a cloud are a lot to read, and the settings were designed for a six-day trading week.
- **Level:** Advanced · **Goals:** trend, levels · **Added:** 2026-09-25 · **Concept:** —

### ATR Trailing Stop (14, 3×) + flips · `atrtrail`
- **Short:** A stop line 3 ATR away from price that only moves in the trade's favour.
- **Desc:** Trails a line three times the 14-bar average true range behind price and marks when price closes through it, flipping long to short. It sizes the stop to how much the stock normally moves, so a volatile name gets more room. Wide stops mean bigger losses per trade, and after a volatility spike the line can sit far from price.
- **Level:** Intermediate · **Goals:** stop, trend · **Added:** 2026-09-24 · **Concept:** —

### Renko structure on candles (ATR brick) + flips · `renko`
- **Short:** Renko bricks drawn over the candles — trend structure with small wiggles removed.
- **Desc:** Builds Renko bricks sized by ATR (a new brick only when price moves a full brick) and draws that staircase over the candles, marking where the brick direction flips. It filters out small moves so the trend is easier to see. Bricks ignore time and the latest brick can be pending, so the chart can look calmer than it is.
- **Level:** Intermediate · **Goals:** trend · **Added:** 2026-08-30 · **Concept:** [[concepts/Renko-Charts]]

## Oscillators

### RSI (14) · `rsi`
- **Short:** Momentum from 0 to 100; above 70 is stretched up, below 30 stretched down.
- **Desc:** The 14-bar Relative Strength Index in its own pane, comparing recent up-closes with down-closes on a 0–100 scale. Above 70 is read as overbought, below 30 as oversold, and 50 as the line between up and down momentum. In strong trends RSI can stay above 70 or below 30 for a long time, so overbought is not a sell signal on its own.
- **Level:** Beginner · **Goals:** stretched · **Added:** 2026-07-20 · **Concept:** [[concepts/RSI]]

### MACD (12, 26, 9) · `macd`
- **Short:** Gap between a fast and slow average — shows momentum building or fading.
- **Desc:** MACD (12, 26, 9) in its own pane: the line is the gap between two exponential averages, the signal line smooths it, and the histogram shows the difference. MACD crossing above its signal line suggests momentum turning up; the histogram shrinking shows it fading. It is built from averages, so its crosses come after the turn and whipsaw in ranges.
- **Level:** Beginner · **Goals:** trend · **Added:** 2026-07-20 · **Concept:** [[concepts/MACD-Divergence]]

### OBV · `obv`
- **Short:** Running total of volume on up days minus down days — is volume backing the trend?
- **Desc:** On-Balance Volume in its own pane: adds the day's volume when the close is up and subtracts it when down. OBV rising with price says volume is supporting the move; OBV flat while price rises is a warning sign. One huge-volume day can shift the line for months, and the level itself means nothing — only its direction.
- **Level:** Beginner · **Goals:** volume, trend · **Added:** 2026-07-20 · **Concept:** [[concepts/On-Balance-Volume]]

### RS vs Benchmark · `rs`
- **Short:** This stock divided by Nifty 50 — rising means it is beating the market.
- **Desc:** Plots the stock's price divided by the benchmark (Nifty 50 for Indian symbols, Bitcoin for crypto), rebased so 100 is the starting point. A rising line means the stock is outperforming even if both are falling. It compares with the index only, so a stock can lead the index while lagging its own sector.
- **Level:** Beginner · **Goals:** trend · **Added:** 2026-07-20 · **Concept:** [[concepts/Mansfield-RS]]

### %R Trend Exhaustion (+ chart arrows / OB confluence) · `prte`
- **Short:** Williams %R exhaustion: flags when a run looks spent, with arrows on the chart.
- **Desc:** Uses short and long Williams %R in a pane to spot when both sit at an extreme and then turn, marking exhaustion arrows on the price chart and noting where they line up with an order block. It is a reversal-watch tool for stretched moves. Strong trends can stay exhausted-looking for a long time, and arrows against the trend fail more often.
- **Level:** Intermediate · **Goals:** stretched · **Added:** 2026-07-20 · **Concept:** [[concepts/Percent-R-Trend-Exhaustion]]

### ADX + DI (trend strength & direction) · `adxdi`
- **Short:** How strong the trend is (ADX), and whether buyers or sellers lead (+DI / −DI).
- **Desc:** ADX in its own pane measures trend strength regardless of direction; +DI and −DI show which side is in control, with their crosses marked. ADX rising above about 20–25 suggests a real trend; below that, a range. ADX is slow and peaks late, so a falling ADX can mean the trend is pausing rather than ending.
- **Level:** Intermediate · **Goals:** trend · **Added:** 2026-08-26 · **Concept:** [[concepts/ADX]]

### EVWMA VWAP MACD (30,5,20) + BUY/SELL · `evmacd`
- **Short:** MACD built from a volume-weighted average vs VWAP, with BUY/SELL marks.
- **Desc:** A MACD-style pane comparing an elastic volume-weighted moving average with VWAP (session VWAP on intraday bars, typical price on daily), with a signal line, histogram and BUY/SELL marks on crosses. It brings volume into a momentum read. Like any MACD it lags and whipsaws in ranges, and on daily bars the VWAP leg is only a typical-price stand-in.
- **Level:** Advanced · **Goals:** trend, volume · **Added:** 2026-08-30 · **Concept:** [[concepts/EVWMA-VWAP-MACD]]

### ROC + RSI Zones (21,5,5,14) · `roc`
- **Short:** Rate of change over 21 bars with RSI zones — how fast price is moving.
- **Desc:** Plots the 21-bar rate of change with its smoothing and RSI-based zones in a pane; red shading above zero warns of overheating, green below zero marks a washed-out move. It shows speed, which often fades before price turns. Speed can stay high in a strong trend, and the shading is a contrarian reading, not a timing signal.
- **Level:** Intermediate · **Goals:** stretched · **Added:** 2026-07-20 · **Concept:** —

### Stochastic (14,3,3) · `stoch`
- **Short:** Where the close sits within the recent high–low range, 0 to 100.
- **Desc:** The Stochastic (14, 3, 3) in its own pane: near 100 the close is at the top of the last 14 bars' range, near 0 at the bottom, with a smoothed signal line. Above 80 is read as overbought, below 20 as oversold, and crosses of the two lines as turns. It is fast and noisy, and in trends it pins at one extreme.
- **Level:** Beginner · **Goals:** stretched · **Added:** 2026-07-20 · **Concept:** [[concepts/Stochastic-Oscillator]]

### MFI (14) · volume-weighted RSI · `mfi`
- **Short:** RSI that counts volume — stretched readings backed (or not) by money flow.
- **Desc:** The 14-bar Money Flow Index in its own pane, like RSI but weighted by volume and typical price. Above 80 is overbought, below 20 oversold, and a gap between MFI and price direction hints that volume is not confirming. A single heavy-volume day moves it a lot, and like RSI it can stay extreme in a trend.
- **Level:** Intermediate · **Goals:** stretched, volume · **Added:** 2026-09-11 · **Concept:** —

### ATR (14) · Wilder — stop sizing · `atr`
- **Short:** Average daily range (Wilder ATR 14) — use it to size stops and positions.
- **Desc:** Plots Wilder's 14-bar Average True Range in its own pane: how far the stock typically moves in a bar, gaps included. Use it to set a stop a sensible distance away and to size the position so a stop-out costs a fixed amount. It says nothing about direction, and it rises after big moves, so it describes the recent past rather than the next bar.
- **Level:** Beginner · **Goals:** stop · **Added:** 2026-09-11 · **Concept:** —

### HM Bottoms & Tops (RSI9 · EMA3 · VWMA21) · `hm`
- **Short:** Hilega-Milega: RSI 9 with its EMA and volume-weighted average, shading strength.
- **Desc:** Draws RSI (9) with a 3-bar EMA of it and a 21-bar volume-weighted average of it in a taller pane, shading above 50 warm and below 50 cool, with entry and exit markers. RSI above both averages is read as strength, below both as weakness. Three lines on a 0–100 scale cross often, and the markers fire in ranges as readily as in trends.
- **Level:** Advanced · **Goals:** stretched, trend · **Added:** 2026-08-21 · **Concept:** —

### RSI Divergence (regular + hidden) · `rsidiv`
- **Short:** Marks where price and RSI disagree — an early hint a move is tiring.
- **Desc:** Finds regular divergences (price makes a new high or low that RSI does not) and hidden divergences (the reverse, read as trend continuation), drawn on both the price chart and the RSI pane. Turning it on also turns RSI on. Divergence needs a confirmed swing, so it is marked a few bars late, and in strong trends divergences can stack up one after another before any turn.
- **Level:** Intermediate · **Goals:** stretched · **Added:** 2026-08-07 · **Concept:** [[concepts/RSI]]

### OBV Divergence (regular + hidden) · `obvdiv`
- **Short:** Marks where price and On-Balance Volume disagree — is volume leaving the move?
- **Desc:** Finds regular and hidden divergences between price swings and OBV swings and marks them on the chart. A new price high with a lower OBV high says volume is not following the move. Like all divergence tools it confirms only after a swing completes, and OBV can be distorted by one unusual volume day.
- **Level:** Intermediate · **Goals:** volume, stretched · **Added:** 2026-09-07 · **Concept:** [[concepts/On-Balance-Volume]]

## Volume

### Volume · `volume`
- **Short:** Volume bars under the candles — how much traded each bar.
- **Desc:** Draws each bar's volume as a histogram along the bottom of the price chart, coloured by up or down bar. A breakout on volume well above normal is more convincing than one on thin volume. Volume is relative: compare with the stock's own recent bars, not with other stocks, and index spot feeds carry no volume at all.
- **Level:** Beginner · **Goals:** volume · **Added:** 2026-07-20 · **Concept:** [[concepts/Volume-Analysis]]

### Simple Volume (Pocket Pivots — PPV / dry / above-average) · `simplevol`
- **Short:** Volume bars highlighted: pocket pivots, dry-ups and above-average days.
- **Desc:** Colours volume bars by meaning: pocket-pivot days (an up day whose volume beats any down day of the last ten), dry-up days (unusually low volume) and above-average days. Pocket pivots inside a base are read as quiet accumulation; dry-ups near a pivot as sellers stepping back. These are labels, not signals: a pocket pivot in a downtrend means much less.
- **Level:** Intermediate · **Goals:** volume · **Added:** 2026-09-22 · **Concept:** [[concepts/Pocket-Pivot]]

### Volume Profile (POC/VA/HVN/LVN) · `volprofile`
- **Short:** How much volume traded at each price — shows the levels the market cares about.
- **Desc:** Draws a sideways histogram of volume by price over the loaded bars, marking the point of control (most-traded price), the value area, and high- and low-volume nodes. High-volume nodes tend to act as support or resistance; low-volume nodes are prices the market moved through quickly. It depends on the window loaded, so zooming or changing the timeframe changes the levels.
- **Level:** Intermediate · **Goals:** levels, volume · **Added:** 2026-07-20 · **Concept:** [[concepts/Volume-Profile]]

### Session Volume Profile HD (D/P/B/I + Accum/Distrib) · `svp`
- **Short:** A volume profile per session, with its shape (D/P/B/I) and accumulation read.
- **Desc:** Builds a separate volume profile for each session and labels its shape: D (balanced), P (buying high in the range), B (selling low in the range) and I (one-way trend), plus an accumulation or distribution read. It shows how each session's auction went, not just the overall levels. Shapes need enough intraday data to mean anything, and the reads have not been measured as signals.
- **Level:** Advanced · **Goals:** levels, volume · **Added:** 2026-08-20 · **Concept:** [[concepts/Volume-Profile]]

### TPO / Market Profile (time-at-price) · `tpo`
- **Short:** Market Profile: how much TIME price spent at each level, letter by letter.
- **Desc:** Builds a Time-Price-Opportunity profile: each period that trades at a price adds a letter there, with the initial balance (opening range) marked. Wide areas of letters are prices the market accepted; thin single prints are prices it rejected. It needs intraday bars, and the profile shape depends on the period length chosen.
- **Level:** Advanced · **Goals:** levels · **Added:** 2026-09-25 · **Concept:** [[concepts/Initial-Balance]]

### Delta Profile — real taker side (Hyperliquid only) · `deltaprofile`
- **Short:** Real buyer-versus-seller volume at each price — Hyperliquid crypto only.
- **Desc:** Draws volume by price split into aggressive buying and aggressive selling, taken from the exchange's own taker-side trade data rather than estimated from candles. Prices where sellers dominated on a rising market can show absorption. It only works for Hyperliquid symbols; NSE daily data has no taker side, so there is nothing to draw for Indian stocks.
- **Level:** Advanced · **Goals:** volume, levels · **Added:** 2026-09-05 · **Concept:** [[concepts/Order-Flow]]

## Price Patterns

### Rounding Bottom (saucer) · `roundbottom`
- **Short:** Finds saucer-shaped bottoms — a slow, rounded turn from down to up.
- **Desc:** Detects rounding-bottom (saucer) bases and shades the base zone on the chart. A slow, rounded base followed by a push through its rim is a classic accumulation picture. The shape is judged after the fact, a saucer can keep extending sideways, and many never break out.
- **Level:** Beginner · **Goals:** target · **Added:** 2026-07-20 · **Concept:** [[concepts/Rounding-Bottom]]

### Double Bottom (neckline + quality grade) · `doublebottom`
- **Short:** W-shaped double bottoms with the neckline drawn and a quality grade.
- **Desc:** Finds two lows at a similar level with a peak between them, draws the neckline (the peak's level) and grades the pattern's quality, including the retest and follow-through. A close above the neckline is the usual confirmation. Before that close it is only a possible pattern, and in a strong downtrend second lows often break.
- **Level:** Beginner · **Goals:** target, levels · **Added:** 2026-09-19 · **Concept:** [[concepts/Reversal-Chart-Patterns]]

### VCP Coiling · `vcp`
- **Short:** Volatility contraction: a base whose pullbacks get smaller and quieter.
- **Desc:** Detects Minervini-style volatility contraction patterns — successive pullbacks each shallower than the last, usually with volume drying up — and shades the coiling zone. Tight action near the highs is read as supply being absorbed before a breakout. Many coils break down instead of up, and the pattern is defined loosely enough that it is easy to see one that is not there.
- **Level:** Intermediate · **Goals:** target · **Added:** 2026-07-20 · **Concept:** [[concepts/VCP]]

### Falling Wedge (converging → breakout) · `falling_wedge`
- **Short:** Falling wedge: price squeezing down between two converging lines, then breaking out.
- **Desc:** Detects a falling wedge — lower highs and lower lows drawing two lines that converge — and marks a breakout above the upper line. It is usually read as selling pressure fading. Wedges can break down as well as up, and lines fitted to a handful of swings are fragile.
- **Level:** Intermediate · **Goals:** target · **Added:** 2026-07-27 · **Concept:** [[concepts/Falling-Wedge]]

### Flag & Pole + measured-move plan (both directions) · `flag_pole`
- **Short:** Flag and pole: a sharp move, a tight pause, and a measured-move target.
- **Desc:** Finds a sharp move (the pole) followed by a tight, slightly counter-trend pause (the flag), in either direction, and draws a plan with entry, stop and a measured-move target equal to the pole's length. Flags are continuation patterns: the trend is expected to resume. The measured move is a rule of thumb, not a forecast, and flags that drift too long or too deep often fail.
- **Level:** Intermediate · **Goals:** target, stop · **Added:** 2026-09-17 · **Concept:** [[concepts/Chart-Patterns]]

### Harmonic (Gartley/Bat/Butterfly/Crab + AB=CD) · `harmonic`
- **Short:** Harmonic patterns (Gartley, Bat, Butterfly, Crab, AB=CD) from Fibonacci ratios.
- **Desc:** Finds five-point XABCD swings whose leg ratios match the named harmonic patterns, or the simpler AB=CD, and marks the completion zone where the pattern expects a reversal. It gives a precise price zone to watch. The ratios have tolerances, so patterns are easy to find in any noisy chart, and a completion zone is a place to look, not a turn.
- **Level:** Advanced · **Goals:** target, levels · **Added:** 2026-07-20 · **Concept:** —

### Gann S/R + Break Odds (Square-of-9 + historical follow-through) · `gann`
- **Short:** Gann Square-of-9 support/resistance, with how often past breaks followed through.
- **Desc:** Draws support and resistance levels from Gann's Square of Nine around the current price and shows a card with how often, on this symbol's own history, a break of such a level carried on. The levels come from a geometric rule, not from where trading happened. The follow-through numbers describe this symbol's past only and are not a promise about the next break.
- **Level:** Advanced · **Goals:** levels · **Added:** 2026-08-18 · **Concept:** [[concepts/Gann-Angles-And-Trend-Change-Levels]]

## Smart Money & Structure

### Fair Value Gap + Buy/Sell signal (FPV) · `fvg`
- **Short:** Price gaps left by fast moves (fair value gaps), with buy/sell marks when they hold.
- **Desc:** Shades three-bar gaps where price moved so fast that a range was left untraded, and marks a buy or sell when price returns to a gap and respects it. Traders watch these gaps as places price may come back to fill. Many gaps are simply filled and run through, and small gaps on a busy chart are mostly noise.
- **Level:** Intermediate · **Goals:** levels · **Added:** 2026-07-20 · **Concept:** [[concepts/Fair-Value-Gap]]

### Trendlines (supply/demand) · `trendlines`
- **Short:** Automatic trendlines along swing highs (supply) and swing lows (demand).
- **Desc:** Connects recent swing highs into a falling supply line and swing lows into a rising demand line. A close through a supply line suggests sellers have weakened; a break of a demand line, buyers. Lines depend on which swings the algorithm picks, they are redrawn as new swings form, and price often pierces a line before deciding.
- **Level:** Beginner · **Goals:** levels, trend · **Added:** 2026-07-20 · **Concept:** [[concepts/Trend-Lines]]

### Structure Break Chain (BOS/CHoCH + quality) · `structure_chain`
- **Short:** Breaks of market structure: BOS continues the trend, CHoCH flags a possible turn.
- **Desc:** Tracks swing highs and lows and marks each Break of Structure (price breaks a swing in the trend's direction) and Change of Character (it breaks one against the trend), with a quality rating for each break. A chain of BOS shows a healthy trend; a CHoCH is the first sign it may be turning. Breaks are confirmed only after a swing completes, and in ranges BOS and CHoCH alternate with little meaning.
- **Level:** Intermediate · **Goals:** trend, levels · **Added:** 2026-07-30 · **Concept:** [[concepts/Market-Structure-CHOCH-BOS]]

### Order Blocks (SMC demand / supply zones) · `orderblock`
- **Short:** Smart-money zones: the last opposite candle before a strong move.
- **Desc:** Shades order blocks — the last down candle before a strong rally (demand) or the last up candle before a sharp drop (supply) — and tracks when price returns to them. Traders watch these zones as places a big participant may defend. The idea of institutional footprints is a story, not something the data shows directly, and many zones are run through on the first touch.
- **Level:** Advanced · **Goals:** levels · **Added:** 2026-08-21 · **Concept:** [[concepts/Order-Blocks]]

### Liquidity Pools + Sweep + BUY signal (equal highs/lows · stop run) · `liquidity`
- **Short:** Clusters of equal highs/lows where stops sit, and BUY when a sweep below reclaims.
- **Desc:** Marks liquidity pools — equal highs or lows where stop orders tend to cluster — and flags a sweep when price pokes through one and closes back. A sweep below a pool that reclaims the level gets a BUY mark; a sweep above is shown as risk only, with no SELL. These are the same detector functions the desk's Liquidity Sweep scanner uses. A sweep can also be the start of a real breakdown, so the reclaim matters more than the poke.
- **Level:** Advanced · **Goals:** levels · **Added:** 2026-09-11 · **Concept:** [[concepts/Equal-Highs-Lows]]

## Levels & Projection

### Elliott Wave (1-5, A-B-C, W-X-Y) · `elliott`
- **Short:** Automatic Elliott Wave count: impulse 1–5 and corrections A-B-C or W-X-Y.
- **Desc:** Finds swing points and labels them as an Elliott Wave count — a five-wave move with the trend and three-wave corrections against it, including complex W-X-Y corrections. It gives a map of where in a larger move price might be. Wave counts are subjective, the count can change as new swings form, and two analysts (or two settings) often disagree.
- **Level:** Advanced · **Goals:** trend, target · **Added:** 2026-07-20 · **Concept:** [[concepts/Elliott-Wave]]

### Elliott Wave · larger degree (nesting) · `ew2deg`
- **Short:** The same wave count at a larger scale, drawn over the normal one.
- **Desc:** Runs the Elliott Wave engine with a larger swing size and draws that count over the normal one, so you can see small waves nested inside bigger ones. It helps tell a correction inside an uptrend from the start of a downtrend. Everything that makes wave counts uncertain applies twice here, and the larger count changes less often but by more when it does.
- **Level:** Advanced · **Goals:** trend, target · **Added:** 2026-10-12 · **Concept:** [[concepts/Elliott-Wave]]

### Price Projection (EW + patterns) · `projection`
- **Short:** Where price could go next: targets from the wave count and detected patterns.
- **Desc:** Combines targets from the Elliott Wave count and from detected chart patterns into projected price levels and paths drawn ahead of the last bar. It answers 'if this pattern plays out, where does it point?'. Projections inherit every uncertainty of the patterns behind them and are scenarios, not forecasts.
- **Level:** Intermediate · **Goals:** target · **Added:** 2026-07-20 · **Concept:** —

### CPR (TC / Pivot / BC + R1 / S1, prior bar) · `cpr`
- **Short:** Central Pivot Range from the prior bar: today's pivot, its band, and R1/S1.
- **Desc:** Computes the pivot, top central (TC) and bottom central (BC) levels from the previous bar's high, low and close, plus the first resistance (R1) and support (S1), and draws them for the current bar. A narrow CPR often comes before a trending day, a wide one before a range; opening above the band is read as bullish. The levels are arithmetic, not traded prices, so they matter only as much as other traders watch them.
- **Level:** Beginner · **Goals:** levels · **Added:** 2026-09-28 · **Concept:** [[concepts/CPR-Central-Pivot-Range]]

### Fibonacci + Trade Plan (VP + Projection confluence) · `fib`
- **Short:** Fibonacci retracement levels on the last swing, plus a trade plan where levels agree.
- **Desc:** Draws Fibonacci retracement levels (38.2%, 50%, 61.8% and others) across the most recent major swing, and builds a trade plan where those levels line up with volume-profile levels and the price projection. Pullbacks often pause near the 38–62% zone. The swing is picked automatically, there are many levels so one is always near price, and agreement between levels is a reason to watch, not a measured edge.
- **Level:** Intermediate · **Goals:** levels, target, stop · **Added:** 2026-07-21 · **Concept:** [[concepts/Fibonacci-Retracement]]

### Option OI Walls + Max Pain (F&O names only, per expiry) · `oiwalls`
- **Short:** Option strikes with the most open interest (walls) and max pain — F&O names only.
- **Desc:** For stocks with listed options, draws the call strike with the largest open interest (a ceiling traders watch), the put strike with the largest (a floor), and the max-pain strike for the chosen expiry. These show where option sellers have the most at stake. The ideas that price gravitates to max pain or bounces off a wall are untested folk claims, and the walls move as positions change during the day.
- **Level:** Advanced · **Goals:** levels · **Added:** 2026-09-02 · **Concept:** —

## Calendar

### Reversal Calendar (Yogas + Lunar) · `reversal_calendar`
- **Short:** Marks dates of Vedic yogas and lunar phases that some traders watch for turns.
- **Desc:** Marks calendar dates of selected Vedic yogas and lunar phases on the time axis. Some traders use these dates as moments to watch for a change in direction. The dates come from astrological rules, not from price or volume, so treat them as a calendar to keep an eye on, not as a forecast.
- **Level:** Intermediate · **Goals:** — · **Added:** 2026-07-20 · **Concept:** [[concepts/Vedic-Calendar-Volatility-Triggers]]
