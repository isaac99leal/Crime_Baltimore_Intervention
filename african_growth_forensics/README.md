# African Growth Forensics

A forensic audit of Sub-Saharan African growth statistics using five open
databases and a symmetric battery of statistical tests. The paper is at
[`paper/paper.md`](paper/paper.md).

## Headline findings

- **Softness, not fabrication.** The three canonical growth sources disagree by
  0.48pp for the median SSA country-year (7× other developing countries); 26%
  of SSA country-years disagree by >2pp. Median ultimate revision of a first
  print: 1.25pp. Both correlate strongly with statistical capacity.
- **One real overstatement channel:** GDP deflators run persistently below CPI
  in a quarter of SSA countries (Nigeria +2.8pp/yr, Angola +3.2), mechanically
  flattering real growth.
- **Clean nulls where the strong-fabrication thesis needed hits:** Benford
  second-digit tests pass, digit heaping is worse outside Africa, revisions run
  upward not downward, and the zero-growth kink is equally present in
  high-income first prints.

## Pipeline

```
pip install pandas numpy scipy matplotlib pyarrow openpyxl

python3 fetch_wdi.py      # World Bank WDI + country metadata  -> data/
python3 fetch_other.py    # IMF datamapper + WGI               -> data/
# plus four bulk files (see below)
python3 run_analysis.py   # all tests -> results/results.json + parquets
python3 make_figures.py   # figures/*.png
```

Bulk downloads (not committed; place in `data/`):

| File | Source |
|---|---|
| `pwt110.dta` | PWT 11.0 — dataverse.nl datafile 554030 (doi:10.34894/FABVLR) |
| `pwt1001.dta` | PWT 10.01 — dataverse.nl datafile 354098 |
| `mpd2023.dta` | Maddison 2023 — dataverse.nl datafile 421303 (doi:10.34894/INZBF2) |
| `WEOhistorical.xlsx` | imf.org/external/pubs/ft/weo/data/WEOhistorical.xlsx |

## Layout

- `lib.py` — loaders, harmonization, cluster-bootstrap/permutation helpers,
  digit-forensics utilities
- `run_analysis.py` — the seven-test battery (A1–A8), writes `results/`
- `make_figures.py` — publication figures, writes `figures/`
- `paper/paper.md` — the working paper
- `results/results.json` — every statistic quoted in the paper
