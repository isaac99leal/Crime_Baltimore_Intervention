#!/usr/bin/env python3
"""Publication figures for the growth-forensics paper.

Style follows the reference dataviz palette: fixed categorical hue order,
one job per color, recessive chrome, direct labels.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lib

# ---- palette (reference instance, light mode) ----
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
C_SSA = "#2a78d6"    # slot 1 blue  — Sub-Saharan Africa
C_DEV = "#1baf7a"    # slot 2 aqua  — other developing
C_HI = "#eda100"     # slot 3 yellow — high income (direct-labeled everywhere)
COLORS = {"Sub-Saharan Africa": C_SSA, "Other developing": C_DEV, "High income": C_HI}
GROUPS = ["Sub-Saharan Africa", "Other developing", "High income"]

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans",
    "text.color": INK,
    "axes.edgecolor": BASE,
    "axes.labelcolor": INK2,
    "axes.titlecolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.axisbelow": True,
    "font.size": 10,
})

results = json.load(open("results/results.json"))
RNG = np.random.default_rng(7)


def jitter_strip(ax, df, valcol, log=False):
    """Horizontal strip plot of country-level values by group with medians."""
    for i, g in enumerate(GROUPS):
        v = df[df.group == g][valcol].to_numpy()
        y = i + RNG.uniform(-0.17, 0.17, len(v))
        ax.scatter(v, y, s=22, color=COLORS[g], alpha=0.65, linewidths=0, zorder=3)
        med = np.median(v)
        ax.plot([med, med], [i - 0.3, i + 0.3], color=INK, lw=2, zorder=4)
        ax.annotate(
            f"median {med:.2f}", (med, i + 0.36), ha="center", fontsize=8.5,
            color=INK2, zorder=5,
        )
    ax.set_yticks(range(len(GROUPS)))
    ax.set_yticklabels(GROUPS, color=INK)
    ax.invert_yaxis()
    if log:
        ax.set_xscale("log")
    ax.grid(axis="y", visible=False)


# ================================================================= Figure 1
# Cross-source disagreement, country medians
cmed = pd.read_parquet("results/a1_country.parquet")
fig, ax = plt.subplots(figsize=(8.6, 3.6), layout="constrained")
d = cmed[cmed.median_spread > 0].copy()
jitter_strip(ax, d, "median_spread", log=True)
ax.set_xlabel("country median spread across WDI, IMF, PWT growth estimates, 1990–2019 (pp, log scale)")
ax.set_title("Same country, same year, three canonical sources: how far apart?", fontsize=11)
fig.savefig("figures/f1_cross_source_disagreement.png", dpi=200)
plt.close(fig)

# ================================================================= Figure 2
# Revisions: |final - first print| by group + scatter vs SPI
rv = pd.read_parquet("results/a5_revisions.parquet")
crev = pd.read_csv("results/country_revisions.csv")
cts = lib.load_countries()[["iso3", "region", "income"]]
crev = crev.merge(cts, on="iso3", how="inner")
crev["group"] = lib.region_group(crev)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), layout="constrained")
ax = axes[0]
grid = np.linspace(0, 6, 400)
label_q = {"Sub-Saharan Africa": 0.62, "Other developing": 0.78, "High income": 0.92}
for g in GROUPS:
    v = rv[rv.group == g].abs_rev.dropna().to_numpy()
    ecdf = [(v <= x).mean() for x in grid]
    ax.plot(grid, ecdf, color=COLORS[g], lw=2)
    q = label_q[g]
    ax.annotate(g, (np.quantile(v, q), q), fontsize=9, color=COLORS[g],
                xytext=(8, -3), textcoords="offset points", fontweight="bold")
ax.set_xlabel("|current IMF estimate − first post-year print| (pp)")
ax.set_ylabel("share of country-years")
ax.set_ylim(0, 1.02)
ax.set_title("Growth revisions, 1990–2021 (cumulative share)", fontsize=11)

ax = axes[1]
d = crev.dropna(subset=["med_abs", "spi"])
for g in GROUPS:
    s = d[d.group == g]
    ax.scatter(s.spi, s.med_abs, s=24, color=COLORS[g], alpha=0.7, linewidths=0,
               label=g)
rho = results["A5_revisions"]["spearman_absrev_vs_spi"]
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
ax.set_xlabel("Statistical Performance Indicator (country mean)")
ax.set_ylabel("median |revision| (pp)")
ax.set_title(f"Revision noise vs statistical capacity (ρ = {rho:.2f})", fontsize=11)
fig.savefig("figures/f2_revisions.png", dpi=200)
plt.close(fig)

# ================================================================= Figure 3
# Deflator - CPI gap
cgap = pd.read_parquet("results/a2_country.parquet")
fig, ax = plt.subplots(figsize=(8, 3.6), layout="constrained")
d = cgap[cgap.median_gap.abs() < 6]
jitter_strip(ax, d, "median_gap")
ax.axvline(0, color=BASE, lw=1.2, zorder=2)
ax.set_xlabel("Country median of (CPI inflation − GDP-deflator inflation), 1990–2024 (pp per year)")
ax.set_title("Right of zero: the deflator runs below CPI, flattering real growth", fontsize=11)
fig.savefig("figures/f3_deflator_gap.png", dpi=200)
plt.close(fig)

# ================================================================= Figure 4
# Distribution of first prints around zero
fp = pd.read_parquet("results/weo_first_prints.parquet")
fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=False, layout="constrained")
edges = np.arange(-6, 10.5, 0.5)
for ax, g in zip(axes, GROUPS):
    v = fp[fp.group == g].first_print.dropna()
    v = v[(v >= -6) & (v < 10)]
    counts, _ = np.histogram(v, bins=edges)
    centers = edges[:-1] + 0.25
    cols = [COLORS[g] if not (-0.5 <= c < 0) else "#e34948" for c in centers]
    ax.bar(centers, counts, width=0.46, color=cols, linewidth=0)
    ax.axvline(0, color=INK2, lw=1)
    z = results["A4_zero_discontinuity_first_prints"][g]["z_left_of_zero"]
    ax.set_title(f"{g}\n(z for bin just left of 0: {z:.1f})", fontsize=9.5)
    ax.grid(axis="x", visible=False)
axes[0].set_ylabel("country-years")
axes[1].set_xlabel("first-print real GDP growth (%), 1990–2022")
fig.suptitle("Too few 'slightly negative' years: the missing-recessions kink in first prints", fontsize=11)
fig.savefig("figures/f4_zero_discontinuity.png", dpi=200)
plt.close(fig)

# ================================================================= Figure 5
# First-decimal-digit heaping in first prints
fig, axes = plt.subplots(1, 3, figsize=(11, 3.2), sharey=True, layout="constrained")
for ax, g in zip(axes, GROUPS):
    dist = results["A3_heaping_weo_first_prints"][g]["dist"]
    n = results["A3_heaping_weo_first_prints"][g]["n"]
    cols = [COLORS[g] if d in (0, 5) else GRID for d in range(10)]
    ax.bar(range(10), dist, color=cols, width=0.7, linewidth=0)
    ax.axhline(0.1, color=INK2, lw=1, ls=(0, (4, 3)))
    ax.set_xticks(range(10))
    ax.set_title(f"{g} (n={n:,})", fontsize=9.5)
    ax.grid(axis="x", visible=False)
axes[0].set_ylabel("share of first prints")
axes[1].set_xlabel("first decimal digit of the growth rate (dashed line = uniform)")
fig.suptitle("Digit heaping at .0 and .5 is universal — not an African signature", fontsize=11)
fig.savefig("figures/f5_heaping.png", dpi=200)
plt.close(fig)

# ================================================================= Figure 6
# Benford second-digit test (null result)
fig, ax = plt.subplots(figsize=(8, 3.4), layout="constrained")
w = 0.26
for i, g in enumerate(GROUPS):
    dist = results["A3_benford2_gdp_lcu"][g]["dist"]
    ax.bar(np.arange(10) + (i - 1) * w, dist, width=w - 0.03, color=COLORS[g],
           linewidth=0, label=g)
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
ax.plot(np.arange(10), lib.BENFORD_2ND, color=INK, lw=1.6, marker="o", ms=4, zorder=5)
ax.annotate("Benford second-digit law", (6.1, lib.BENFORD_2ND[6] + 0.006),
            fontsize=9, color=INK)
ax.set_xticks(range(10))
ax.set_xlabel("second digit of nominal GDP (LCU)")
ax.set_ylabel("share")
ax.set_title("No fabrication signature: all three groups match Benford's second-digit law")
ax.grid(axis="x", visible=False)
fig.savefig("figures/f6_benford.png", dpi=200)
plt.close(fig)

# ================================================================= Figure 7
# Mean growth by source: the aggregate story survives
fig, ax = plt.subplots(figsize=(8, 3.4), layout="constrained")
src = results["A8_mean_growth_by_source"]
sources = list(src.keys())
for i, g in enumerate(GROUPS):
    y = [src[s][g] for s in sources]
    ax.scatter(range(len(sources)), y, color=COLORS[g], s=48, zorder=4)
    ax.plot(range(len(sources)), y, color=COLORS[g], lw=1.2, alpha=0.5, zorder=3)
    ax.annotate(g, (len(sources) - 1 + 0.06, y[-1]), fontsize=9, color=COLORS[g],
                va="center", fontweight="bold")
ax.set_xticks(range(len(sources)))
ax.set_xticklabels(sources, color=INK)
ax.set_xlim(-0.4, len(sources) + 1.0)
ax.set_ylabel("mean annual real GDP growth, 1990–2019 (%)")
ax.set_title("The group-level growth ranking survives across databases")
ax.grid(axis="x", visible=False)
fig.savefig("figures/f7_aggregate_story.png", dpi=200)
plt.close(fig)

print("wrote 7 figures")
