#!/usr/bin/env python3
"""Shared loaders and statistical helpers for the growth-forensics analyses.

Sources (all open):
  - World Bank WDI (data/wdi.parquet, data/countries.parquet)  [fetch_wdi.py]
  - IMF datamapper current vintage (data/imf_datamapper.parquet) [fetch_other.py]
  - Worldwide Governance Indicators (data/wgi.parquet)          [fetch_other.py]
  - Penn World Table 11.0 (data/pwt110.xlsx) and 10.01 (data/pwt1001.dta)
  - Maddison Project Database 2023 (data/mpd2023.dta)
  - IMF WEO historical vintages, Spring/Fall 1990-2022 (data/WEOhistorical.xlsx)
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260709)

SSA = "Sub-Saharan Africa"
DEVELOPING_INCOME = {"Low income", "Lower middle income", "Upper middle income"}


# ---------------------------------------------------------------- loading

def load_countries() -> pd.DataFrame:
    return pd.read_parquet("data/countries.parquet")


def load_wdi() -> pd.DataFrame:
    df = pd.read_parquet("data/wdi.parquet")
    wgi = pd.read_parquet("data/wgi.parquet")
    return df.merge(wgi, on=["iso3", "year"], how="left")


def load_imf() -> pd.DataFrame:
    df = pd.read_parquet("data/imf_datamapper.parquet")
    return df.rename(columns={"NGDP_RPCH": "imf_growth", "PCPIPCH": "imf_inflation"})


def _pwt_growth(df: pd.DataFrame, gdpcol: str, out: str) -> pd.DataFrame:
    df = df.sort_values(["countrycode", "year"]).copy()
    df[out] = df.groupby("countrycode")[gdpcol].pct_change() * 100
    return df.rename(columns={"countrycode": "iso3"})[["iso3", "year", out]]


def load_pwt11() -> pd.DataFrame:
    df = pd.read_stata("data/pwt110.dta")
    return _pwt_growth(df, "rgdpna", "pwt11_growth")


def load_pwt1001() -> pd.DataFrame:
    df = pd.read_stata("data/pwt1001.dta")
    g = _pwt_growth(df, "rgdpna", "pwt10_growth")
    # statistical capacity indicator shipped with PWT 10.01
    cap = (
        df.rename(columns={"countrycode": "iso3"})
        .groupby("iso3", as_index=False)["statcap"]
        .mean()
        .rename(columns={"statcap": "pwt_statcap"})
    )
    return g, cap


def load_maddison() -> pd.DataFrame:
    df = pd.read_stata("data/mpd2023.dta")
    df = df.sort_values(["countrycode", "year"])
    df["gdp"] = df["gdppc"] * df["pop"]
    df["mpd_growth"] = df.groupby("countrycode")["gdp"].pct_change() * 100
    # Maddison is annual only in recent era; restrict to continuous coverage
    df = df[df.year >= 1950]
    return df.rename(columns={"countrycode": "iso3"})[["iso3", "year", "mpd_growth"]]


_VINTAGE_RE = re.compile(r"^([SF])(\d{4})ngdp_rpch$")


def load_weo_vintages() -> pd.DataFrame:
    """Long panel: iso3, year (target), vintage_year, season, value."""
    raw = pd.read_excel("data/WEOhistorical.xlsx", sheet_name="ngdp_rpch")
    rows = []
    vcols = [c for c in raw.columns if _VINTAGE_RE.match(str(c))]
    long = raw.melt(
        id_vars=["ISOAlpha_3Code", "year"], value_vars=vcols,
        var_name="vintage", value_name="value",
    ).rename(columns={"ISOAlpha_3Code": "iso3"})
    m = long["vintage"].str.extract(_VINTAGE_RE)
    long["season"] = m[0]
    long["vintage_year"] = m[1].astype(int)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.dropna(subset=["value", "iso3"])
    # order index: spring = .0, fall = .5
    long["vorder"] = long["vintage_year"] + np.where(long["season"] == "F", 0.5, 0.0)
    return long[["iso3", "year", "season", "vintage_year", "vorder", "value"]]


def weo_first_and_latest(long: pd.DataFrame) -> pd.DataFrame:
    """For each country-year: the first post-year estimate (usually the
    Spring vintage of year t+1) and the last estimate in the vintage file
    (Fall of t+2 — the file carries vintages t-5 .. t+2 for each target year).

    The fully-revised "final" value is NOT in this file; merge the current
    IMF datamapper series to compute long-run revisions.
    """
    est = long[long.vorder >= long.year + 1].sort_values("vorder")
    first = est.groupby(["iso3", "year"]).first().rename(columns={"value": "first_print"})
    latest = est.groupby(["iso3", "year"]).last().rename(columns={"value": "t_plus2"})
    out = (
        first[["first_print", "vorder"]]
        .rename(columns={"vorder": "first_vorder"})
        .join(latest[["t_plus2", "vorder"]].rename(columns={"vorder": "latest_vorder"}))
        .reset_index()
    )
    # short-run revision within the vintage file (~1.5 years of updating)
    out["rev_short"] = np.where(
        out.latest_vorder > out.first_vorder, out.t_plus2 - out.first_print, np.nan
    )
    return out


def attach_region(df: pd.DataFrame) -> pd.DataFrame:
    c = load_countries()[["iso3", "region", "income"]]
    return df.merge(c, on="iso3", how="inner")


def region_group(df: pd.DataFrame) -> pd.Series:
    """SSA vs other developing vs high income."""
    grp = np.where(
        df.region == SSA,
        "Sub-Saharan Africa",
        np.where(df.income.isin(DEVELOPING_INCOME), "Other developing", "High income"),
    )
    return pd.Series(grp, index=df.index, name="group")


# ---------------------------------------------------------- inference helpers

def cluster_boot_mean(df, col, cluster="iso3", n=2000, stat=np.nanmean):
    """Bootstrap CI for stat(col), resampling clusters (countries)."""
    groups = {k: v[col].to_numpy() for k, v in df.groupby(cluster)}
    keys = list(groups)
    point = stat(df[col].to_numpy())
    sims = np.empty(n)
    for i in range(n):
        draw = RNG.choice(len(keys), size=len(keys), replace=True)
        sims[i] = stat(np.concatenate([groups[keys[j]] for j in draw]))
    lo, hi = np.nanpercentile(sims, [2.5, 97.5])
    return point, lo, hi, sims


def perm_test_groups(df, col, groupcol, cluster="iso3", n=4000, stat=np.nanmean):
    """Permutation test for stat(group A) - stat(group B), where `groupcol`
    is a boolean column constant within cluster; labels are permuted at the
    country level."""
    labels = df.groupby(cluster)[groupcol].first()
    groups = {k: v[col].to_numpy() for k, v in df.groupby(cluster)}
    keys = np.array(list(groups))
    lab = labels.loc[keys].to_numpy()

    def diff(l):
        a = np.concatenate([groups[k] for k, m in zip(keys, l) if m])
        b = np.concatenate([groups[k] for k, m in zip(keys, l) if not m])
        return stat(a) - stat(b)

    obs = diff(lab)
    cnt = 0
    for _ in range(n):
        cnt += abs(diff(RNG.permutation(lab))) >= abs(obs)
    return obs, (cnt + 1) / (n + 1)


# ------------------------------------------------------------- digit helpers

BENFORD_2ND = np.array(
    [sum(np.log10(1 + 1 / (10 * k + d)) for k in range(1, 10)) for d in range(10)]
)


def second_digit(x: float) -> int | None:
    s = re.sub(r"[^0-9]", "", f"{x:.15e}".split("e")[0])
    s = s.lstrip("0")
    return int(s[1]) if len(s) >= 2 else None


def second_digit_dist(values) -> np.ndarray:
    digs = [second_digit(v) for v in values if v and np.isfinite(v) and v > 0]
    digs = [d for d in digs if d is not None]
    counts = np.bincount(digs, minlength=10).astype(float)
    return counts


def chi2_stat(counts: np.ndarray, probs: np.ndarray) -> float:
    n = counts.sum()
    exp = probs * n
    return float(((counts - exp) ** 2 / exp).sum())


def first_decimal_digit(x: float) -> int:
    return int(round(abs(x) * 10)) % 10
