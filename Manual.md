PS C:\WINDOWS\system32> py -3 "C:\Users\dhara\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\screener_pipeline.py"

scraping financial data like share swap, divident bonus record date,demerger right issue from nseinda bse india portal for 1 week lookback date

Thought for 17s

Key sources for this data are the official NSE and BSE corporate actions pages.

nseindia.com

- NSE: [Corporate Filings - Corporate Actions](https://www.nseindia.com/companies-listing/corporate-filings-actions) (filter by "Last 1 Week").
- BSE: [Corporate Actions](https://www.bseindia.com/corporates/corporates_act.html) (filter by dates/Ex-Date/Record Date).
    
    bseindia.com
    

These pages list dividends, bonuses, rights issues, splits, etc., with Ex-Date, Record Date, and other details. Data is dynamic and best viewed directly on the sites (or downloaded as CSV). Below is a summary of notable items around mid-June 2026 (focusing on ~1-week lookback from ~June 18, 2026).

nseindia.com

Recent/Upcoming Dividends (Ex-Date/Record Date in mid-June 2026)Many companies have Ex-Dates and Record Dates clustered around June 18–19, 2026 (and extending further):June 18, 2026:

- Vimta Labs (VIMTALABS): Dividend ₹2/share.
- HDB Financial Services (HDBFS): Dividend ₹2/share.
- Tata Technologies (TATATECH): Dividend ₹8.35 + Special ₹3.35/share.
- Capital Small Finance Bank (CAPITALSFB): Dividend ₹5/share.
- JSW Infrastructure (JSWINFRA): Dividend ₹0.90/share.
- eMudhra (EMUDHRA): Dividend ₹1.25/share.
- GHCL: Dividend ₹12/share.
    
    nseindia.com
    

June 19, 2026 (and nearby):

- HDFC Bank (HDFCBANK): Dividend ₹13/share.
- Polycab India (POLYCAB): Dividend ₹47/share.
- Indiamart Intermesh (INDIAMART): Dividend ₹30 + Special ₹30/share.
- Torrent Power (TORNTPOWER), HDFC Life, Sanofi Consumer Healthcare, and others.
    
    bseindia.com
    

Later in June: Asian Paints, Hindustan Unilever, Tata Power, etc. (check exact Ex/Record dates on the portals).Bonus Issues

- String Metaverse Ltd: Bonus 2:9, Ex/Record ~June 19, 2026.
    
    bseindia.com
    
- ZF Commercial Vehicle Control Systems India Ltd: Bonus 5:1, Ex/Record ~June 24, 2026.
    
    bseindia.com
    
- Recent/prior: Brigade Enterprises (1:3), others in early-mid June.
    
    anandrathi.com
    

Rights Issues

- Oasis Securities Ltd: Rights Issue, Ex/Record ~June 18, 2026.
    
    bseindia.com
    
- Marg Techno Projects Ltd: Rights Issue, around June 19–20, 2026.
    
    bseindia.com
    
- Others appear sporadically (check portals for new filings).

Demerger / Share Swap / Other

- These are less frequent and often announced earlier with longer timelines. Recent examples (e.g., Vedanta-related demergers) had record dates in May 2026.
    
    bseindia.com
    
- No major new demergers/share swaps prominently listed for the exact past week in the summaries, but check the full corporate announcements/filings sections on NSE/BSE for schemes of arrangement.

Tips for Scraping / Automation (1-Week Lookback)

1. Direct scraping (ethically/respectfully, with delays and user-agent):
    - Use Python + requests/BeautifulSoup or selenium for the dynamic tables.
    - NSE/BSE often require POST requests or filters for "Last 1 Week".
    - APIs are limited; most reliable is parsing the HTML tables or CSV downloads.
2. Third-party aggregators (easier but not official):
    - Moneycontrol, Trendlyne, or GoIndiaStocks corporate action calendars.
        
        goindiastocks.com
        
3. Code example skeleton (use responsibly):
    
    python
    
    ```python
    import requests
    from bs4 import BeautifulSoup
    # Or use Selenium for JS-heavy pages
    # Filter NSE by date range or "Last 1 Week"
    ```
    

Always verify on official NSE/BSE sites as data changes daily. For production use, consider paid data providers or official exchange APIs/feeds if available. Let me know if you need help with specific companies or a particular date range!

![](https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https%3A%2F%2Fwww.nseindia.com%2Fcompanies-listing%2Fcorporate-filings-actions&size=256)

![](https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https%3A%2F%2Fwww.bseindia.com%2Fcorporates%2Fcorporates_act.html&size=256)

![](https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https%3A%2F%2Fanandrathi.com%2Fshare-market-today%2Fupcoming-bonus-share&size=256)

5 web pages

Python scraping NSE BSE corporate actions

NSE BSE corporate action APIs

provide me some github agent bot project of similar kind

Thought for 12s

Here are some relevant GitHub projects for scraping or fetching corporate actions (dividends, bonuses, rights issues, demergers, share swaps, etc.) from NSE India and BSE India:Top Recommendations for Corporate Actions

|Repo|Focus|Key Features|Link|
|---|---|---|---|
|BennyThadikaran/BseIndiaApi|BSE Corporate Actions & Announcements|Unofficial Python API. Fetches dividends, bonuses/splits, announcements, results. Includes example scripts for portfolio tracking.|[github.com/BennyThadikaran/BseIndiaApi](https://github.com/BennyThadikaran/BseIndiaApi)|
|bshada/nse-bse-api|NSE + BSE Unified API (TypeScript)|Corporate actions (dividends, bonuses, rights), announcements, quotes, option chains. Good for unified access.|[github.com/bshada/nse-bse-api](https://github.com/bshada/nse-bse-api)|
|BuildAlgos/screener-scraper|BSE + Screener.in Scraper|Scrapes announcements, upcoming events, corporate actions, fundamentals from BSE. Outputs structured JSON.|[github.com/BuildAlgos/screener-scraper](https://github.com/BuildAlgos/screener-scraper)|

Other Useful Scrapers & Libraries

- sdabhi23/bsedata — Python library for real-time BSE data.
    
    github.com
    
- Sampad-Hegde/NSE-India-Web-Scraping — General NSE scraper (can be extended for corporate filings).
    
    github.com
    
- nsepython (aeron7/nsepython) — Popular unofficial NSE API wrapper. Often used alongside BSE libraries for corporate data.
    
    pypi.org
    

Agentic / Bot-style Projects (Closer to "Agent Bot")

- vishwaskv362/StockResearchAgenticAI — Multi-agent AI system (CrewAI) for Indian stock research (NSE/BSE). Includes Telegram bot + Web UI. Good base for building a corporate action monitoring agent.
    
    github.com
    
- hopit-ai/india-trade-cli — Agentic AI trading platform with multiple LLM agents for NSE/BSE analysis.
    
    github.com
    
- SankarGaneshb/Market-Rover — AI stock intelligence tool that handles corporate actions (auto-fix for demergers/splits).
    
    github.com
    

General Tips for Your Use Case

- Most projects rely on web scraping or unofficial APIs → they may break when NSE/BSE changes their site. Add retries, headers, and rate limiting.
- For 1-week lookback, filter by date range on corporate actions pages or announcements.
- Combine a BSE scraper with nsepython for full coverage.
- Many projects support GitHub Actions for scheduled daily/weekly runs.

Would you like me to:

- Help you pick one and show how to set it up?
- Provide a sample Python script combining a few of these?
- Search for more agentic (LangChain/CrewAI/AutoGen) specific bots?

Let me know your preferred language (Python recommended) or specific features!

![](https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https%3A%2F%2Fgithub.com%2Fsdabhi23%2Fbsedata&size=256)

![](https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https%3A%2F%2Fgithub.com%2FSampad-Hegde%2FNSE-India-Web-Scraping&size=256)

![](https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https%3A%2F%2Fpypi.org%2Fproject%2Fnsepython%2F&size=256)

6 web pages

Explore CrewAI for multi-agent stock research

Check Trendlyne for corporate action ale![[Pasted image 20260618130213.png]]rts