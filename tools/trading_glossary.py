#!/usr/bin/env python3
"""
trading_glossary.py - Beginner-friendly explanations for trading terms.

Provides a centralized glossary of all technical terms used throughout
Trading Bramha, with beginner-friendly explanations and examples.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TermDefinition:
    """A single term definition with beginner-friendly explanation."""
    term: str
    category: str  # e.g., "Scanner", "Indicator", "Pattern", "Risk"
    definition: str  # Simple explanation for beginners
    technical_detail: str  # More technical explanation
    example: str  # Practical example
    related_terms: List[str]  # Related terms for cross-referencing


# ── Complete Glossary ───────────────────────────────────────────────────────────

GLOSSARY: Dict[str, TermDefinition] = {
    # ── Scanner Terms ───────────────────────────────────────────────────────────
    "VCP": TermDefinition(
        term="VCP (Volatility Contraction Pattern)",
        category="Scanner",
        definition="A price pattern where the stock's price range gets tighter and tighter, like a coiled spring. When it breaks out, it often moves strongly in one direction.",
        technical_detail="Characterized by progressively smaller price swings (lower volatility) followed by a decisive breakout above resistance. Named by Mark Minervini as a key setup for explosive moves.",
        example="RELIANCE traded between 2400-2500 for 3 months with smaller swings each week, then broke above 2500 and surged to 2800 in 2 weeks.",
        related_terms=["Breakout", "Resistance", "Volatility"],
    ),
    
    "Darvas Box": TermDefinition(
        term="Darvas Box",
        category="Scanner",
        definition="A rectangular price pattern where a stock trades in a tight range (the 'box') and then breaks above it with strong volume.",
        technical_detail="Named after Nicolas Darvas. Defined by a series of higher highs and higher lows forming a horizontal resistance level. The 'box' is the price range between the highest high and the lowest low before breakout.",
        example="TCS moved between 3400-3500 for 2 months, then broke above 3500 on 2x normal volume - that's a Darvas Box breakout.",
        related_terms=["Breakout", "Volume", "Resistance"],
    ),
    
    "Pullback Entry": TermDefinition(
        term="Pullback Entry",
        category="Scanner",
        definition="Buying a stock after it dips temporarily during an uptrend, betting it will resume going up.",
        technical_detail="An entry strategy where you buy when price pulls back to a support level (like the 21-day EMA) during an established uptrend. Lower risk than buying at the top because you're closer to a logical stop-loss.",
        example="INFY is in an uptrend, dips from 1500 to 1450 (touching its 21-day EMA), then bounces back up. Buying at 1450 is a pullback entry.",
        related_terms=["EMA", "Support", "Uptrend", "Stop-loss"],
    ),
    
    "Order Block": TermDefinition(
        term="Order Block",
        category="Scanner",
        definition="A price zone where institutional traders (big players) placed large buy orders in the past. When price returns to this zone, it often bounces up.",
        technical_detail="In Smart Money Concepts (SMC), an order block is the last down-candle before a strong bullish move. It represents where institutional demand absorbed selling pressure.",
        example="HDFC BANK had a big down-day at 1450, then rallied 10% over the next week. When it returned to 1450 later, buyers stepped in again - that's an order block.",
        related_terms=["Support", "Institutional", "Demand Zone"],
    ),
    
    "Breakout Retest": TermDefinition(
        term="Breakout Retest",
        category="Scanner",
        definition="After a stock breaks above a resistance level, it often comes back to test that level. If it holds above it, that's a good entry point.",
        technical_detail="The old resistance becomes new support. A retest confirms the breakout is valid. Buying on the retest offers better risk-reward than buying at the breakout.",
        example="TATAMOTORS broke above 600, dipped back to 598 (the old resistance), then bounced. Buying at 598 is a breakout retest entry.",
        related_terms=["Breakout", "Resistance", "Support", "Risk-Reward"],
    ),
    
    "HM Buy": TermDefinition(
        term="HM Buy (Hilega Milega)",
        category="Scanner",
        definition="A momentum-based buy signal from the Hilega Milega indicator. It identifies when a stock's momentum is turning bullish.",
        technical_detail="Based on RSI crossing above 50 with specific EMA confirmations. 'Hilega Milega' is Hindi for 'will go up'. The system looks for RSI momentum shifts with volume confirmation.",
        example="WIPRO's RSI was below 50, then crossed above with EMA confirmation and high volume - that's an HM Buy signal.",
        related_terms=["RSI", "EMA", "Momentum", "Volume"],
    ),
    
    "RSI Divergence": TermDefinition(
        term="RSI Divergence",
        category="Scanner",
        definition="When price makes a new low but the RSI indicator makes a higher low - a sign the downward momentum is weakening.",
        technical_detail="Bullish divergence: Price lower low, RSI higher low = potential reversal up. Bearish divergence: Price higher high, RSI lower high = potential reversal down. Divergence warns that the current trend may be losing strength.",
        example="MARUTI fell to 9000 (lower than previous low of 9200), but RSI only dropped to 35 (higher than previous 30). This bullish divergence preceded a rally to 9500.",
        related_terms=["RSI", "Reversal", "Momentum"],
    ),
    
    "52-Week High Leaders": TermDefinition(
        term="52-Week High Leaders",
        category="Scanner",
        definition="Stocks trading within 5% of their highest price in the last year. These are often the strongest momentum leaders.",
        technical_detail="Near 52-week highs indicate strong demand and institutional interest. These stocks have already proven they can go higher - the trend is your friend.",
        example="BAJFINANCE is at 7500, its 52-week high is 7800 (only 4% away). It's a 52-week high leader with strong momentum.",
        related_terms=["Momentum", "Leaders", "Trend"],
    ),
    
    "Stage 2 Uptrend": TermDefinition(
        term="Stage 2 Uptrend",
        category="Scanner",
        definition="A textbook uptrend defined by Mark Minervini: price is above its 50-day, 150-day, and 200-day moving averages, and all three averages are rising.",
        technical_detail="Stage 1 = Accumulation (bottoming), Stage 2 = Uptrend (the money-making phase), Stage 3 = Distribution (topping), Stage 4 = Downtrend. Stage 2 is where you want to be long.",
        example="SBIN is trading above its SMA50, SMA150, and SMA200, and all three are sloping upward - that's a classic Stage 2 uptrend.",
        related_terms=["SMA", "Uptrend", "Minervini", "Moving Average"],
    ),
    
    "CHoCH": TermDefinition(
        term="CHoCH (Change of Character)",
        category="Scanner",
        definition="A market structure shift where price breaks a key swing high in a downtrend, signaling the trend might be reversing to up.",
        technical_detail="In Smart Money Concepts, CHoCH is the first sign of trend reversal. A bullish CHoCH occurs when price breaks above the most recent confirmed swing high while in a downtrend.",
        example="LT was in a downtrend making lower highs, then broke above its most recent swing high at 2200 - that's a bullish CHoCH signaling potential trend reversal.",
        related_terms=["Market Structure", "Reversal", "Swing High", "Trend"],
    ),
    
    # ── Indicator Terms ─────────────────────────────────────────────────────────
    "RSI": TermDefinition(
        term="RSI (Relative Strength Index)",
        category="Indicator",
        definition="A momentum indicator that measures how fast price is changing. It ranges from 0-100. Above 70 = overbought (price may fall), below 30 = oversold (price may rise).",
        technical_detail="Developed by J. Welles Wilder. RSI compares the magnitude of recent gains to recent losses. Default period is 14 days. Overbought/oversold conditions can persist in strong trends, so use with other indicators.",
        example="TCS RSI is at 75 (overbought) - it might pull back soon. INFY RSI is at 25 (oversold) - it might bounce.",
        related_terms=["Momentum", "Overbought", "Oversold"],
    ),
    
    "EMA": TermDefinition(
        term="EMA (Exponential Moving Average)",
        category="Indicator",
        definition="A type of moving average that gives more weight to recent prices, making it faster to react to price changes than a simple moving average.",
        technical_detail="EMA calculation applies a weighting multiplier to each data point, with more recent prices getting higher weight. Common periods: EMA21 (short-term), EMA50 (medium-term), EMA200 (long-term). EMAs are used for trend identification and support/resistance.",
        example="Price is above EMA21 = short-term uptrend. Price crosses above EMA50 = medium-term trend reversal signal.",
        related_terms=["SMA", "Moving Average", "Trend", "Support"],
    ),
    
    "SMA": TermDefinition(
        term="SMA (Simple Moving Average)",
        category="Indicator",
        definition="The average price over a specific period. It smooths out price data to show the trend direction more clearly.",
        technical_detail="Calculated by summing prices over N periods and dividing by N. Unlike EMA, it gives equal weight to all periods. Common periods: SMA50, SMA150, SMA200. Used in Stage analysis and trend confirmation.",
        example="The 50-day SMA of RELIANCE is 2400 - this is the average price over the last 50 trading days.",
        related_terms=["EMA", "Moving Average", "Trend"],
    ),
    
    "ADX": TermDefinition(
        term="ADX (Average Directional Index)",
        category="Indicator",
        definition="Measures the strength of a trend (not direction). ADX above 25 = strong trend, below 20 = weak trend or ranging market.",
        technical_detail="Developed by J. Welles Wilder. ADX is derived from the +DI and -DI indicators. High ADX means the trend is strong (whether up or down). Low ADX means the market is ranging or trendless.",
        example="HDFC BANK has ADX of 30 = strong trend. Whether it's up or down depends on +DI vs -DI.",
        related_terms=["Trend Strength", "+DI", "-DI", "Ranging"],
    ),
    
    "VWMA": TermDefinition(
        term="VWMA (Volume Weighted Moving Average)",
        category="Indicator",
        definition="A moving average that gives more weight to days with higher volume. It shows where the 'real' average price is, considering trading activity.",
        technical_detail="Unlike SMA which treats all days equally, VWMA multiplies each day's price by its volume. High-volume days have more influence. Useful for identifying where institutional activity occurred.",
        example="Price is above VWMA21 = buyers in control on average volume. Price below VWMA = sellers in control.",
        related_terms=["Volume", "Moving Average", "Institutional"],
    ),
    
    "ATR": TermDefinition(
        term="ATR (Average True Range)",
        category="Indicator",
        definition="Measures how much a stock typically moves in a day (volatility). Higher ATR = more volatile, larger price swings.",
        technical_detail="Developed by J. Welles Wilder. ATR considers the true range (high-low, high-previous close, low-previous close). Used for setting stop-loss distances (e.g., 2x ATR below entry).",
        example="TCS has ATR of 50 = it typically moves ₹50 per day. Use this to set a stop-loss 2x ATR (₹100) below your entry.",
        related_terms=["Volatility", "Stop-loss", "Risk Management"],
    ),
    
    "%R": TermDefinition(
        term="Williams %R",
        category="Indicator",
        definition="A momentum indicator similar to RSI but scaled from -100 to 0. Above -20 = overbought, below -80 = oversold.",
        technical_detail="Developed by Larry Williams. Measures overbought/oversold conditions based on closing price relative to the high-low range over N periods. Useful for identifying potential reversals at extremes.",
        example="%R at -15 = overbought, watch for pullback. %R at -85 = oversold, watch for bounce.",
        related_terms=["RSI", "Momentum", "Overbought", "Oversold"],
    ),
    
    # ── Pattern Terms ───────────────────────────────────────────────────────────
    "Symmetrical Triangle": TermDefinition(
        term="Symmetrical Triangle",
        category="Pattern",
        definition="A pattern where the highs are getting lower and the lows are getting higher, forming a triangle shape. Price is squeezing between converging trendlines.",
        technical_detail="Indicates consolidation before a breakout. Can break either way (up or down). Volume typically decreases as the pattern forms, then increases on breakout. The direction is unpredictable until breakout.",
        example="MARUTI highs went from 9500→9300→9100 while lows went from 8800→8900→9000 - forming a symmetrical triangle.",
        related_terms=["Consolidation", "Breakout", "Trendline"],
    ),
    
    "Ascending Triangle": TermDefinition(
        term="Ascending Triangle",
        category="Pattern",
        definition="A bullish pattern with a flat top (resistance) and rising bottom (support). Buyers are getting more aggressive, pushing lows higher.",
        technical_detail="Resistance is horizontal (sellers at fixed price), support is rising (buyers willing to pay more). Typically breaks upward. Measured target = height of triangle added to breakout point.",
        example="HDFC BANK hit 1600 three times (flat resistance) but each dip was shallower (850→870→890). Eventually broke above 1600.",
        related_terms=["Resistance", "Support", "Bullish", "Breakout"],
    ),
    
    "Bull Flag": TermDefinition(
        term="Bull Flag",
        category="Pattern",
        definition="A continuation pattern after a strong up move. Price consolidates in a small range (the 'flag') before resuming the uptrend.",
        technical_detail="The 'pole' is the strong initial rally. The 'flag' is a small consolidation, often sloping slightly downward. Breakout above the flag typically continues the prior uptrend. Measured target = pole height added to breakout.",
        example="TATAMOTORS rallied from 500 to 600 (pole), then consolidated at 580-600 for 2 weeks (flag), then broke above 600 to 700.",
        related_terms=["Continuation", "Uptrend", "Breakout", "Consolidation"],
    ),
    
    "Cup and Handle": TermDefinition(
        term="Cup and Handle",
        category="Pattern",
        definition="A bullish pattern that looks like a teacup. A rounded bottom (cup) followed by a small dip (handle) before breaking out.",
        technical_detail="The cup is a U-shaped correction (typically 7-20 weeks). The handle is a shallow pullback (typically 1-4 weeks) on low volume. Breakout above handle resistance signals continuation. One of the most reliable patterns.",
        example="BAJFINANCE fell from 7500 to 6500 over 3 months forming a cup, then dipped to 7000 (handle), then broke above 7500.",
        related_terms=["Continuation", "Breakout", "Bullish", "Correction"],
    ),
    
    # ── Risk Management Terms ───────────────────────────────────────────────────
    "Stop-loss": TermDefinition(
        term="Stop-loss",
        category="Risk",
        definition="A predetermined price level where you'll exit a trade if it goes against you. It limits your loss on any single trade.",
        technical_detail="Essential risk management tool. Set based on technical levels (support, ATR multiples, etc.). Never move a stop-loss further away (locking in losses is okay, expanding risk is not). Typical: 1-2% of capital per trade.",
        example="You buy at 1000 with stop-loss at 950. If price drops to 950, you sell automatically, limiting loss to 5%.",
        related_terms=["Risk Management", "Capital", "Support", "ATR"],
    ),
    
    "Risk-Reward Ratio": TermDefinition(
        term="Risk-Reward Ratio (R:R)",
        category="Risk",
        definition="The ratio of potential profit to potential loss. A 2:1 ratio means you risk ₹1 to make ₹2. Higher ratios are better.",
        technical_detail="Calculated as (Target Price - Entry Price) / (Entry Price - Stop-loss). Minimum acceptable is typically 2:1. Never take a trade with poor R:R even if the setup looks good.",
        example="Entry 1000, Target 1100, Stop 950. Risk = 50, Reward = 100. R:R = 100/50 = 2:1.",
        related_terms=["Stop-loss", "Target", "Risk Management"],
    ),
    
    "Position Sizing": TermDefinition(
        term="Position Sizing",
        category="Risk",
        definition="Deciding how many shares to buy based on your risk tolerance. Ensures no single trade can blow up your account.",
        technical_detail="Formula: Position Size = (Capital × Risk %) / (Entry - Stop-loss). If you have ₹1,00,000 and risk 1% per trade, and stop-loss is ₹50 away, buy 20 shares (max loss ₹1,000).",
        example="With ₹1,00,000 capital, 1% risk per trade, and stop-loss ₹50 away, you should buy 20 shares (max loss ₹1,000 = 1% of capital).",
        related_terms=["Capital", "Stop-loss", "Risk Management"],
    ),
    
    "Drawdown": TermDefinition(
        term="Drawdown",
        category="Risk",
        definition="The peak-to-trough decline in your portfolio value. It measures how much your account has dropped from its highest point.",
        technical_detail="Calculated as (Peak Value - Current Value) / Peak Value. Monitoring drawdown prevents overtrading during losing streaks. Professional traders typically limit max drawdown to 10-20%.",
        example="Your portfolio peaked at ₹1,00,000, then dropped to ₹85,000. Drawdown = (1,00,000 - 85,000) / 1,00,000 = 15%.",
        related_terms=["Portfolio", "Risk Management", "Peak"],
    ),
    
    # ── Market Structure Terms ───────────────────────────────────────────────────
    "Support": TermDefinition(
        term="Support",
        category="Market Structure",
        definition="A price level where buying interest is strong enough to prevent further decline. Think of it as a 'floor' for the price.",
        technical_detail="Support forms where buyers have historically stepped in (previous lows, moving averages, psychological levels). More touches = stronger support. Broken support often becomes resistance.",
        example="RELIANCE has bounced off 2400 three times in the last 6 months - 2400 is strong support.",
        related_terms=["Resistance", "Floor", "Buying Interest"],
    ),
    
    "Resistance": TermDefinition(
        term="Resistance",
        category="Market Structure",
        definition="A price level where selling pressure is strong enough to prevent further advance. Think of it as a 'ceiling' for the price.",
        technical_detail="Resistance forms where sellers have historically stepped in (previous highs, moving averages, psychological levels). More touches = stronger resistance. Broken resistance often becomes support.",
        example="TCS has failed to break above 3800 four times - 3800 is strong resistance.",
        related_terms=["Support", "Ceiling", "Selling Pressure"],
    ),
    
    "Uptrend": TermDefinition(
        term="Uptrend",
        category="Market Structure",
        definition="A series of higher highs and higher lows. Price is generally moving upward over time.",
        technical_detail="Defined by price making successively higher peaks and higher troughs. In an uptrend, each rally exceeds the previous high, and each decline stays above the previous low. The trend is your friend - trade with it.",
        example="INFY went 1400→1500→1600 (higher highs) and dipped to 1450→1550 (higher lows) - clear uptrend.",
        related_terms=["Downtrend", "Higher Highs", "Higher Lows", "Trend"],
    ),
    
    "Downtrend": TermDefinition(
        term="Downtrend",
        category="Market Structure",
        definition="A series of lower highs and lower lows. Price is generally moving downward over time.",
        technical_detail="Defined by price making successively lower peaks and lower troughs. In a downtrend, each decline exceeds the previous low, and each rally stays below the previous high. Avoid going long in strong downtrends.",
        example="SBIN went 600→550→500 (lower highs) and bounced to 580→530 (lower lows) - clear downtrend.",
        related_terms=["Uptrend", "Lower Highs", "Lower Lows", "Trend"],
    ),
    
    "Swing High": TermDefinition(
        term="Swing High",
        category="Market Structure",
        definition="A peak in price that is higher than the prices immediately before and after it. Used to draw trendlines and identify market structure.",
        technical_detail="In technical analysis, a swing high is a local maximum. A series of lower swing highs confirms a downtrend. A break above a swing high can signal trend reversal (CHoCH).",
        example="Price went 100→120→110→115→100. 120 is a swing high (higher than neighbors 100 and 110).",
        related_terms=["Swing Low", "Trendline", "Market Structure", "CHoCH"],
    ),
    
    "Swing Low": TermDefinition(
        term="Swing Low",
        category="Market Structure",
        definition="A trough in price that is lower than the prices immediately before and after it. Used to draw trendlines and identify market structure.",
        technical_detail="In technical analysis, a swing low is a local minimum. A series of higher swing lows confirms an uptrend. A break below a swing low can signal trend reversal.",
        example="Price went 100→80→90→85→100. 80 is a swing low (lower than neighbors 100 and 90).",
        related_terms=["Swing High", "Trendline", "Market Structure"],
    ),
    
    # ── Volume Terms ────────────────────────────────────────────────────────────
    "Volume": TermDefinition(
        term="Volume",
        category="Volume",
        definition="The number of shares traded in a given time period. High volume means many shares are changing hands (high interest/activity).",
        technical_detail="Volume confirms price moves. Price up on high volume = strong buyer interest. Price up on low volume = weak move (may not sustain). Volume precedes price - watch for volume spikes.",
        example="TCS normally trades 5M shares/day. Today it traded 15M shares = 3x normal volume, high interest.",
        related_terms=["Volume Confirmation", "Liquidity", "Interest"],
    ),
    
    "Volume Confirmation": TermDefinition(
        term="Volume Confirmation",
        category="Volume",
        definition="When a price move is accompanied by high volume, it's more likely to be genuine and sustainable.",
        technical_detail="Breakouts on low volume often fail (fake-outs). Breakouts on high volume have institutional backing and are more reliable. Look for volume 1.5-2x above average when evaluating setups.",
        example="HDFC BANK broke above resistance at 3000 with 2x normal volume = volume-confirmed breakout, more reliable.",
        related_terms=["Volume", "Breakout", "Institutional"],
    ),
    
    "Liquidity": TermDefinition(
        term="Liquidity",
        category="Volume",
        definition="How easily you can buy or sell a stock without affecting its price. High liquidity = easy to trade, low liquidity = hard to trade.",
        technical_detail="Measured by average daily volume and bid-ask spread. High-volume stocks (Nifty 50) are liquid. Small-caps with low volume are illiquid (hard to enter/exit without slippage). Avoid illiquid stocks for large positions.",
        example="RELIANCE trades 20M shares/day = highly liquid. A smallcap trading 10K shares/day = illiquid.",
        related_terms=["Volume", "Slippage", "Market Impact"],
    ),
    
    # ── Fundamental Terms ─────────────────────────────────────────────────────
    "EPS": TermDefinition(
        term="EPS (Earnings Per Share)",
        category="Fundamental",
        definition="A company's profit divided by its number of shares. Higher EPS = more profitable per share owned.",
        technical_detail="EPS = Net Income / Outstanding Shares. Increasing EPS over time = growing profitability. Compare EPS growth across quarters/years. Used in P/E ratio calculation.",
        example="TCS earned ₹20,000 crore profit with 1 billion shares = EPS of ₹20.",
        related_terms=["P/E", "Profitability", "Earnings"],
    ),
    
    "P/E Ratio": TermDefinition(
        term="P/E Ratio (Price-to-Earnings)",
        category="Fundamental",
        definition="Stock price divided by EPS. Shows how much you're paying for each rupee of earnings. Lower P/E = cheaper relative to earnings.",
        technical_detail="P/E = Price / EPS. Compare P/E to sector average and historical range. High P/E = growth expectations or overvalued. Low P/E = value or troubled company.",
        example="TCS at ₹3000 with EPS ₹50 = P/E of 60. If sector average is 25, TCS may be expensive.",
        related_terms=["EPS", "Valuation", "Overvalued", "Undervalued"],
    ),
    
    "Market Cap": TermDefinition(
        term="Market Capitalization",
        category="Fundamental",
        definition="Total value of a company's shares. Large-cap = ₹1,00,000+ crore, Mid-cap = ₹10,000-1,00,000 crore, Small-cap = below ₹10,000 crore.",
        technical_detail="Market Cap = Share Price × Outstanding Shares. Large-caps are stable, small-caps are volatile. Diversify across market cap for risk management.",
        example="RELIANCE at ₹2500 with 4 billion shares = market cap of ₹10,00,000 crore (large-cap).",
        related_terms=["Large-cap", "Mid-cap", "Small-cap", "Valuation"],
    ),
    
    # ── Regime Terms ───────────────────────────────────────────────────────────
    "RISK-ON": TermDefinition(
        term="RISK-ON Regime",
        category="Regime",
        definition="Market conditions where investors are confident and willing to take risks. Bullish signals work better in this regime.",
        technical_detail="Characterized by rising indices (Nifty above 200 SMA), positive breadth, low VIX. In RISK-ON, growth stocks and small-caps outperform. Use aggressive trading strategies.",
        example="Nifty is above 200-day SMA, VIX below 15, more stocks advancing than declining = RISK-ON regime.",
        related_terms=["RISK-OFF", "Bullish", "Market Conditions"],
    ),
    
    "RISK-OFF": TermDefinition(
        term="RISK-OFF Regime",
        category="Regime",
        definition="Market conditions where investors are fearful and avoid risk. Defensive stocks work better in this regime.",
        technical_detail="Characterized by falling indices (Nifty below 200 SMA), negative breadth, high VIX. In RISK-OFF, quality large-caps and defensives outperform. Reduce position sizes, avoid speculative stocks.",
        example="Nifty is below 200-day SMA, VIX above 25, more stocks declining than advancing = RISK-OFF regime.",
        related_terms=["RISK-ON", "Bearish", "Market Conditions", "VIX"],
    ),
    
    "VIX": TermDefinition(
        term="VIX (Volatility Index)",
        category="Regime",
        definition="India's 'fear gauge' - measures expected market volatility over the next 30 days. Higher VIX = more fear/volatility.",
        technical_detail="India VIX is based on Nifty options. VIX below 15 = calm market, VIX above 25 = volatile/fearful market. High VIX = wider stop-losses needed, reduce position sizes.",
        example="India VIX at 12 = calm market, good for breakout trades. VIX at 30 = volatile, be cautious.",
        related_terms=["Volatility", "Fear Gauge", "Market Sentiment"],
    ),
    
    # ── Scanner Categories ─────────────────────────────────────────────────────
    "Entry Scanner": TermDefinition(
        term="Entry Scanner",
        category="Scanner Category",
        definition="Scanners that identify potential buy points with specific entry, stop-loss, and target levels. These are actionable trade setups.",
        technical_detail="Entry scanners provide complete trade plans: where to enter, where to place stop-loss, and where to take profit. Examples: Pullback Entry, Order Block Retest, HM Buy. Use these for taking new positions.",
        example="The Pullback Entry scanner says buy at 1450, stop at 1420, target 1510 - that's a complete entry plan.",
        related_terms=["Trade Setup", "Stop-loss", "Target", "Actionable"],
    ),
    
    "Trend Scanner": TermDefinition(
        term="Trend Scanner",
        category="Scanner Category",
        definition="Scanners that identify the overall trend direction or structure changes. These provide context, not entry signals.",
        technical_detail="Trend scanners tell you IF a stock is in an uptrend/downtrend or IF the trend is changing. Examples: Stage 2 Uptrend, CHoCH, Renko Flip. Use these to filter which stocks to consider for entries.",
        example="Stage 2 Uptrend scanner tells you TCS is in an uptrend - good context, but not a buy signal by itself.",
        related_terms=["Context", "Trend", "Market Structure", "Filter"],
    ),
    
    "Risk Scanner": TermDefinition(
        term="Risk Scanner",
        category="Scanner Category",
        definition="Scanners that identify potential risks or exit signals. These warn you to exit or avoid certain stocks.",
        technical_detail="Risk scanners flag stocks showing signs of topping, exhaustion, or reversal. Examples: RSI Divergence Bear, %R Exhaustion Sell, Bearish Reversal Candle. Use these to manage existing positions.",
        example="RSI Divergence Bear scanner flags your holding with a bearish divergence - consider taking profits or tightening stop-loss.",
        related_terms=["Exit Signal", "Risk Flag", "Reversal", "Warning"],
    ),
    
    "Pattern Scanner": TermDefinition(
        term="Pattern Scanner",
        category="Scanner Category",
        definition="Scanners that detect geometric price patterns. These identify setups that may lead to predictable price moves.",
        technical_detail="Pattern scanners recognize shapes like triangles, flags, wedges, and boxes. These patterns have measured targets. Examples: Darvas Box, Symmetrical Triangle, Bull Flag. Patterns are probability plays, not certainties.",
        example="Darvas Box scanner detects a box pattern with measured target 10% above breakout - probability of reaching target is historically 60-70%.",
        related_terms=["Geometric Pattern", "Setup", "Measured Target", "Probability"],
    ),
    
    # ── Confluence Terms ────────────────────────────────────────────────────────
    "Confluence": TermDefinition(
        term="Confluence",
        category="Analysis",
        definition="When multiple indicators/scanners agree on the same signal. Higher confluence = higher probability of success.",
        technical_detail="A stock hitting 3+ scanners has confluence. The more independent methods that agree, the stronger the signal. For example: Entry scanner + Trend scanner + Momentum scanner all firing = high confluence.",
        example="TCS hits Pullback Entry (Entry), Stage 2 Uptrend (Trend), and 52-Week High Leaders (Momentum) = 3-point confluence, strong signal.",
        related_terms=["Agreement", "Probability", "Multiple Signals", "Confirmation"],
    ),
    
    "Conviction": TermDefinition(
        term="Conviction",
        category="Analysis",
        definition="How confident you are in a trade based on the strength of the signal. High conviction = more confluence, better setup quality.",
        technical_detail="Conviction is subjective but should be based on objective factors: number of confluence points, quality of setup, regime alignment, risk-reward ratio. Scale conviction: Low, Medium, High. Only take large positions on High conviction.",
        example="A stock with 4-point confluence in RISK-ON regime with 3:1 R:R = High conviction. Take full position size.",
        related_terms=["Confluence", "Confidence", "Position Size", "Quality"],
    ),
}


# ── Category Lists ─────────────────────────────────────────────────────────────

CATEGORIES = {
    "Scanner": [t for t, d in GLOSSARY.items() if d.category == "Scanner"],
    "Indicator": [t for t, d in GLOSSARY.items() if d.category == "Indicator"],
    "Pattern": [t for t, d in GLOSSARY.items() if d.category == "Pattern"],
    "Risk": [t for t, d in GLOSSARY.items() if d.category == "Risk"],
    "Market Structure": [t for t, d in GLOSSARY.items() if d.category == "Market Structure"],
    "Volume": [t for t, d in GLOSSARY.items() if d.category == "Volume"],
    "Fundamental": [t for t, d in GLOSSARY.items() if d.category == "Fundamental"],
    "Regime": [t for t, d in GLOSSARY.items() if d.category == "Regime"],
    "Scanner Category": [t for t, d in GLOSSARY.items() if d.category == "Scanner Category"],
    "Analysis": [t for t, d in GLOSSARY.items() if d.category == "Analysis"],
}


# ── Helper Functions ───────────────────────────────────────────────────────────

def get_definition(term: str) -> TermDefinition | None:
    """Get the definition for a term (case-insensitive)."""
    return GLOSSARY.get(term)


def search_terms(query: str) -> list[str]:
    """Search for terms matching the query in term name or definition."""
    query = query.lower()
    matches = []
    for term, defn in GLOSSARY.items():
        if query in term.lower() or query in defn.definition.lower():
            matches.append(term)
    return sorted(matches)


def get_terms_by_category(category: str) -> list[str]:
    """Get all terms in a category."""
    return CATEGORIES.get(category, [])


def get_all_categories() -> list[str]:
    """Get all category names."""
    return sorted(CATEGORIES.keys())


def get_related_terms(term: str) -> list[str]:
    """Get related terms for a given term."""
    defn = get_definition(term)
    if defn:
        return defn.related_terms
    return []


# ── HTML Tooltip Generator ────────────────────────────────────────────────────

def generate_tooltip(term: str, icon: str = "ℹ️") -> str:
    """Generate an HTML tooltip for a term with info icon."""
    defn = get_definition(term)
    if not defn:
        return f"{icon} {term}"
    
    return f"""
    <span style="cursor:help; border-bottom: 1px dotted #666;" title="{defn.definition}">
        {icon} {term}
    </span>
    """


def generate_detailed_tooltip(term: str, icon: str = "ℹ️") -> str:
    """Generate a detailed HTML tooltip with all information."""
    defn = get_definition(term)
    if not defn:
        return f"{icon} {term}"
    
    return f"""
    <div style="display:inline-block; position:relative;">
        <span style="cursor:help; border-bottom: 1px dotted #666;">
            {icon} {term}
        </span>
        <div style="display:none; position:absolute; left:0; top:100%; z-index:1000;
                    background:#fff; border:1px solid #ccc; padding:10px; border-radius:5px;
                    box-shadow:0 2px 10px rgba(0,0,0,0.1); width:300px; font-size:12px;
                    color:#333;">
            <strong>{defn.term}</strong><br/>
            <em>{defn.category}</em><br/><br/>
            <b>Simple:</b> {defn.definition}<br/><br/>
            <b>Technical:</b> {defn.technical_detail}<br/><br/>
            <b>Example:</b> {defn.example}<br/><br/>
            <small>Related: {', '.join(defn.related_terms)}</small>
        </div>
    </div>
    """


if __name__ == "__main__":
    # Test the glossary
    print("Trading Glossary loaded successfully!")
    print(f"Total terms: {len(GLOSSARY)}")
    print(f"Categories: {get_all_categories()}")
    
    # Test search
    print("\nSearch 'RSI':", search_terms("RSI"))
    print("Search 'trend':", search_terms("trend"))
