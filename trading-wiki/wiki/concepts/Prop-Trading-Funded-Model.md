---
title: "Prop Trading Funded Model"
category: concept
tags: [prop-trading, funded-accounts, evaluation, apex, ftmo, topstep, risk-management, trailing-drawdown]
created: 2026-06-17
updated: 2026-08-29
sources: 3
related:
  - sources/Prop-Trading-Secrets-Lien-Crete-2025.md
  - concepts/Trading-Psychology-Champion.md
  - concepts/Capital-Management-Methods.md
  - concepts/Initial-Balance.md
  - analyses/Kalyan-Trading-Philosophy.md
---

# Prop Trading Funded Model

## Definition

Modern prop trading firms offer retail traders access to large simulated accounts in exchange for a one-time evaluation fee. Traders who pass a challenge (hit a profit target while staying within a maximum drawdown) receive a "funded" account and keep 70–90% of all profits withdrawn. The trader's maximum liability is the evaluation fee.

This model democratized access to significant trading capital for retail traders from any background, removing the traditional barrier of working for an institutional prop desk.

## How It Works

### Stage 1: Evaluation (Challenge)
- **Cost**: $500–$600 for a $100,000 account (typical; varies by firm/account size)
- **Profit target**: 8–10% of account size
- **Max daily drawdown**: 3–5% of account
- **Max total drawdown**: 8–12% (often "trailing" — locks in from peak balance including unrealized)
- **Minimum trading days**: 5–10 (forces consistency; prevents lucky one-day passing)
- **Position close requirement**: most futures firms require flat by 4:59 p.m. EST; some forex firms allow swing

### Stage 2: Funded Account (Performance Account)
- Trade the same rules with firm's simulated capital
- Trailing drawdown "fixes" once sufficient cushion is built (e.g., Apex: fixes at $300,100 once you reach $307,600 on a $300K account — then you have a permanent $7,500 drawdown floor)
- Withdraw profits periodically (daily, weekly, or monthly depending on firm); withdrawals are real cash from firm's P&L

### Trailing Drawdown Mechanics (Critical)
- Calculated from **peak equity** (realized + unrealized combined at most futures firms)
- An open unrealized gain expands your trailing threshold; if the trade reverses, the threshold does NOT come back down — it locks at the peak
- **Protection strategy**: scale out of winning trades early to "lock in" the threshold before the trade can reverse

## Scaling Strategy — Vince Koehn Model

> "Scale with accounts, not contracts."

- Trade 1–3 contracts per account across 20 accounts
- Same rules, same discipline, same conservative stops
- Per-account gain: $250–$500/day × 20 accounts = $5,000–$10,000/day
- Risk per account stays manageable; trailing drawdown stays proportional to account size
- **Practical approach**: work in groups of 3–5 accounts; hit daily mini-target → protect gains → shift to next group

Why this works better than scaling contracts on one account:
- 20 contracts on one account magnifies slippage, expands trailing drawdown exposure, and amplifies psychology pressure
- 1 contract × 20 accounts keeps each individual decision small and calm

## Key Prop Firms

| Firm | Focus | Notable Feature |
|------|-------|-----------------|
| Apex Trader Funding | Futures (NQ, ES, YM) | Trailing drawdown model; CEO known for personal outreach to traders |
| FTMO | Forex, indices, CFDs | Oldest/most recognized; forex and CFD focus |
| Topstep | Futures | US-based; established track record |
| Darwinex | Forex | UCITS-backed; path to real AUM management |

## Evaluation vs. Funded Strategy

| Aspect | Evaluation Mode | Funded Mode |
|--------|----------------|-------------|
| Risk per trade | Very conservative (0.25–0.5%) | Same; never increase just because funded |
| Daily target | Break into daily sub-goals | Let account grow steadily with same targets |
| Trailing drawdown | Protect from peak at all times | Same; when fixed, slightly less acute |
| News trading | Often prohibited | Check firm rules |
| Strategy | Carry forward what worked in demo | Same strategy as evaluation |

**Key rule**: never change strategy from evaluation to funded account. If a strategy passed the evaluation, it passes because it works. Don't chase bigger profits by switching.

## Prop-Specific Psychology

- **Recency-bias trap**: Many prop challenges incentivize short-term thinking (monthly targets). Counter by anchoring to process over 30/60/90-day arc.
- **Evaluation pressure psychology**: Fear of "wasting the fee" causes over-trading. Treat the evaluation fee as trading tuition, not a bet.
- **First-trade tone**: Never start an evaluation day with a full-size, aggressive position. The first trade sets the psychological tone for the session.
- **Three-strikes rule**: After 3 losses in a day → stop. Revenge trading on a prop account quickly breaches daily drawdown limits. (Used by Matt Miller, Rob Hoffman, others.)
- **Over-leveraging mistake**: #1 cause of evaluation failure; large contracts on a news event → slippage takes out trailing drawdown even on a correct directional call.

## Choosing a Prop Firm — Due Diligence Checklist

