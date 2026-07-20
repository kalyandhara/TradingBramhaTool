import express from 'express';
import cors from 'cors';

const app = express();
app.use(cors());
app.use(express.json());

// ── Universe (≈ 500 each) ─────────────────────────────────────────────────────

const USA_TICKERS = [
  // Technology
  'AAPL','MSFT','NVDA','GOOGL','GOOG','META','AVGO','ORCL','CSCO','ADBE',
  'CRM','AMD','TXN','QCOM','INTC','AMAT','MU','LRCX','KLAC','ADI',
  'MRVL','SNPS','CDNS','ANSS','PANW','CRWD','FTNT','ZS','DDOG','SNOW',
  'PLTR','DELL','HPQ','HPE','IBM','WDC','STX','NTAP','FFIV','JNPR',
  'KEYS','TER','MPWR','SWKS','QRVO','ANET','SMCI','VRT','VRSN','TRMB',
  'EPAM','CTSH','GDDY','CDAY','PAYC','PCTY','MANH','BRZE','ZI','AI',
  'PATH','ASAN','MNDY','BILL','FIVN','EGHT','JAMF','AKAM','CDW','TTEC',
  'AZPN','DOCN','BOX','DBX','MDB','ESTC','DSGX','FOUR','TASK','WK',
  'POWI','IDCC','MTSI','CRUS','SLAB','CALX','VIAV','IPGP','COHR','ONTO',
  // Financials
  'JPM','BAC','WFC','C','GS','MS','USB','PNC','TFC','COF',
  'DFS','SYF','ALLY','WAL','WTFC','ZION','RF','KEY','FITB','HBAN',
  'CFG','MTB','BHF','AXP','V','MA','PYPL','COIN','IBKR','HOOD',
  'SOFI','FIS','FISV','GPN','WEX','NDAQ','ICE','CME','CBOE','MSCI',
  'MCO','SPGI','BLK','SCHW','TROW','BEN','IVZ','AMP','PRU','MET',
  'AIG','AFL','ALL','CB','TRV','PGR','HIG','MMC','AON','WTW',
  'BRO','AJG','RE','RNR','ERIE','UNM','GL','STT','BK','NTRS',
  'BRK-B','LNC','VOYA','FHI','AMG','SEIC','VRTS','OMF','SLM','NAVI',
  // Healthcare
  'UNH','LLY','JNJ','ABBV','MRK','PFE','BMY','AMGN','GILD','BIIB',
  'REGN','VRTX','MRNA','ISRG','SYK','MDT','BSX','EW','BDX','TMO',
  'DHR','A','IDXX','DXCM','PODD','ALGN','ZBH','BAX','CAH','MCK',
  'ABC','CVS','WBA','MOH','ELV','CI','HCA','THC','UHS','CNC',
  'HUM','STE','HOLX','XRAY','TECH','GMED','IRTC','INSP','NVCR','HALO',
  'AMED','ENSG','TDOC','HIMS','RXRX','ACAD','ALNY','EXAS','NTRA','IONS',
  'NBIX','RARE','PTCT','AGEN','SAGE','NVAX','ILMN','BHVN','VKTX','PCVX',
  // Consumer Discretionary
  'AMZN','TSLA','HD','MCD','NKE','SBUX','LOW','TJX','ROST','CMG',
  'DPZ','YUM','YUMC','QSR','DRI','EAT','TXRH','CAKE','SHAK','WEN',
  'ETSY','W','CHWY','EBAY','RH','WSM','PTON','DKNG','DHI','LEN',
  'NVR','PHM','TOL','MDC','MTH','LGIH','SKY','BZH','LAD','ABG',
  'AN','SAH','GPI','PAG','KMX','CVNA','ANF','AEO','RL','PVH',
  'CPRI','TPR','LULU','ULTA','DKS','BBY','GPS','ONON','SKX','DECK',
  'BOOT','CROX','UA','VF','HAS','MAT','NCLH','CCL','RCL','LYV',
  // Consumer Staples
  'WMT','COST','TGT','KR','SFM','PG','KO','PEP','PM','MO',
  'STZ','BUD','TAP','SAM','FIZZ','KDP','MNST','CELH','SJM','MKC',
  'CPB','CAG','GIS','K','HRL','THS','SMPL','FRPT','CLX','CHD',
  'CL','ENR','SPB','PBH','PRGO','EL','REYN',
  // Energy
  'XOM','CVX','COP','EOG','PXD','OXY','DVN','HES','MRO','APA',
  'FANG','CTRA','MTDR','SM','CIVI','SWN','EQT','RRC','CNX','AR',
  'CHK','BKR','SLB','HAL','HP','NBR','PTEN','RIG','PSX','VLO',
  'MPC','PBF','DINO','PARR','CVI','WMB','KMI','ET','EPD','MPLX',
  'TRGP','AM','OKE','ENLC','BSM','GPRE','ALTO','REX','AMTX','GEVO',
  // Industrials
  'HON','CAT','DE','GE','EMR','ETN','ITW','PH','ROK','ROP',
  'AME','FTV','GNRC','IR','XYL','TDG','GD','RTX','LMT','NOC',
  'BA','HII','LHX','LDOS','BAH','CACI','SAIC','KTOS','RKLB','UPS',
  'FDX','ODFL','SAIA','JBHT','XPO','CSX','NSC','UNP','CP','CNI',
  'EXPD','CHRW','FWRD','KNX','WERN','CMI','PCAR','DOV','FAST','AGCO',
  'CNH','MAS','SWK','OTIS','CARR','TT','ENPH','FSLR','RUN','NOVA',
  'ARRY','SPWR','MAXN','CSIQ','DQ','ORA','SPX','FLOW','ENPRO',
  // Materials
  'LIN','APD','SHW','ECL','IFF','AVNT','RPM','HUN','OLN','CLF',
  'NUE','STLD','CMC','RS','WOR','AA','CENX','ARNC','HL','CDE',
  'PAAS','CCK','SEE','IP','WRK','PKG','GPK','SON','ATR','BERY',
  // Utilities
  'NEE','SO','DUK','D','AEP','EXC','PCG','ED','FE','ETR',
  'CMS','ES','CNP','WEC','AEE','NI','PNW','AES','AWK','NJR',
  'SR','POR','PNM','IDA','AVA','OTTR','MDU','BKH','EVRG','LNT',
  // REITs
  'PLD','AMT','EQIX','CCI','SPG','O','WELL','EQR','AVB','SBAC',
  'VICI','GLPI','WPC','BXP','VNO','SLG','KRC','NNN','EQC','DEI',
  'HIW','BDN','STAG','REXR','TRNO','EPRT','FCPT','GTY','NNN','IIPR',
  // Communication
  'NFLX','DIS','CMCSA','WBD','VZ','T','TMUS','CHTR','SIRI','EA',
  'TTWO','RBLX','SNAP','PINS','MTCH','BMBL','NYT','NWSA','FOXA','OMC',
  'IPG','ROKU','SPOT','ZG','ANGI','IAC','LBRDK','FWONA'
];

