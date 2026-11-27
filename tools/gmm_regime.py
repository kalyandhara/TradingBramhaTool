#!/usr/bin/env python3
"""gmm_regime.py — a 2-component Gaussian-mixture market regime (B-174).

A probabilistic regime from NIFTY's own (return, volatility) pairs: EM fits two
Gaussian clouds, and the one with the higher mean volatility is "stressed".
Plain numpy, no scikit-learn. Deterministic: initialised by splitting the
training window at the median of volatility, so the same data always gives the
same fit.

UNMEASURED until B-174 reports (analyses/GMM-Regime-vs-Verdict). Nothing on the
desk reads this; it exists to be tested against `market_verdict.classify_regime`.

    probs = rolling_stress(close)       # P(stressed) per day, point-in-time
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VOL_WINDOW = 20
TRAIN = 750
REFIT_EVERY = 21
MAX_ITER = 200
TOL = 1e-6


def features(close: pd.Series) -> pd.DataFrame:
    """(r, v): daily log return and the std of the last 20 of them."""
    r = np.log(close.astype(float)).diff()
    return pd.DataFrame({"r": r, "v": r.rolling(VOL_WINDOW).std()}).dropna()


def _logpdf(x: np.ndarray, mu: np.ndarray, cov: np.ndarray) -> np.ndarray:
    d = x - mu
    inv = np.linalg.inv(cov)
    _, logdet = np.linalg.slogdet(cov)
    return -0.5 * (np.einsum("ij,jk,ik->i", d, inv, d) + logdet + x.shape[1] * np.log(2 * np.pi))


def fit(x: np.ndarray, vol_col: int = 1) -> dict:
    """EM for a 2-component full-covariance mixture. Component 1 is always the
    higher-mean-volatility ("stressed") one."""
    n, k = len(x), 2
    split = x[:, vol_col] > np.median(x[:, vol_col])
    resp = np.column_stack([~split, split]).astype(float)
    ll_old = -np.inf
    reg = 1e-6 * np.eye(x.shape[1])
    for _ in range(MAX_ITER):
        nk = resp.sum(0) + 1e-12
        w = nk / n
        mu = (resp.T @ x) / nk[:, None]
        cov = np.array([((resp[:, j, None] * (x - mu[j])).T @ (x - mu[j])) / nk[j] + reg
                        for j in range(k)])
        logp = np.column_stack([np.log(w[j]) + _logpdf(x, mu[j], cov[j]) for j in range(k)])
        m = logp.max(1, keepdims=True)
        ll = float((m[:, 0] + np.log(np.exp(logp - m).sum(1))).sum())
        resp = np.exp(logp - m)
        resp /= resp.sum(1, keepdims=True)
        if abs(ll - ll_old) < TOL * max(1.0, abs(ll)):
            break
        ll_old = ll
    order = np.argsort(mu[:, vol_col])            # [calm, stressed]
    return {"w": w[order], "mu": mu[order], "cov": cov[order], "loglik": ll}


def posterior(model: dict, x: np.ndarray) -> np.ndarray:
    """P(stressed) for each row of ``x``."""
    logp = np.column_stack([np.log(model["w"][j]) + _logpdf(x, model["mu"][j], model["cov"][j])
                            for j in range(2)])
    m = logp.max(1, keepdims=True)
    p = np.exp(logp - m)
    return p[:, 1] / p.sum(1)


def rolling_stress(close: pd.Series, train: int = TRAIN,
                   refit_every: int = REFIT_EVERY) -> pd.Series:
    """P(stressed) per day, point-in-time: each fit sees only the trailing
    ``train`` days up to its refit day, standardised with THAT window's moments,
    and scores days until the next refit."""
    f = features(close)
    vals = f.to_numpy()
    out = pd.Series(np.nan, index=f.index)
    model = mean = sd = None
    for i in range(train - 1, len(f)):
        if model is None or (i - (train - 1)) % refit_every == 0:
            win = vals[i - train + 1:i + 1]
            mean, sd = win.mean(0), win.std(0)
            model = fit((win - mean) / sd)
        out.iloc[i] = posterior(model, ((vals[i] - mean) / sd)[None, :])[0]
    return out.dropna()
