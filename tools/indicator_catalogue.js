// indicator_catalogue.js — plain-words content for every INDICATOR_DEFS entry (B-149).
//
// DRAFT, written by Claude 2026-10-14 from the code and the wiki concept pages;
// the owner reviews it before any panel shows it (review sheet:
// trading-wiki/wiki/analyses/Indicator-Catalogue-Draft-Review.md). Kept out of
// chart_dashboard.html so the words can be reviewed and edited in one place.
//
// Per key:
//   short    ≤ 90 chars, beginner wording — the card line
//   desc     2–4 sentences: what it draws · how to read it · when it misleads
//   level    Beginner | Intermediate | Advanced
//   goals    B-156 chips it answers (ids in INDICATOR_GOALS)
//   added    first commit containing key:'<key>' (git log -S). 2026-07-20 is the
//            day the chart file entered git, so it means "on or before".
//   concept  wiki concept page, or null where none exists
//
// No evidence claims here: what the desk has MEASURED belongs to B-154's verdict
// line. test_indicator_catalogue.py rejects promise words ("guaranteed",
// "high probability", "winning", "best") and checks every def has an entry.
//
// The object between the markers is strict JSON so the Python test can read it.
// "draft" shows a "Draft — under review" tag in the browser (B-150); the owner
// flips it to "approved" once the text below has been read and corrected.
window.INDICATOR_CATALOGUE_STATUS = "draft";
window.INDICATOR_GOALS = {
  "trend":     "Which way is it trending?",
  "stretched": "Is it stretched / overbought?",
  "levels":    "Where is support or resistance?",
  "volume":    "Is real volume behind the move?",
  "target":    "Where could price go next?",
  "stop":      "Where should my stop be?"
};
window.INDICATOR_INFO = /*JSON-BEGIN*/{
  "sma20": {
    "short": "Average close of the last 20 bars — the short-term trend line.",
    "desc": "Draws the plain average of the last 20 closes as a line on price. Price holding above a rising line is a short-term uptrend; below a falling one, a downtrend. In a sideways market price crosses it back and forth and every cross is noise.",
    "level": "Beginner", "goals": ["trend"], "added": "2026-07-20", "concept": null
  },
  "sma50": {
    "short": "Average close of the last 50 bars — the medium-term trend most traders watch.",
    "desc": "Draws the average of the last 50 closes. Many swing traders treat it as the line a healthy uptrend should hold on pullbacks. It reacts slowly, so by the time price clearly breaks it a good part of the move is often over.",
    "level": "Beginner", "goals": ["trend", "levels"], "added": "2026-07-20", "concept": null
  },
  "sma200": {
    "short": "Average close of the last 200 bars — the long-term trend divider.",
    "desc": "Draws the average of the last 200 closes, roughly a year of daily bars. Above it is broadly read as a long-term uptrend, below it as a downtrend. It is very slow: it says little about the next few weeks and needs 200 bars of history before it appears at all.",
    "level": "Beginner", "goals": ["trend", "levels"], "added": "2026-07-20", "concept": null
  },
  "ema9": {
    "short": "Fast exponential average of 9 bars — hugs price, shows short swings.",
    "desc": "An average that weights recent closes more, so it turns faster than a simple average. Useful for seeing whether the latest swing is still pushing in one direction. Because it is fast it whipsaws often; on its own it is not a trend filter.",
    "level": "Beginner", "goals": ["trend"], "added": "2026-07-23", "concept": "concepts/EMA.md"
  },
  "ema20": {
    "short": "20-bar exponential average — the line strong trends tend to pull back to.",
    "desc": "A 20-bar average weighted toward recent closes. In a steady trend, pullbacks often stop near it, which is why it is a common pullback reference. In choppy markets price slices through it repeatedly and the line goes flat.",
    "level": "Beginner", "goals": ["trend", "levels"], "added": "2026-07-20", "concept": "concepts/EMA.md"
  },
  "ema50": {
    "short": "50-bar exponential average — medium-term trend, turns sooner than the SMA 50.",
    "desc": "A 50-bar average weighted toward recent closes. Read it like the SMA 50: price above a rising line is a medium-term uptrend. It turns earlier than the simple version, which also means it gives more false turns.",
    "level": "Beginner", "goals": ["trend", "levels"], "added": "2026-07-20", "concept": "concepts/EMA.md"
  },
  "ema200": {
    "short": "200-bar exponential average — the long-term trend line, weighted to recent bars.",
    "desc": "A 200-bar average weighted toward recent closes. Above it is the long-term up side, below it the down side. It needs a long history to settle and on a young listing it is little more than a guess.",
    "level": "Beginner", "goals": ["trend", "levels"], "added": "2026-07-20", "concept": "concepts/EMA.md"
  },
  "vwap": {
    "short": "Average price paid today, weighted by volume — intraday charts only.",
    "desc": "Draws the running volume-weighted average price for each session. Price above it means today's buyers are, on average, in profit; below it, in loss. It only means something on intraday bars: on a daily chart each bar is its own session and the line is just the bar's typical price, and on feeds with no volume (index spot) it cannot be computed.",
    "level": "Beginner", "goals": ["levels", "volume"], "added": "2026-07-20", "concept": "concepts/VWAP.md"
  },
  "avwap": {
    "short": "Average price paid since the last major swing low, weighted by volume.",
    "desc": "Starts a volume-weighted average at the most recent major swing low and carries it forward. It shows whether everyone who bought since that low is, on average, in profit; a close back under it says they are not. The anchor is chosen automatically, so if you read a different low as the important one, the line answers a different question.",
    "level": "Intermediate", "goals": ["levels", "volume"], "added": "2026-08-02", "concept": "concepts/Anchored-VWAP-Pyramiding.md"
  },
  "vwmr": {
    "short": "Bands around VWAP; BUY/SELL marks when price snaps back from a band with volume.",
    "desc": "Draws bands a set number of standard deviations above and below VWAP, and marks a BUY or SELL when price stretches to an outer band and turns back with volume confirmation. It is a fade-the-stretch tool for range-bound sessions. In a strong trend price can ride the outer band for a long time and every counter-trend marker loses.",
    "level": "Intermediate", "goals": ["stretched", "levels"], "added": "2026-09-06", "concept": "concepts/VWAP.md"
  },
  "mabias": {
    "short": "One card that sums up the moving averages: trend regime, stack, trigger and caveats.",
    "desc": "Reads the 50/200 averages for the regime, the 9/20 cross for a trigger and the order of the averages (the stack), then prints a verdict card with crosses marked on the chart. Choppy conditions veto the verdict first, and a separate 'distrust' tier lists reasons not to believe it. It summarises averages, so it inherits their lag: it confirms trends rather than calling turns.",
    "level": "Beginner", "goals": ["trend"], "added": "2026-07-23", "concept": "concepts/EMA.md"
  },
  "bollinger": {
    "short": "A band two standard deviations around the 20-bar average — shows how stretched price is.",
    "desc": "Draws a 20-bar average with bands two standard deviations above and below. Price at the upper band is stretched relative to its recent range; bands narrowing (a squeeze) means volatility is low and often comes before a bigger move. In a strong trend price can walk along one band for weeks, so touching it is not a reversal signal by itself.",
    "level": "Beginner", "goals": ["stretched"], "added": "2026-07-20", "concept": "concepts/Bollinger-Bands-Squeeze.md"
  },
  "donchian": {
    "short": "Highest high and lowest low of the last 20 bars — the breakout channel.",
    "desc": "Draws the highest high and lowest low of the last 20 bars, with the midline between. A close above the top line is a 20-bar breakout; the bottom line is a simple trailing exit for longs. Many breakouts fail and pull back inside, so the line marks where to look, not a confirmed move.",
    "level": "Beginner", "goals": ["levels", "stop"], "added": "2026-07-20", "concept": null
  },
  "keltner": {
    "short": "A channel 1.5 ATR either side of the 20-bar average — volatility-sized bands.",
    "desc": "Draws a 20-bar average with bands set 1.5 times the average true range above and below. Closes outside the channel suggest a strong push; the far band is a volatility-sized reference for stops. Bands widen after big bars, so right after a shock the channel looks wide and calm-market rules do not apply.",
    "level": "Intermediate", "goals": ["stretched", "stop"], "added": "2026-07-20", "concept": null
  },
  "pmax": {
    "short": "Trend line that trails price by 3 ATR and flips side when the trend turns.",
    "desc": "Builds a trailing line from a 10-bar EMA plus or minus three times the 10-bar ATR, and marks buy and sell flips when the average crosses it. It keeps you on one side of the trend and gives an obvious stop level. In sideways markets it flips back and forth and each flip costs a small loss.",
    "level": "Intermediate", "goals": ["trend", "stop"], "added": "2026-07-20", "concept": "concepts/PMax.md"
  },
  "stai": {
    "short": "SuperTrend whose distance from price is picked automatically from recent performance.",
    "desc": "A SuperTrend trailing line whose ATR multiplier is chosen by grouping (K-means) how different multipliers performed recently, with buy and sell flips marked. The aim is a line that adapts to the market instead of a fixed setting. The choice is fitted on the past, so when conditions change it adapts after the fact, and flips in a range still cost money.",
    "level": "Advanced", "goals": ["trend", "stop"], "added": "2026-08-23", "concept": "concepts/SuperTrend.md"
  },
  "psar": {
    "short": "Dots that trail price and jump to the other side when the trend reverses.",
    "desc": "Wilder's Parabolic SAR: dots below price in an uptrend, above in a downtrend, accelerating toward price as the trend runs (step 0.02, cap 0.20). The dots work as a trailing stop that tightens over time. In sideways markets the dots flip side constantly.",
    "level": "Beginner", "goals": ["trend", "stop"], "added": "2026-09-07", "concept": null
  },
  "ichimoku": {
    "short": "Japanese all-in-one view: trend, momentum and support in a shaded cloud.",
    "desc": "Draws the Tenkan (9) and Kijun (26) lines, the lagging line, and a cloud built from them and the 52-bar midpoint, shifted forward. Price above a rising cloud is an uptrend and the cloud is support; inside the cloud is no clear trend. Five lines and a cloud are a lot to read, and the settings were designed for a six-day trading week.",
    "level": "Advanced", "goals": ["trend", "levels"], "added": "2026-09-25", "concept": null
  },
  "atrtrail": {
    "short": "A stop line 3 ATR away from price that only moves in the trade's favour.",
    "desc": "Trails a line three times the 14-bar average true range behind price and marks when price closes through it, flipping long to short. It sizes the stop to how much the stock normally moves, so a volatile name gets more room. Wide stops mean bigger losses per trade, and after a volatility spike the line can sit far from price.",
    "level": "Intermediate", "goals": ["stop", "trend"], "added": "2026-09-24", "concept": null
  },
  "riskbox": {
    "short": "Draws entry, stop and 1R/2R/3R lines and works out how many shares to buy.",
    "desc": "Takes an entry and a stop (by default the last close and the trade card's own stop rule) and draws them with targets at one, two and three times the risk. It sizes the position so that hitting the stop loses a fixed slice of your capital, 2% unless you change it. It is arithmetic about risk, not a buy signal, and the 2% figure is a starting assumption rather than a tested number.",
    "level": "Beginner", "goals": ["stop", "target"], "added": "2026-10-15", "concept": null
  },
  "renko": {
    "short": "Renko bricks drawn over the candles — trend structure with small wiggles removed.",
    "desc": "Builds Renko bricks sized by ATR (a new brick only when price moves a full brick) and draws that staircase over the candles, marking where the brick direction flips. It filters out small moves so the trend is easier to see. Bricks ignore time and the latest brick can be pending, so the chart can look calmer than it is.",
    "level": "Intermediate", "goals": ["trend"], "added": "2026-08-30", "concept": "concepts/Renko-Charts.md"
  },
  "rsi": {
    "short": "Momentum from 0 to 100; above 70 is stretched up, below 30 stretched down.",
    "desc": "The 14-bar Relative Strength Index in its own pane, comparing recent up-closes with down-closes on a 0–100 scale. Above 70 is read as overbought, below 30 as oversold, and 50 as the line between up and down momentum. In strong trends RSI can stay above 70 or below 30 for a long time, so overbought is not a sell signal on its own.",
    "level": "Beginner", "goals": ["stretched"], "added": "2026-07-20", "concept": "concepts/RSI.md"
  },
  "macd": {
    "short": "Gap between a fast and slow average — shows momentum building or fading.",
    "desc": "MACD (12, 26, 9) in its own pane: the line is the gap between two exponential averages, the signal line smooths it, and the histogram shows the difference. MACD crossing above its signal line suggests momentum turning up; the histogram shrinking shows it fading. It is built from averages, so its crosses come after the turn and whipsaw in ranges.",
    "level": "Beginner", "goals": ["trend"], "added": "2026-07-20", "concept": "concepts/MACD-Divergence.md"
  },
  "obv": {
    "short": "Running total of volume on up days minus down days — is volume backing the trend?",
    "desc": "On-Balance Volume in its own pane: adds the day's volume when the close is up and subtracts it when down. OBV rising with price says volume is supporting the move; OBV flat while price rises is a warning sign. One huge-volume day can shift the line for months, and the level itself means nothing — only its direction.",
    "level": "Beginner", "goals": ["volume", "trend"], "added": "2026-07-20", "concept": "concepts/On-Balance-Volume.md"
  },
  "rs": {
    "short": "This stock divided by Nifty 50 — rising means it is beating the market.",
    "desc": "Plots the stock's price divided by the benchmark (Nifty 50 for Indian symbols, Bitcoin for crypto), rebased so 100 is the starting point. A rising line means the stock is outperforming even if both are falling. It compares with the index only, so a stock can lead the index while lagging its own sector.",
    "level": "Beginner", "goals": ["trend", "target"], "added": "2026-07-20", "concept": "concepts/Mansfield-RS.md"
  },
  "prte": {
    "short": "Williams %R exhaustion: flags when a run looks spent, with arrows on the chart.",
    "desc": "Uses short and long Williams %R in a pane to spot when both sit at an extreme and then turn, marking exhaustion arrows on the price chart and noting where they line up with an order block. It is a reversal-watch tool for stretched moves. Strong trends can stay exhausted-looking for a long time, and arrows against the trend fail more often.",
    "level": "Intermediate", "goals": ["stretched"], "added": "2026-07-20", "concept": "concepts/Percent-R-Trend-Exhaustion.md"
  },
  "adxdi": {
    "short": "How strong the trend is (ADX), and whether buyers or sellers lead (+DI / −DI).",
    "desc": "ADX in its own pane measures trend strength regardless of direction; +DI and −DI show which side is in control, with their crosses marked. ADX rising above about 20–25 suggests a real trend; below that, a range. ADX is slow and peaks late, so a falling ADX can mean the trend is pausing rather than ending.",
    "level": "Intermediate", "goals": ["trend"], "added": "2026-08-26", "concept": "concepts/ADX.md"
  },
  "evmacd": {
    "short": "MACD built from a volume-weighted average vs VWAP, with BUY/SELL marks.",
    "desc": "A MACD-style pane comparing an elastic volume-weighted moving average with VWAP (session VWAP on intraday bars, typical price on daily), with a signal line, histogram and BUY/SELL marks on crosses. It brings volume into a momentum read. Like any MACD it lags and whipsaws in ranges, and on daily bars the VWAP leg is only a typical-price stand-in.",
    "level": "Advanced", "goals": ["trend", "volume"], "added": "2026-08-30", "concept": "concepts/EVWMA-VWAP-MACD.md"
  },
  "roc": {
    "short": "Rate of change over 21 bars with RSI zones — how fast price is moving.",
    "desc": "Plots the 21-bar rate of change with its smoothing and RSI-based zones in a pane; red shading above zero warns of overheating, green below zero marks a washed-out move. It shows speed, which often fades before price turns. Speed can stay high in a strong trend, and the shading is a contrarian reading, not a timing signal.",
    "level": "Intermediate", "goals": ["stretched"], "added": "2026-07-20", "concept": null
  },
  "stoch": {
    "short": "Where the close sits within the recent high–low range, 0 to 100.",
    "desc": "The Stochastic (14, 3, 3) in its own pane: near 100 the close is at the top of the last 14 bars' range, near 0 at the bottom, with a smoothed signal line. Above 80 is read as overbought, below 20 as oversold, and crosses of the two lines as turns. It is fast and noisy, and in trends it pins at one extreme.",
    "level": "Beginner", "goals": ["stretched"], "added": "2026-07-20", "concept": "concepts/Stochastic-Oscillator.md"
  },
  "mfi": {
    "short": "RSI that counts volume — stretched readings backed (or not) by money flow.",
    "desc": "The 14-bar Money Flow Index in its own pane, like RSI but weighted by volume and typical price. Above 80 is overbought, below 20 oversold, and a gap between MFI and price direction hints that volume is not confirming. A single heavy-volume day moves it a lot, and like RSI it can stay extreme in a trend.",
    "level": "Intermediate", "goals": ["stretched", "volume"], "added": "2026-09-11", "concept": null
  },
  "atr": {
    "short": "Average daily range (Wilder ATR 14) — use it to size stops and positions.",
    "desc": "Plots Wilder's 14-bar Average True Range in its own pane: how far the stock typically moves in a bar, gaps included. Use it to set a stop a sensible distance away and to size the position so a stop-out costs a fixed amount. It says nothing about direction, and it rises after big moves, so it describes the recent past rather than the next bar.",
    "level": "Beginner", "goals": ["stop"], "added": "2026-09-11", "concept": null
  },
  "hm": {
    "short": "Hilega-Milega: RSI 9 with its EMA and volume-weighted average, shading strength.",
    "desc": "Draws RSI (9) with a 3-bar EMA of it and a 21-bar volume-weighted average of it in a taller pane, shading above 50 warm and below 50 cool, with entry and exit markers. RSI above both averages is read as strength, below both as weakness. Three lines on a 0–100 scale cross often, and the markers fire in ranges as readily as in trends.",
    "level": "Advanced", "goals": ["stretched", "trend"], "added": "2026-08-21", "concept": null
  },
  "rsidiv": {
    "short": "Marks where price and RSI disagree — an early hint a move is tiring.",
    "desc": "Finds regular divergences (price makes a new high or low that RSI does not) and hidden divergences (the reverse, read as trend continuation), drawn on both the price chart and the RSI pane. Turning it on also turns RSI on. Divergence needs a confirmed swing, so it is marked a few bars late, and in strong trends divergences can stack up one after another before any turn.",
    "level": "Intermediate", "goals": ["stretched"], "added": "2026-08-07", "concept": "concepts/RSI.md"
  },
  "obvdiv": {
    "short": "Marks where price and On-Balance Volume disagree — is volume leaving the move?",
    "desc": "Finds regular and hidden divergences between price swings and OBV swings and marks them on the chart. A new price high with a lower OBV high says volume is not following the move. Like all divergence tools it confirms only after a swing completes, and OBV can be distorted by one unusual volume day.",
    "level": "Intermediate", "goals": ["volume", "stretched"], "added": "2026-09-07", "concept": "concepts/On-Balance-Volume.md"
  },
  "volume": {
    "short": "Volume bars under the candles — how much traded each bar.",
    "desc": "Draws each bar's volume as a histogram along the bottom of the price chart, coloured by up or down bar. A breakout on volume well above normal is more convincing than one on thin volume. Volume is relative: compare with the stock's own recent bars, not with other stocks, and index spot feeds carry no volume at all.",
    "level": "Beginner", "goals": ["volume"], "added": "2026-07-20", "concept": "concepts/Volume-Analysis.md"
  },
  "simplevol": {
    "short": "Volume bars highlighted: pocket pivots, dry-ups and above-average days.",
    "desc": "Colours volume bars by meaning: pocket-pivot days (an up day whose volume beats any down day of the last ten), dry-up days (unusually low volume) and above-average days. Pocket pivots inside a base are read as quiet accumulation; dry-ups near a pivot as sellers stepping back. These are labels, not signals: a pocket pivot in a downtrend means much less.",
    "level": "Intermediate", "goals": ["volume"], "added": "2026-09-22", "concept": "concepts/Pocket-Pivot.md"
  },
  "volprofile": {
    "short": "How much volume traded at each price — shows the levels the market cares about.",
    "desc": "Draws a sideways histogram of volume by price over the loaded bars, marking the point of control (most-traded price), the value area, and high- and low-volume nodes. High-volume nodes tend to act as support or resistance; low-volume nodes are prices the market moved through quickly. It depends on the window loaded, so zooming or changing the timeframe changes the levels.",
    "level": "Intermediate", "goals": ["levels", "volume"], "added": "2026-07-20", "concept": "concepts/Volume-Profile.md"
  },
  "svp": {
    "short": "A volume profile per session, with its shape (D/P/B/I) and accumulation read.",
    "desc": "Builds a separate volume profile for each session and labels its shape: D (balanced), P (buying high in the range), B (selling low in the range) and I (one-way trend), plus an accumulation or distribution read. It shows how each session's auction went, not just the overall levels. Shapes need enough intraday data to mean anything, and the reads have not been measured as signals.",
    "level": "Advanced", "goals": ["levels", "volume"], "added": "2026-08-20", "concept": "concepts/Volume-Profile.md"
  },
  "tpo": {
    "short": "Market Profile: how much TIME price spent at each level, letter by letter.",
    "desc": "Builds a Time-Price-Opportunity profile: each period that trades at a price adds a letter there, with the initial balance (opening range) marked. Wide areas of letters are prices the market accepted; thin single prints are prices it rejected. It needs intraday bars, and the profile shape depends on the period length chosen.",
    "level": "Advanced", "goals": ["levels"], "added": "2026-09-25", "concept": "concepts/Initial-Balance.md"
  },
  "deltaprofile": {
    "short": "Real buyer-versus-seller volume at each price — Hyperliquid crypto only.",
    "desc": "Draws volume by price split into aggressive buying and aggressive selling, taken from the exchange's own taker-side trade data rather than estimated from candles. Prices where sellers dominated on a rising market can show absorption. It only works for Hyperliquid symbols; NSE daily data has no taker side, so there is nothing to draw for Indian stocks.",
    "level": "Advanced", "goals": ["volume", "levels"], "added": "2026-09-05", "concept": "concepts/Order-Flow.md"
  },
  "elliott": {
    "short": "Automatic Elliott Wave count: impulse 1–5 and corrections A-B-C or W-X-Y.",
    "desc": "Finds swing points and labels them as an Elliott Wave count — a five-wave move with the trend and three-wave corrections against it, including complex W-X-Y corrections. It gives a map of where in a larger move price might be. Wave counts are subjective, the count can change as new swings form, and two analysts (or two settings) often disagree.",
    "level": "Advanced", "goals": ["trend", "target"], "added": "2026-07-20", "concept": "concepts/Elliott-Wave.md"
  },
  "ew2deg": {
    "short": "The same wave count at a larger scale, drawn over the normal one.",
    "desc": "Runs the Elliott Wave engine with a larger swing size and draws that count over the normal one, so you can see small waves nested inside bigger ones. It helps tell a correction inside an uptrend from the start of a downtrend. Everything that makes wave counts uncertain applies twice here, and the larger count changes less often but by more when it does.",
    "level": "Advanced", "goals": ["trend", "target"], "added": "2026-10-12", "concept": "concepts/Elliott-Wave.md"
  },
  "fvg": {
    "short": "Price gaps left by fast moves (fair value gaps), with buy/sell marks when they hold.",
    "desc": "Shades three-bar gaps where price moved so fast that a range was left untraded, and marks a buy or sell when price returns to a gap and respects it. Traders watch these gaps as places price may come back to fill. Many gaps are simply filled and run through, and small gaps on a busy chart are mostly noise.",
    "level": "Intermediate", "goals": ["levels"], "added": "2026-07-20", "concept": "concepts/Fair-Value-Gap.md"
  },
  "roundbottom": {
    "short": "Finds saucer-shaped bottoms — a slow, rounded turn from down to up.",
    "desc": "Detects rounding-bottom (saucer) bases and shades the base zone on the chart. A slow, rounded base followed by a push through its rim is a classic accumulation picture. The shape is judged after the fact, a saucer can keep extending sideways, and many never break out.",
    "level": "Beginner", "goals": ["target"], "added": "2026-07-20", "concept": "concepts/Rounding-Bottom.md"
  },
  "doublebottom": {
    "short": "W-shaped double bottoms with the neckline drawn and a quality grade.",
    "desc": "Finds two lows at a similar level with a peak between them, draws the neckline (the peak's level) and grades the pattern's quality, including the retest and follow-through. A close above the neckline is the usual confirmation. Before that close it is only a possible pattern, and in a strong downtrend second lows often break.",
    "level": "Beginner", "goals": ["target", "levels"], "added": "2026-09-19", "concept": "concepts/Reversal-Chart-Patterns.md"
  },
  "vcp": {
    "short": "Volatility contraction: a base whose pullbacks get smaller and quieter.",
    "desc": "Detects Minervini-style volatility contraction patterns — successive pullbacks each shallower than the last, usually with volume drying up — and shades the coiling zone. Tight action near the highs is read as supply being absorbed before a breakout. Many coils break down instead of up, and the pattern is defined loosely enough that it is easy to see one that is not there.",
    "level": "Intermediate", "goals": ["target"], "added": "2026-07-20", "concept": "concepts/VCP.md"
  },
  "trendlines": {
    "short": "Automatic trendlines along swing highs (supply) and swing lows (demand).",
    "desc": "Connects recent swing highs into a falling supply line and swing lows into a rising demand line. A close through a supply line suggests sellers have weakened; a break of a demand line, buyers. Lines depend on which swings the algorithm picks, they are redrawn as new swings form, and price often pierces a line before deciding.",
    "level": "Beginner", "goals": ["levels", "trend"], "added": "2026-07-20", "concept": "concepts/Trend-Lines.md"
  },
  "falling_wedge": {
    "short": "Falling wedge: price squeezing down between two converging lines, then breaking out.",
    "desc": "Detects a falling wedge — lower highs and lower lows drawing two lines that converge — and marks a breakout above the upper line. It is usually read as selling pressure fading. Wedges can break down as well as up, and lines fitted to a handful of swings are fragile.",
    "level": "Intermediate", "goals": ["target"], "added": "2026-07-27", "concept": "concepts/Falling-Wedge.md"
  },
  "flag_pole": {
    "short": "Flag and pole: a sharp move, a tight pause, and a measured-move target.",
    "desc": "Finds a sharp move (the pole) followed by a tight, slightly counter-trend pause (the flag), in either direction, and draws a plan with entry, stop and a measured-move target equal to the pole's length. Flags are continuation patterns: the trend is expected to resume. The measured move is a rule of thumb, not a forecast, and flags that drift too long or too deep often fail.",
    "level": "Intermediate", "goals": ["target", "stop"], "added": "2026-09-17", "concept": "concepts/Chart-Patterns.md"
  },
  "structure_chain": {
    "short": "Breaks of market structure: BOS continues the trend, CHoCH flags a possible turn.",
    "desc": "Tracks swing highs and lows and marks each Break of Structure (price breaks a swing in the trend's direction) and Change of Character (it breaks one against the trend), with a quality rating for each break. A chain of BOS shows a healthy trend; a CHoCH is the first sign it may be turning. Breaks are confirmed only after a swing completes, and in ranges BOS and CHoCH alternate with little meaning.",
    "level": "Intermediate", "goals": ["trend", "levels"], "added": "2026-07-30", "concept": "concepts/Market-Structure-CHOCH-BOS.md"
  },
  "orderblock": {
    "short": "Smart-money zones: the last opposite candle before a strong move.",
    "desc": "Shades order blocks — the last down candle before a strong rally (demand) or the last up candle before a sharp drop (supply) — and tracks when price returns to them. Traders watch these zones as places a big participant may defend. The idea of institutional footprints is a story, not something the data shows directly, and many zones are run through on the first touch.",
    "level": "Advanced", "goals": ["levels"], "added": "2026-08-21", "concept": "concepts/Order-Blocks.md"
  },
  "liquidity": {
    "short": "Clusters of equal highs/lows where stops sit, and BUY when a sweep below reclaims.",
    "desc": "Marks liquidity pools — equal highs or lows where stop orders tend to cluster — and flags a sweep when price pokes through one and closes back. A sweep below a pool that reclaims the level gets a BUY mark; a sweep above is shown as risk only, with no SELL. These are the same detector functions the desk's Liquidity Sweep scanner uses. A sweep can also be the start of a real breakdown, so the reclaim matters more than the poke.",
    "level": "Advanced", "goals": ["levels"], "added": "2026-09-11", "concept": "concepts/Equal-Highs-Lows.md"
  },
  "harmonic": {
    "short": "Harmonic patterns (Gartley, Bat, Butterfly, Crab, AB=CD) from Fibonacci ratios.",
    "desc": "Finds five-point XABCD swings whose leg ratios match the named harmonic patterns, or the simpler AB=CD, and marks the completion zone where the pattern expects a reversal. It gives a precise price zone to watch. The ratios have tolerances, so patterns are easy to find in any noisy chart, and a completion zone is a place to look, not a turn.",
    "level": "Advanced", "goals": ["target", "levels"], "added": "2026-07-20", "concept": null
  },
  "projection": {
    "short": "Where price could go next: targets from the wave count and detected patterns.",
    "desc": "Combines targets from the Elliott Wave count and from detected chart patterns into projected price levels and paths drawn ahead of the last bar. It answers 'if this pattern plays out, where does it point?'. Projections inherit every uncertainty of the patterns behind them and are scenarios, not forecasts.",
    "level": "Intermediate", "goals": ["target"], "added": "2026-07-20", "concept": null
  },
  "cpr": {
    "short": "Central Pivot Range from the prior bar: today's pivot, its band, and R1/S1.",
    "desc": "Computes the pivot, top central (TC) and bottom central (BC) levels from the previous bar's high, low and close, plus the first resistance (R1) and support (S1), and draws them for the current bar. A narrow CPR often comes before a trending day, a wide one before a range; opening above the band is read as bullish. The levels are arithmetic, not traded prices, so they matter only as much as other traders watch them.",
    "level": "Beginner", "goals": ["levels"], "added": "2026-09-28", "concept": "concepts/CPR-Central-Pivot-Range.md"
  },
  "fib": {
    "short": "Fibonacci retracement levels on the last swing, plus a trade plan where levels agree.",
    "desc": "Draws Fibonacci retracement levels (38.2%, 50%, 61.8% and others) across the most recent major swing, and builds a trade plan where those levels line up with volume-profile levels and the price projection. Pullbacks often pause near the 38–62% zone. The swing is picked automatically, there are many levels so one is always near price, and agreement between levels is a reason to watch, not a measured edge.",
    "level": "Intermediate", "goals": ["levels", "target", "stop"], "added": "2026-07-21", "concept": "concepts/Fibonacci-Retracement.md"
  },
  "gann": {
    "short": "Gann Square-of-9 support/resistance, with how often past breaks followed through.",
    "desc": "Draws support and resistance levels from Gann's Square of Nine around the current price and shows a card with how often, on this symbol's own history, a break of such a level carried on. The levels come from a geometric rule, not from where trading happened. The follow-through numbers describe this symbol's past only and are not a promise about the next break.",
    "level": "Advanced", "goals": ["levels"], "added": "2026-08-18", "concept": "concepts/Gann-Angles-And-Trend-Change-Levels.md"
  },
  "oiwalls": {
    "short": "Option strikes with the most open interest (walls) and max pain — F&O names only.",
    "desc": "For stocks with listed options, draws the call strike with the largest open interest (a ceiling traders watch), the put strike with the largest (a floor), and the max-pain strike for the chosen expiry. These show where option sellers have the most at stake. The ideas that price gravitates to max pain or bounces off a wall are untested folk claims, and the walls move as positions change during the day.",
    "level": "Advanced", "goals": ["levels"], "added": "2026-09-02", "concept": null
  },
  "reversal_calendar": {
    "short": "Marks dates of Vedic yogas and lunar phases that some traders watch for turns.",
    "desc": "Marks calendar dates of selected Vedic yogas and lunar phases on the time axis. Some traders use these dates as moments to watch for a change in direction. The dates come from astrological rules, not from price or volume, so treat them as a calendar to keep an eye on, not as a forecast.",
    "level": "Intermediate", "goals": [], "added": "2026-07-20", "concept": "concepts/Vedic-Calendar-Volatility-Triggers.md"
  }
}/*JSON-END*/;