const INDIA_TICKERS = [
  // Banks & NBFCs
  'HDFCBANK.NS','ICICIBANK.NS','KOTAKBANK.NS','AXISBANK.NS','SBIN.NS',
  'INDUSINDBK.NS','BAJFINANCE.NS','BAJAJFINSV.NS','IDFCFIRSTB.NS','BANDHANBNK.NS',
  'FEDERALBNK.NS','CANBK.NS','PNB.NS','BANKBARODA.NS','UNIONBANK.NS',
  'RBLBANK.NS','YESBANK.NS','IDBI.NS','EQUITASBNK.NS','CUB.NS',
  'UCOBANK.NS','UJJIVANSFB.NS','SURYODAY.NS','KARUR.NS','J&KBANK.NS',
  'CHOLAFIN.NS','MUTHOOTFIN.NS','MANAPPURAM.NS','SHRIRAMFIN.NS','SRTRANSFIN.NS',
  'LICHSGFIN.NS','PNBHOUSING.NS','CREDITACC.NS','SPANDANA.NS','ABCAPITAL.NS',
  // Insurance, AMC, Broking
  'SBILIFE.NS','HDFCLIFE.NS','ICICIPRU.NS','STARHEALTH.NS','GICRE.NS',
  'NIACL.NS','POLICYBZR.NS','HDFCAMC.NS','UTIAMC.NS','NUVAMA.NS',
  'EDELWEISS.NS','IIFL.NS','IIFLFIN.NS','IIFLWAM.NS','MOTILALOFS.NS',
  'ANGELONE.NS','KFINTECH.NS','CDSL.NS','CAMS.NS','MCX.NS','IEX.NS',
  // IT / Technology
  'TCS.NS','INFY.NS','WIPRO.NS','HCLTECH.NS','TECHM.NS',
  'LTIM.NS','MPHASIS.NS','OFSS.NS','PERSISTENT.NS','LTTS.NS',
  'TATAELXSI.NS','TATACOMM.NS','COFORGE.NS','CYIENT.NS','BSOFT.NS',
  'KPITTECH.NS','HAPPSTMNDS.NS','TANLA.NS','RATEGAIN.NS','LATENTVIEW.NS',
  'INTELLECT.NS','NAZARA.NS','STLTECH.NS','HFCL.NS','INDIAMART.NS',
  'NAUKRI.NS','ZOMATO.NS','NYKAA.NS','PAYTM.NS','EASEMYTRIP.NS',
  'DELHIVERY.NS','CARTRADE.NS','FSL.NS','AFFLE.NS','DATAMATICS.NS',
  'ONMOBILE.NS','XCHANGING.NS','BIRLASOFT.NS','ECLERX.NS','CMSINFO.NS',
  // Pharma & Healthcare
  'SUNPHARMA.NS','DRREDDY.NS','CIPLA.NS','DIVISLAB.NS','APOLLOHOSP.NS',
  'LUPIN.NS','AUROPHARMA.NS','TORNTPHARM.NS','ALKEM.NS','IPCA.NS',
  'GRANULES.NS','AJANTPHARM.NS','PIIND.NS','PFIZER.NS','SANOFI.NS',
  'ABBOTINDIA.NS','WOCKPHARMA.NS','ERIS.NS','LAURUSLABS.NS','SOLARA.NS',
  'SEQUENT.NS','CAPLIPOINT.NS','AARTIDRUGS.NS','SYNGENE.NS','FORTIS.NS',
  'MAXHEALTH.NS','KIMS.NS','RAINBOW.NS','THYROCARE.NS','METROPOLIS.NS',
  'LALPATHLAB.NS','MEDPLUS.NS','SPARC.NS','NAVINFLUOR.NS','ALKYLAMINE.NS',
  'BALAMINES.NS','DHANUKA.NS','RALLIS.NS','SUMICHEM.NS','SHARDACROP.NS',
  'BAYERCROP.NS','DEEPAKFERT.NS','CHAMBLFERT.NS','GHCL.NS','DEEPAKNTR.NS',
  'GNFC.NS','GSFC.NS','AARTI.NS','AARTIIND.NS','FINEORG.NS',
  // Auto & Components
  'MARUTI.NS','TATAMOTORS.NS','EICHERMOT.NS','HEROMOTOCO.NS','BAJAJ-AUTO.NS',
  'TVSMOTOR.NS','ESCORTS.NS','MAHINDCIE.NS','MOTHERSON.NS','BOSCHLTD.NS',
  'SUNDRMFAST.NS','SUPRAJIT.NS','SUBROS.NS','CEATLTD.NS','JKTYRE.NS',
  'MRF.NS','BALKRISIND.NS','ZFSTEER.NS','JBMA.NS','CRAFTSMAN.NS',
  'TIINDIA.NS','SKFINDIA.NS','TIMKEN.NS','SCHAEFFLER.NS','ELGIEQUIP.NS',
  'GRINDWELL.NS','APOLLOTYRE.NS','MMFSL.NS',
  // Cement & Construction
  'ULTRACEMCO.NS','SHREECEM.NS','AMBUJACEM.NS','ACC.NS','DALBHARAT.NS',
  'RAMCOCEM.NS','JKCEMENT.NS','JKLAKSHMI.NS','NUVOCO.NS','ORIENTCEM.NS',
  'KNRCON.NS','NCC.NS','PNC.NS','IRCON.NS','PATELENG.NS',
  'MONTECARLO.NS','GPPL.NS','BRIGADE.NS','SOBHA.NS','GODREJPROP.NS',
  'OBEROIRLTY.NS','DLF.NS','MACROTECH.NS','KOLTEPATIL.NS','PHOENIXLTD.NS',
  'PRESTIGE.NS','IBREALEST.NS','RUSTOMJEE.NS',
  // Power, Energy & Metals
  'NTPC.NS','POWERGRID.NS','TATAPOWER.NS','ADANIGREEN.NS','ADANIENT.NS',
  'ADANIPORTS.NS','ADANITRANS.NS','COALINDIA.NS','ONGC.NS','BPCL.NS',
  'HINDPETRO.NS','IOC.NS','OIL.NS','PETRONET.NS','IGL.NS',
  'MGL.NS','GUJGASLTD.NS','ATGL.NS','GAIL.NS','GSPL.NS',
  'TORNTPOWER.NS','CESC.NS','IREDA.NS','NLCINDIA.NS','HUDCO.NS',
  'JSWSTEEL.NS','TATASTEEL.NS','HINDALCO.NS','VEDL.NS','NATIONALUM.NS',
  'HINDCOPPER.NS','GRAPHITE.NS','HEG.NS','NMDC.NS','SAIL.NS',
  'JSPL.NS','MOIL.NS','JINDALSTEL.NS','JINDALSAW.NS','JSL.NS',
  // FMCG / Consumer
  'HINDUNILVR.NS','ITC.NS','BRITANNIA.NS','NESTLEIND.NS','DABUR.NS',
  'MARICO.NS','COLPAL.NS','GODREJCP.NS','EMAMILTD.NS','VBL.NS',
  'RADICO.NS','TATACONSUM.NS','JUBLFOOD.NS','WESTLIFE.NS','DEVYANI.NS',
  'SAPPHIRE.NS','BIKAJI.NS','HONASA.NS','UNITDSPR.NS','GILLETTE.NS',
  'PGHH.NS','JYOTHYLAB.NS',
  // Capital Goods & Engineering
  'LT.NS','SIEMENS.NS','ABB.NS','THERMAX.NS','BHEL.NS',
  'BEL.NS','BEML.NS','HAL.NS','CUMMINSIND.NS','KALPATPOWR.NS',
  'GREAVESCOT.NS','TRIVENI.NS','TEAMLEASE.NS','ISGEC.NS','KIRLOSBROS.NS',
  'TITAGARH.NS','RATNAMANI.NS','APARINDS.NS','FINEORG.NS','AMARA.NS',
  'RITES.NS','IRFC.NS','IRCTC.NS',
  // Textiles & Miscellaneous
  'VARDHMAN.NS','WELSPUNLIV.NS','TRIDENT.NS','RAYMOND.NS','ARVINDFASN.NS',
  'CENTURYTEX.NS','KPRMILL.NS','VSTIND.NS','MIRZAINT.NS',
  // Retail, Media & Consumer Misc
  'TRENT.NS','TITAN.NS','KALYANKJIL.NS','VAIBHAVGBL.NS','PVRINOX.NS',
  'INDHOTEL.NS','LEMONTREE.NS','WONDERLA.NS','SAFARI.NS','VMART.NS',
  'METROBRAND.NS','BATAINDIA.NS','LIBERTSHOE.NS','VSTIL.NS',
  'TTKHLTCARE.NS','TTKPRESTIG.NS','SAREGAMA.NS','SUNTVNETWORK.NS',
  // Chemicals & Specialty
  'PIDILITIND.NS','BERGEPAINT.NS','KAJARIA.NS','SUPREMEIND.NS',
  'PRINCEPIPE.NS','FINOLEX.NS','ASTRAL.NS','EPL.NS','POLYCAB.NS',
  'HAVELLS.NS','CROMPTON.NS','BLUESTARCO.NS','VOLTAS.NS','WHIRLPOOL.NS',
  'DIXON.NS','AMBER.NS','ORIENTELEC.NS','OLECTRA.NS',
  // Diversified / Conglomerate
  'RELIANCE.NS','GRASIM.NS','TATACHEM.NS','TATAINVEST.NS',
  'GODREJAGRO.NS','GODREJIND.NS','BAJAJCON.NS',
  // Midcap / Smallcap additions
  'MTAR.NS','LATENTVIEW.NS','DBREALTY.NS','RPOWER.NS','SUZLON.NS',
  'DELTACORP.NS','ORIENTELEC.NS','NUVOCO.NS','STCINDIA.NS','RAMKY.NS',
  'PARADEEP.NS','MAYURUNIQ.NS','SYMPHONY.NS','ELGIEQUIP.NS','BSOFT.NS',
  'KRBL.NS','AMARAJABAT.NS','ASAHIINDIA.NS','ATUL.NS','CARBORUNIV.NS',
  'CASTROLIND.NS','CCL.NS','CENTURYPLY.NS','CHEMPLASTS.NS','CLEAN.NS',
  'DALBHARAT.NS','DEEPAKFERT.NS','DPWWORLD.NS','EQUITASBNK.NS','GALLANTT.NS',
  'GESHIP.NS','GNFC.NS','GODAWARI.NS','GPPL.NS','HAPPSTMNDS.NS',
  'HATSUN.NS','HIKAL.NS','HIMADRI.NS','INGERRAND.NS','INTELLECT.NS',
  'JBCHEPHARM.NS','JKPAPER.NS','JMFINANCIL.NS','KAMDHENU.NS','KILPEST.NS',
  'KNRCON.NS','KOPRAN.NS','LANTMANFT.NS','LINC.NS','LUXIND.NS',
  'MAHSCOOTER.NS','MEDPLUS.NS','MINDAIND.NS','NAHARPOLY.NS','NAVINFLUOR.NS',
  'NOCIL.NS','NSLNISP.NS','OLECTRA.NS','PAISALO.NS','PCJEWELLER.NS',
  'POLYMED.NS','PRSMJOHNSN.NS','RAJESHEXPO.NS','RESPONIND.NS','RUSCORP.NS',
  'SCHAEFFLER.NS','SEQUENT.NS','SHANKARA.NS','SHREEPUSHK.NS','SKFINDIA.NS',
  'SOLARA.NS','SPECIALITY.NS','SUBROS.NS','SUPRAJIT.NS','TANLA.NS',
  'TATVA.NS','TEAMLEASE.NS','THYROCARE.NS','TIMKEN.NS','TITAGARH.NS',
  'TVSSRICHAK.NS','UJJIVANSFB.NS','VAIBHAVGBL.NS','WOCKPHARMA.NS',
  'ZFSTEER.NS','ZEEL.NS','AARTIDRUGS.NS','ALKYLAMINE.NS','CAPLIPOINT.NS',
  'CRAFTSMAN.NS','CREDITACC.NS','CYIENT.NS','ELGIEQUIP.NS','EPL.NS',
  'GRANULES.NS','GRINDWELL.NS','GSFC.NS','GSPL.NS','HFCL.NS',
  'IEX.NS','IPCA.NS','IRCON.NS','JKCEMENT.NS','JKLAKSHMI.NS',
  'KALPATPOWR.NS','KFINTECH.NS','KIMS.NS','KRBL.NS','LALPATHLAB.NS',
  'LAURUSLABS.NS','LEMONTREE.NS','MCX.NS','MINDAIND.NS','MOIL.NS',
  'MONTECARLO.NS','MOTILALOFS.NS','MTAR.NS','NCC.NS','NLCINDIA.NS',
  'NMDC.NS','NOCIL.NS','NUVAMA.NS','NUVOCO.NS','NYKAA.NS',
  'ORIENTCEM.NS','PARADEEP.NS','PATELENG.NS','PHOENIXLTD.NS','PIIND.NS',
  'PNC.NS','PNBHOUSING.NS','POLYMED.NS','PVRINOX.NS','RADICO.NS',
  'RAINBOW.NS','RALLIS.NS','RAMCOCEM.NS','RATEGAIN.NS','RAYMOND.NS',
  'RENUKA.NS','RITES.NS','SAFARI.NS','SAIL.NS','SANOFI.NS',
  'SAREGAMA.NS','SCHAEFFLER.NS','SHANKARA.NS','SHRIRAMFIN.NS','SOBHA.NS',
  'SPARC.NS','SRTRANSFIN.NS','STLTECH.NS','SUBROS.NS','SUNTVNETWORK.NS',
  'SUPRAJIT.NS','SUZLON.NS','SYMPHONY.NS','TANLA.NS','TATAINVEST.NS',
  'TATVA.NS','TEAMLEASE.NS','THYROCARE.NS','TIMKEN.NS','TITAGARH.NS',
  'TRENT.NS','TRIDENT.NS','TRIVENI.NS','TTKHLTCARE.NS','TTKPRESTIG.NS',
  'UCOBANK.NS','UTIAMC.NS','VAIBHAVGBL.NS','VARDHMAN.NS','VEDL.NS',
  'VOLTAS.NS','VMART.NS','VSTIND.NS','WELSPUNLIV.NS','WESTLIFE.NS',
  'WHIRLPOOL.NS','WONDERLA.NS','YESBANK.NS','ZFSTEER.NS'
];

