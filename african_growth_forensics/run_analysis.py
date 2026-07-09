#!/usr/bin/env python3
"""Run the full forensic battery and write results/ + figures/.

Every test is symmetric: it is run identically for Sub-Saharan Africa,
other developing countries, and high-income countries, with country-clustered
resampling for inference. Nothing is conditioned on finding a problem.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

import lib
from lib import RNG

os.makedirs("results", exist_ok=True)
os.makedirs("figures", exist_ok=True)

YR0, YR1 = 1990, 2019  # primary window: post-1990 coverage, pre-COVID

results: dict = {"window": [YR0, YR1]}

# ------------------------------------------------------------------ load
print("loading sources ...")
wdi = lib.load_wdi()
imf = lib.load_imf()
pwt11 = lib.load_pwt11()
pwt10, statcap = lib.load_pwt1001()
mpd = lib.load_maddison()
weo = lib.load_weo_vintages()
weo_fl = lib.weo_first_and_latest(weo)

panel = (
    wdi.merge(imf, on=["iso3", "year"], how="left")
    .merge(pwt11, on=["iso3", "year"], how="left")
    .merge(pwt10, on=["iso3", "year"], how="left")
    .merge(mpd, on=["iso3", "year"], how="left")
)
panel["group"] = lib.region_group(panel)
panel["is_ssa"] = panel.group == "Sub-Saharan Africa"

GROUPS = ["Sub-Saharan Africa", "Other developing", "High income"]

results["n_countries"] = panel.groupby("group").iso3.nunique().to_dict()


def by_group(df, fn):
    return {g: fn(df[df.group == g]) for g in GROUPS if (df.group == g).any()}


# =====================================================================
# A1. Cross-source disagreement: same country, same year, three sources
# =====================================================================
print("A1: cross-source disagreement ...")
w = panel.query(f"{YR0} <= year <= {YR1}").copy()
src = ["gdp_growth", "imf_growth", "pwt11_growth"]
a1 = w.dropna(subset=src, how="any").copy()
vals = a1[src].to_numpy()
a1["spread"] = vals.max(axis=1) - vals.min(axis=1)  # max pairwise gap, pp
a1["d_wdi_imf"] = (a1.gdp_growth - a1.imf_growth).abs()
a1["d_wdi_pwt"] = (a1.gdp_growth - a1.pwt11_growth).abs()
a1["d_imf_pwt"] = (a1.imf_growth - a1.pwt11_growth).abs()

cmed = (
    a1.groupby(["iso3", "group"], as_index=False)
    .agg(median_spread=("spread", "median"), n=("spread", "size"))
    .query("n >= 10")
)
results["A1_cross_source"] = {
    "n_country_years": int(len(a1)),
    "median_spread_by_group": by_group(a1, lambda d: float(d.spread.median())),
    "mean_spread_by_group": by_group(a1, lambda d: float(d.spread.mean())),
    "country_median_spread_by_group": {
        g: float(cmed[cmed.group == g].median_spread.median()) for g in GROUPS
    },
    "pairwise_median_by_group": {
        g: {
            "wdi_vs_imf": float(a1[a1.group == g].d_wdi_imf.median()),
            "wdi_vs_pwt": float(a1[a1.group == g].d_wdi_pwt.median()),
            "imf_vs_pwt": float(a1[a1.group == g].d_imf_pwt.median()),
        }
        for g in GROUPS
    },
}
dev = a1[a1.group != "High income"].copy()
obs, p = lib.perm_test_groups(dev, "spread", "is_ssa", stat=np.nanmedian)
results["A1_cross_source"]["ssa_vs_otherdev_median_diff_pp"] = float(obs)
results["A1_cross_source"]["perm_p"] = float(p)

# share of country-years where sources disagree by more than 2pp / 5pp
for th in (2, 5):
    results["A1_cross_source"][f"share_spread_gt{th}pp"] = by_group(
        a1, lambda d, t=th: float((d.spread > t).mean())
    )

# SPI correlation (country level)
spi = wdi.groupby("iso3", as_index=False).spi_overall.mean()
cc = cmed.merge(spi, on="iso3").merge(statcap, on="iso3", how="left")
rho = cc[["median_spread", "spi_overall"]].corr(method="spearman").iloc[0, 1]
results["A1_cross_source"]["spearman_spread_vs_spi"] = float(rho)
cc.to_csv("results/country_disagreement.csv", index=False)

# =====================================================================
# A2. Deflator vs CPI gap (real growth can be inflated by a low deflator)
# =====================================================================
print("A2: deflator-CPI gap ...")
a2 = panel.query(f"{YR0} <= year <= 2024").dropna(
    subset=["deflator_growth", "cpi_inflation"]
)
a2 = a2[(a2.deflator_growth.abs() < 50) & (a2.cpi_inflation.abs() < 50)].copy()
a2["gap"] = a2.cpi_inflation - a2.deflator_growth  # >0: deflator below CPI
cgap = a2.groupby(["iso3", "group"], as_index=False).agg(
    median_gap=("gap", "median"), n=("gap", "size")
).query("n >= 10")
results["A2_deflator_gap"] = {
    "n_country_years": int(len(a2)),
    "median_gap_by_group": by_group(a2, lambda d: float(d.gap.median())),
    "country_median_gap_by_group": {
        g: float(cgap[cgap.group == g].median_gap.median()) for g in GROUPS
    },
    "share_countries_gap_gt1pp": {
        g: float((cgap[cgap.group == g].median_gap > 1).mean()) for g in GROUPS
    },
}
dev2 = a2[a2.group != "High income"]
obs, p = lib.perm_test_groups(dev2, "gap", "is_ssa", stat=np.nanmedian)
results["A2_deflator_gap"]["ssa_vs_otherdev_median_diff_pp"] = float(obs)
results["A2_deflator_gap"]["perm_p"] = float(p)

# cumulative implication: for countries with gap>0, implied overstatement of
# cumulative real growth if CPI were the correct deflator
cg = cgap[cgap.group == "Sub-Saharan Africa"].median_gap
results["A2_deflator_gap"]["ssa_median_country_gap_pp_per_year"] = float(cg.median())

# =====================================================================
# A3. Digit forensics
# =====================================================================
print("A3: digit forensics ...")


def benford2_test(values, nsim=4000):
    counts = lib.second_digit_dist(values)
    n = int(counts.sum())
    if n < 200:
        return None
    stat = lib.chi2_stat(counts, lib.BENFORD_2ND)
    sims = np.array([
        lib.chi2_stat(
            np.bincount(RNG.choice(10, size=n, p=lib.BENFORD_2ND), minlength=10),
            lib.BENFORD_2ND,
        )
        for _ in range(nsim)
    ])
    return {
        "n": n,
        "chi2": float(stat),
        "p_sim": float(((sims >= stat).sum() + 1) / (nsim + 1)),
        "dist": (counts / n).round(4).tolist(),
    }


lcu = panel.dropna(subset=["gdp_lcu"])
results["A3_benford2_gdp_lcu"] = by_group(lcu, lambda d: benford2_test(d.gdp_lcu))

# decimal-digit heaping in WEO first prints
fp = lib.attach_region(weo_fl.dropna(subset=["first_print"]))
fp = fp.merge(imf[["iso3", "year", "imf_growth"]], on=["iso3", "year"], how="left")
fp["group"] = lib.region_group(fp)
fp["is_ssa"] = fp.group == "Sub-Saharan Africa"
# long-run revision: today's fully revised IMF value minus the first print
fp["latest"] = fp.imf_growth
fp["revision"] = fp.latest - fp.first_print


def heaping_test(values, nsim=4000):
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    digs = np.array([lib.first_decimal_digit(x) for x in v])
    counts = np.bincount(digs, minlength=10).astype(float)
    n = int(counts.sum())
    if n < 200:
        return None
    unif = np.full(10, 0.1)
    stat = lib.chi2_stat(counts, unif)
    sims = np.array([
        lib.chi2_stat(np.bincount(RNG.choice(10, size=n), minlength=10), unif)
        for _ in range(nsim)
    ])
    share05 = float((counts[0] + counts[5]) / n)
    integer_share = float(np.mean(np.isclose(v, np.round(v))))
    return {
        "n": n,
        "chi2_vs_uniform": float(stat),
        "p_sim": float(((sims >= stat).sum() + 1) / (nsim + 1)),
        "share_decimal_0_or_5": share05,
        "share_exact_integers": integer_share,
        "dist": (counts / n).round(4).tolist(),
    }


results["A3_heaping_weo_first_prints"] = by_group(fp, lambda d: heaping_test(d.first_print))

# =====================================================================
# A4. Discontinuity at zero in first-print growth (recession avoidance)
# =====================================================================
print("A4: discontinuity at zero ...")


def bd_test(values, width=0.5, lo=-10, hi=15):
    """Burgstahler-Dichev standardized difference for the bin left of zero."""
    v = np.asarray(values, float)
    v = v[(v >= lo) & (v < hi) & np.isfinite(v)]
    edges = np.arange(lo, hi + width, width)
    hist, _ = np.histogram(v, bins=edges)
    iz = int(np.searchsorted(edges, 0.0)) - 1  # bin [-width, 0)
    n = hist.sum()

    def z(i):
        exp = (hist[i - 1] + hist[i + 1]) / 2
        pi = hist[i] / n
        var = n * pi * (1 - pi) + 0.25 * n * (
            (hist[i - 1] / n) * (1 - hist[i - 1] / n)
            + (hist[i + 1] / n) * (1 - hist[i + 1] / n)
        )
        return float((hist[i] - exp) / np.sqrt(var)) if var > 0 else np.nan

    return {
        "n": int(n),
        "z_left_of_zero": z(iz),        # negative => too few small negatives
        "z_right_of_zero": z(iz + 1),   # positive => too many small positives
        "counts_around_zero": hist[iz - 2 : iz + 3].tolist(),
    }


results["A4_zero_discontinuity_first_prints"] = by_group(
    fp, lambda d: bd_test(d.first_print)
)
# same test on final (latest-vintage) data — does the kink survive revision?
lt = fp.dropna(subset=["latest"])
results["A4_zero_discontinuity_latest"] = by_group(lt, lambda d: bd_test(d.latest))

# =====================================================================
# A5. Revision forensics: first print vs latest vintage
# =====================================================================
print("A5: revisions ...")
# restrict to target years with >=4 years of settling time before the
# current vintage, and drop first prints that were themselves projections
rv = fp.dropna(subset=["revision"]).query("year <= 2021").copy()
rv["abs_rev"] = rv.revision.abs()
rv["rev_short_abs"] = rv.rev_short.abs()


def rev_summary(d):
    pt, lo, hi, _ = lib.cluster_boot_mean(d, "revision")
    return {
        "n": int(len(d)),
        "mean_revision_pp": float(pt),
        "ci95": [float(lo), float(hi)],
        "median_abs_revision_pp": float(d.abs_rev.median()),
        "share_abs_gt1pp": float((d.abs_rev > 1).mean()),
        "share_abs_gt2pp": float((d.abs_rev > 2).mean()),
        "median_abs_short_run_rev_pp": float(d.rev_short_abs.median()),
    }


results["A5_revisions"] = by_group(rv, rev_summary)
dev5 = rv[rv.group != "High income"]
obs, p = lib.perm_test_groups(dev5, "abs_rev", "is_ssa", stat=np.nanmedian)
results["A5_revisions"]["ssa_vs_otherdev_abs_median_diff"] = float(obs)
results["A5_revisions"]["perm_p_abs"] = float(p)
obs, p = lib.perm_test_groups(dev5, "revision", "is_ssa", stat=np.nanmean)
results["A5_revisions"]["ssa_vs_otherdev_mean_diff"] = float(obs)
results["A5_revisions"]["perm_p_mean"] = float(p)

# capacity + accountability correlates (country level)
crev = rv.groupby("iso3", as_index=False).agg(
    mean_rev=("revision", "mean"), med_abs=("abs_rev", "median")
)
acct = wdi.groupby("iso3", as_index=False).agg(
    va=("voice_accountability", "mean"), spi=("spi_overall", "mean")
)
crev = crev.merge(acct, on="iso3").merge(statcap, on="iso3", how="left")
results["A5_revisions"]["spearman_absrev_vs_spi"] = float(
    crev[["med_abs", "spi"]].corr(method="spearman").iloc[0, 1]
)
results["A5_revisions"]["spearman_absrev_vs_statcap"] = float(
    crev[["med_abs", "pwt_statcap"]].corr(method="spearman").iloc[0, 1]
)
results["A5_revisions"]["spearman_meanrev_vs_voice"] = float(
    crev[["mean_rev", "va"]].corr(method="spearman").iloc[0, 1]
)
crev.to_csv("results/country_revisions.csv", index=False)

# =====================================================================
# A6. History rewriting between PWT vintages (10.01 -> 11.0)
# =====================================================================
print("A6: PWT vintage rewriting ...")
a6 = panel.dropna(subset=["pwt10_growth", "pwt11_growth"]).query("year <= 2019").copy()
a6["dv"] = (a6.pwt11_growth - a6.pwt10_growth).abs()
results["A6_pwt_rewrite"] = {
    "median_abs_change_by_group": by_group(a6, lambda d: float(d.dv.median())),
    "share_gt1pp": by_group(a6, lambda d: float((d.dv > 1).mean())),
    "share_gt2pp": by_group(a6, lambda d: float((d.dv > 2).mean())),
    "n": by_group(a6, lambda d: int(len(d))),
}
a6["dv_gt1"] = (a6.dv > 1).astype(float)
dev6 = a6[a6.group != "High income"]
obs, p = lib.perm_test_groups(dev6, "dv_gt1", "is_ssa", stat=np.nanmean)
results["A6_pwt_rewrite"]["ssa_vs_otherdev_share_gt1pp_diff"] = float(obs)
results["A6_pwt_rewrite"]["perm_p_share_gt1pp"] = float(p)

# =====================================================================
# A7. Expenditure-side statistical discrepancy
# =====================================================================
print("A7: internal discrepancy ...")
a7 = panel.dropna(subset=["gdp_discrepancy_lcu", "gdp_lcu"]).query("gdp_lcu > 0").copy()
a7["disc_share"] = (a7.gdp_discrepancy_lcu / a7.gdp_lcu).abs() * 100
results["A7_discrepancy"] = {
    "coverage_share_reporting": by_group(
        panel.query(f"{YR0}<=year<={YR1}"),
        lambda d: float(d.gdp_discrepancy_lcu.notna().mean()),
    ),
    "median_disc_pct_gdp": by_group(a7, lambda d: float(d.disc_share.median())),
    "share_disc_gt2pct": by_group(a7, lambda d: float((d.disc_share > 2).mean())),
}

# =====================================================================
# A8. Aggregate story: does the SSA growth narrative survive across sources?
# =====================================================================
print("A8: aggregate story ...")
agg = {}
for col, name in [
    ("gdp_growth", "WDI"),
    ("imf_growth", "IMF WEO (current)"),
    ("pwt11_growth", "PWT 11.0"),
    ("mpd_growth", "Maddison 2023"),
]:
    d = w.dropna(subset=[col])
    agg[name] = by_group(d, lambda x, c=col: float(x[c].mean()))
results["A8_mean_growth_by_source"] = agg

# per-capita version for the 2000-2019 "Africa Rising" era
w2 = panel.query("2000 <= year <= 2019")
results["A8_africa_rising_gdppc"] = by_group(
    w2.dropna(subset=["gdppc_growth"]), lambda d: float(d.gdppc_growth.mean())
)

# SPI levels for context
spi_latest = wdi.query("year >= 2019").groupby(["iso3"], as_index=False).agg(
    spi=("spi_overall", "mean")
)
spi_latest = lib.attach_region(spi_latest)
spi_latest["group"] = lib.region_group(spi_latest)
results["A8_spi_by_group"] = by_group(spi_latest, lambda d: float(d.spi.mean()))

with open("results/results.json", "w") as f:
    json.dump(results, f, indent=2)
print("wrote results/results.json")

# persist analysis frames for figure-making
a1.to_parquet("results/a1_panel.parquet")
cmed.to_parquet("results/a1_country.parquet")
a2[["iso3", "year", "group", "gap"]].to_parquet("results/a2_panel.parquet")
cgap.to_parquet("results/a2_country.parquet")
fp.to_parquet("results/weo_first_prints.parquet")
rv[["iso3", "year", "group", "revision", "abs_rev"]].to_parquet("results/a5_revisions.parquet")
a6[["iso3", "year", "group", "dv"]].to_parquet("results/a6_pwt.parquet")
print("done")