1. **Longevity**: Prefer firms in business >2 years; prop firms have shut down with trader funds
2. **Technology**: In-house platform or third-party white label? (White label = more intermediary risk)
3. **Liquidity providers**: Named transparently? (Legitimate firms disclose who fills their trades)
4. **Reputation**: Trustpilot + PropFirmMatch reviews; look for payout consistency issues specifically
5. **Rules compatibility**: Does your strategy comply?
   - EAs (expert advisors / bots) allowed?
   - News trading allowed? (Many firms ban 5 min before/after major releases)
   - Swing trading (hold over weekend)? (Most futures firms disallow; most forex firms allow)
6. **Customer service**: Multiple channels, real response time
7. **Payout terms**: Minimum days before first withdrawal? Payout frequency? Payout size limits?

## The "target ÷ drawdown = your R" argument, and why it is wrong (2026-08-29)

A widely repeated piece of prop-firm reasoning, stated plainly in
[[sources/YT-Chris-Kmer-World-Cup-Order-Flow]]:

> The drawdown is 2,000 but the profit target is 3,000. It's literally a 1.5R. So if you
> just constantly take 1.5R trades, then you'll be fine.

**This is a unit error.** `R` is a *per-trade* quantity (reward ÷ the risk taken on that
trade). The 3,000/2,000 ratio is a *per-account* quantity (target ÷ maximum drawdown).
They are not the same measure and one does not license the other. Whether you reach
+3,000 before −2,000 is a **gambler's-ruin** question determined by per-trade risk size
relative to the buffer, win rate, and the *sequence* of outcomes — a trader taking 1.5R
setups at a 50% win rate is a coin flip to bust, and one risking 1,000 per trade can be
out in two trades regardless of payoff ratio.

The underlying point survives the bad argument: a small drawdown buffer *does* force
larger per-trade risk than a personal account would justify, and that is a real structural
feature of the evaluation model — the trader's downside is capped at the evaluation fee,
which genuinely changes optimal aggression. In the cited case the implied sizing is
**4–8% of account risked per trade**, against the **0.5%** default in
[[concepts/Capital-Management-Methods]].

**What does not transfer:** that sizing, to a personal account. The asymmetry that
justifies it — capped downside, someone else's capital — does not exist there.

## Prop firms as a game-theory problem (2026-08-29)

From [[sources/YT-Pro-Trader-Amygdala-Options-Philosophy]], said without hostility —
"we're all adults" — and worth pricing in rather than resenting.

**Whose side the incentives are on.** If a firm's only product is *simulated* funding, its
interests are **diametrically opposed** to its clients': it wants you to lose, but not so
much that you quit, and it wants a handful of winners as aspirational marketing. That is
not a scandal, it is the business model — but it should be read before, not after.

**Counterparty risk is the real risk.** *"They just might not pay you."* These are
unregulated private businesses; the recourse when a legitimate payout is denied is public
noise, and perhaps the firm closing. Accept that risk explicitly at purchase or don't buy.

**Where to look for alignment.** Not necessarily live capital. If you can hold $1M across
simulated accounts against a $200k live ceiling, the sim programme is where the money is —
the question is *which stage of which programme* aligns the firm's payout with your
performance, and that varies by firm.

**Rules incentivise behaviour — that is where traders actually get hurt.**

> "It's not whether you know the rules and decide to follow them or not. It's if you don't
> understand how the rules incentivise certain types of behaviour."

Consistency rules, in his read, serve the firm rather than the trader — which is fine if
you know it. The task is to identify the behaviour a given rule set pushes you into and
decide whether you still have an edge *inside that behaviour*. A worked example he gives:
where evaluations are cheap and fast, treat the pass as a modelled cost of doing business
(size the account to your expected pass rate, accept failing more often than passing) — and
then **trade the funded stage completely differently**.

**Would he start on prop today? Yes, 100%** — while preparing for the day he has to trade
his own capital, build a track record, and raise money responsibly. But the two are not the
same skill:

> "Just because you play Call of Duty doesn't make you a real soldier."

He also thinks we are in the **late stages** of the prop-firm golden era.

## Common Mistakes

1. Going from learning straight to funded account — prove consistency with personal money first
2. Over-leveraging because "it's not my money" — treat it exactly like real money; you can withdraw it
3. Waiting too long to withdraw — "profits only become real when they hit your bank account" (Chapter 17)
4. Withdrawing too aggressively — leaving yourself too close to trailing drawdown threshold
5. Trading evaluations during a losing streak — psychological state carries into your trading
6. Ignoring trailing drawdown mechanics — a winning unrealized position expanding to peak then reversing can breach the account before you act

## Related Concepts

- [Capital Management Methods](Capital-Management-Methods.md) — Kelly, Optimal-f: applicable to sizing within prop accounts
- [Trading Psychology Champion](Trading-Psychology-Champion.md) — mindset layer for evaluation and funded phases
- [Initial Balance](Initial-Balance.md) — NQ scalping strategy widely used by prop traders
- [Performance Metrics](Performance-Metrics.md) — track record building and Sharpe/profit factor for evaluation

## Sources

1. [Prop-Trading-Secrets-Lien-Crete-2025](../sources/Prop-Trading-Secrets-Lien-Crete-2025.md) — All 17 chapters (Lien & Crete, 2025)
2. [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]] — evaluation-vs-personal sizing asymmetry; the target÷drawdown "R" fallacy
3. [[sources/YT-Pro-Trader-Amygdala-Options-Philosophy]] — sim-firm incentive opposition; counterparty risk; rules-incentivise-behaviour