// ── HTTP helpers ──────────────────────────────────────────────────────────────

const HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
  Accept: 'application/json, text/plain, */*',
  'Accept-Language': 'en-US,en;q=0.9'
};

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function fetchChart(ticker, interval, range) {
  const url =
    `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}` +
    `?interval=${interval}&range=${range}&includeAdjustedClose=false`;
  const res = await fetch(url, { headers: HEADERS, signal: AbortSignal.timeout(15000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  const result = json?.chart?.result?.[0];
  if (!result) throw new Error('No data');
  const ts    = result.timestamp || [];
  const q     = result.indicators?.quote?.[0] || {};
  return ts
    .map((t, i) => ({
      time:   t,
      open:   q.open?.[i],
      high:   q.high?.[i],
      low:    q.low?.[i],
      close:  q.close?.[i],
      volume: q.volume?.[i] || 0
    }))
    .filter(c => c.open != null && c.high != null && c.low != null && c.close != null);
}

async function fetchMarketCap(ticker) {
  try {
    const url =
      `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(ticker)}` +
      `?modules=summaryDetail`;
    const res  = await fetch(url, { headers: HEADERS, signal: AbortSignal.timeout(8000) });
    if (!res.ok) return null;
    const json = await res.json();
    return json?.quoteSummary?.result?.[0]?.summaryDetail?.marketCap ?? null;
  } catch { return null; }
}

// ── Aggregation & math ────────────────────────────────────────────────────────

function aggregateTo4h(candles) {
  const result = [];
  for (let i = 0; i + 3 < candles.length; i += 4) {
    const g = candles.slice(i, i + 4);
    result.push({
      time:   g[0].time,
      open:   g[0].open,
      high:   Math.max(...g.map(c => c.high)),
      low:    Math.min(...g.map(c => c.low)),
      close:  g[3].close,
      volume: g.reduce((s, c) => s + c.volume, 0)
    });
  }
  return result;
}

function sma(arr, period) {
  if (arr.length < period) return null;
  return arr.slice(-period).reduce((a, b) => a + b, 0) / period;
}

// ── 8-check screener ──────────────────────────────────────────────────────────

async function screenTicker(ticker) {
  const hourly  = await fetchChart(ticker, '1h', '3mo');
  const candles = aggregateTo4h(hourly);
  if (candles.length < 11) return null;

  const current = candles[candles.length - 1];
  const prior10 = candles.slice(-11, -1);

  const consolidationHigh = Math.max(...prior10.map(c => Math.max(c.open, c.close)));
  const consolidationLow  = Math.min(...prior10.map(c => Math.min(c.open, c.close)));
  const rangePercent = (consolidationHigh - consolidationLow) / consolidationLow * 100;
  if (rangePercent > 12) return null;                              // 1

  if (current.close < consolidationHigh * 1.005) return null;     // 2  (≥ +0.5% above range top)

  const breakoutSize = Math.abs(current.close - current.open) / current.open * 100;
  if (breakoutSize < 1.5) return null;                             // 3  (body ≥ 1.5%)

  const avgVol10  = prior10.reduce((s, c) => s + c.volume, 0) / prior10.length;
  const relVolume = current.volume / (avgVol10 || 1);
  if (relVolume < 1.2) return null;                                // 4  (rel. vol ≥ 1.2×)

  const daily = await fetchChart(ticker, '1d', '6mo');
  if (daily.length < 50) return null;

  const dailyClose  = daily.map(d => d.close);
  const dailyVolume = daily.map(d => d.volume);

  const avgVol20d = dailyVolume.slice(-20).reduce((a, b) => a + b, 0) / Math.min(20, dailyVolume.length);
  if (avgVol20d < 500_000) return null;                            // 5

  const mc = await fetchMarketCap(ticker);
  if (mc != null && mc < 50_000_000) return null;                  // 6

  const high20d     = Math.max(...dailyClose.slice(-20));
  const high50d     = Math.max(...dailyClose.slice(-50));
  const from20dHigh = (current.close / high20d - 1) * 100;
  const from50dHigh = (current.close / high50d - 1) * 100;
  if (from20dHigh < -10 && from50dHigh < -10) return null;        // 7

  const sma20 = sma(dailyClose, 20);
  const sma50 = sma(dailyClose, 50);
  if (!sma20 || !sma50 || current.close <= sma20 || current.close <= sma50) return null; // 8

  return {
    ticker,
    price:            +current.close.toFixed(2),
    breakoutPercent:  +((current.close / consolidationHigh - 1) * 100).toFixed(2),
    breakoutSize:     +breakoutSize.toFixed(2),
    relVolume:        +relVolume.toFixed(2),
    from20dHigh:      +from20dHigh.toFixed(2),
    from50dHigh:      +from50dHigh.toFixed(2),
    avgVolume20d:     Math.round(avgVol20d),
    consolidationHigh,
    consolidationLow,
    rangePercent:     +rangePercent.toFixed(2),
    sma20:            +sma20.toFixed(2),
    sma50:            +sma50.toFixed(2)
  };
}

// ── Concurrent batch runner ───────────────────────────────────────────────────

const CONCURRENCY = 8; // parallel Yahoo Finance calls

async function runBatch(tickers, onResult) {
  const queue  = [...tickers];
  let active   = 0;
  let resolved = 0;

  return new Promise(resolve => {
    const next = () => {
      while (active < CONCURRENCY && queue.length) {
        const ticker = queue.shift();
        active++;
        screenTicker(ticker)
          .then(r  => onResult(ticker, r,  null))
          .catch(e => onResult(ticker, null, e))
          .finally(() => {
            active--;
            resolved++;
            if (queue.length || active > 0) next();
            else resolve();
          });
      }
    };
    next();
  });
}

// ── GET /api/scan  (SSE — live progress stream) ───────────────────────────────
app.get('/api/scan', (req, res) => {
  const { market } = req.query;
  if (!['india', 'usa'].includes(market)) {
    return res.status(400).json({ error: 'market must be "india" or "usa"' });
  }

  res.setHeader('Content-Type',  'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection',    'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  const tickers  = market === 'india' ? INDIA_TICKERS : USA_TICKERS;
  // De-duplicate (some symbols appear twice due to list construction)
  const unique   = [...new Set(tickers)];
  const total    = unique.length;
  const results  = [];
  let   scanned  = 0;
  let   cancelled = false;

  req.on('close', () => { cancelled = true; });

  const send = obj => {
    if (!res.writableEnded && !cancelled) res.write(`data: ${JSON.stringify(obj)}\n\n`);
  };

  runBatch(unique, (ticker, result, err) => {
    if (cancelled) return;
    if (result) results.push(result);
    scanned++;
    send({ type: 'progress', scanned, total, found: results.length, ticker });
  }).then(() => {
    if (cancelled) return;
    results.sort((a, b) => b.relVolume - a.relVolume);
    send({ type: 'done', results: results.slice(0, 50), scannedAt: new Date().toISOString() });
    res.end();
  });
});

// ── POST /api/chart ───────────────────────────────────────────────────────────
app.post('/api/chart', async (req, res) => {
  try {
    const { ticker } = req.body;
    if (!ticker) return res.status(400).json({ error: 'ticker required' });

    const hourly  = await fetchChart(ticker, '1h', '3mo');
    const candles = aggregateTo4h(hourly);
    if (candles.length < 11) return res.status(400).json({ error: 'Insufficient data' });

    const prior10 = candles.slice(-11, -1);
    res.json({
      candles:          candles.slice(-40),
      consolidationHigh: Math.max(...prior10.map(c => Math.max(c.open, c.close))),
      consolidationLow:  Math.min(...prior10.map(c => Math.min(c.open, c.close)))
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ── GET / ─────────────────────────────────────────────────────────────────────
app.get('/', (_req, res) => res.json({
  status: 'ok',
  universe: { usa: USA_TICKERS.length, india: INDIA_TICKERS.length },
  endpoints: ['GET /api/scan?market=usa|india  (SSE)', 'POST /api/chart']
}));

app.listen(3001, () => console.log('Breakout Scanner API → http://localhost:3001'));
