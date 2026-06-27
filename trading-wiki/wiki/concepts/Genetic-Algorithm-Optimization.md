---
title: "Genetic Algorithm / Population-Based Strategy Optimization"
category: concept
tags: [optimization, genetic-algorithm, parameter-search, population-algorithms]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [strategies/Systematic-Strategy-Search.md, concepts/Performance-Metrics.md]
---

# Genetic Algorithm / Population-Based Strategy Optimization

## Definition
A class of stochastic, population-based optimization algorithms used to search a strategy's parameter space for combinations that maximize a performance objective (e.g. profit factor, Sharpe), without exhaustively testing every combination. Modeled on Darwinian evolution: a "chromosome" = one full set of strategy parameter values, a "gene" = one parameter (e.g. `LookbackPeriod` for ADX), and a "population" = a generation of candidate parameter sets.

## How to Use

### Why population algorithms for strategy search
- The objective function (run a full backtest) is expensive, nonlinear, multi-extremal (many local optima), and has no analytical form — classical gradient-based optimizers don't apply.
- Population algorithms work on many candidate solutions ("agents") simultaneously, are modular (mix-and-match operators), and aim for a *suboptimal but good enough* solution in far fewer tests than brute force. A single 5-condition signal can yield ~10^35 parameter combinations — brute force is infeasible.

### General loop
1. **Initialize** a population (random or spread across the search space).
2. **Evaluate** each agent via the objective function (run backtest, get e.g. profit factor).
3. **Select** parents based on fitness.
4. **Apply mutation/crossover operators** → new generation.
5. **Check termination**: fixed number of generations, or *stagnation* (best result hasn't improved in N generations).
6. Repeat from step 2.

### Key operator families
- **Mutation operators** — randomly perturb one or more genes of an individual:
  - *Random/boundary*: replace gene with a random value in its valid range.
  - *Arithmetic creep*: `x' = x + ξ(2ψ-1)` (small bounded perturbation, ξ = free param, ψ = random 0-1).
  - *Gaussian*: `x' = x + Φ(μ,σ)` — perturbation drawn from a normal distribution.
- **Crossover operators** — combine two parent chromosomes into offspring: Flat, Blend, Arithmetical, Heuristic (biased toward the fitter parent), Linear (3 children from 1 formula), Fuzzy, Simulated Binary Crossover (SBX).
- **Filtering operators** (choose who survives into the next generation): Roulette/proportional (selection probability ∝ fitness — risks losing good solutions and premature convergence), Stochastic Universal, Tournament (group of n, pick best — typical n=2-3), Rank-based (probability by rank, not raw fitness — reduces premature stagnation), Elitism (guarantee top X% survive, e.g. top 10% kept + 90% via roulette), Clipping (threshold-based), Crowding (remove near-duplicate individuals via a distance/Euclidean-norm measure to preserve diversity).
- **Selection operators** (choose parent pairs for crossover): Panmixia (random, equal probability — degrades at large population sizes), Selective selection (only above-average-fitness individuals can be parents — fast but risks early local-minimum convergence), Inbreeding (pair similar individuals — fast convergence within sub-groups), Outbreeding (pair dissimilar individuals — preserves diversity).

### Handling constraint violations (out-of-range parameters)
Mutation/crossover can produce parameter values outside valid bounds. Options:
- **Death penalty**: discard invalid individuals and regenerate (risk of infinite loops if the valid region is small).
- **Static/dynamic penalty functions**: subtract a penalty from fitness proportional to the number/severity of violated bounds; dynamic penalties increase the penalty weight as generations progress (recommended free-parameter starting point: a=-0.5, b=2.0, c=2.0).
- **Sliding tolerance**: allow violations within a shrinking tolerance band that tightens each generation — soft constraints early, hard constraints late.
- **Segregated GA**: maintain two penalty functions, sort separately, merge and keep the least-violating half.
- **Reduction**: walk a mutated/invalid individual's genes back toward their pre-mutation values one at a time until it becomes valid again.

### Intensity vs. breadth tradeoff
- *Intensity* = fast convergence to a solution; *breadth* = diversification across the search space to avoid missing the true optimum.
- Self-adaptation mechanisms gradually shift the balance from breadth (early generations) to intensity (later generations) — analogous to "wide-range coarse search → narrow refinement" in [[strategies/Systematic-Strategy-Search]].
- Because population algorithms are stochastic, results vary run-to-run even with identical parameters — evaluate via **multistart** (multiple runs of the same config).

## Variants / Parameters
- Other optimization algorithm classes mentioned (for comparison/contrast, not detailed): grid search (brute force), random search, simulated annealing — all viable alternatives to genetic algorithms depending on dimensionality and budget.

## Common Mistakes
- Running a full-precision genetic search directly on a huge parameter space without a coarse pre-filter — combine with the [[strategies/Systematic-Strategy-Search]] three-step (coarse quality filter → iterative narrowing → forward test) approach instead of one giant GA run.
- Using roulette-only selection on small populations — high risk of premature convergence; prefer rank-based or elitism + roulette hybrids.
- Treating a single GA run's result as definitive — use multistart given the stochastic nature of these algorithms.

## Related Concepts
- [[strategies/Systematic-Strategy-Search]] — the broader Theory→SubTheory→Strategy pipeline that GA fits into as the "choose optimization algorithm" step
- [[concepts/Performance-Metrics]] — the objective function that GA agents are evaluated against

## Examples in This Wiki
- Not yet applied — candidate for a future "parameter sweep" tool for [[strategies/PMax-Confluence-Strategy]] or [[strategies/Screener-Queries]] thresholds (e.g. CCI(34) threshold, ATR multiplier).

## Sources
- [[sources/Dolzhenko-Algorithmic-Trading-Systems-2024]] (2026-06-15)
