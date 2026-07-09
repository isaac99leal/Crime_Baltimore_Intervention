#!/usr/bin/env python3
"""Fetch World Bank WDI indicators + country metadata into data/wdi.parquet.

All series are pulled for all countries via the public API (v2, JSON).
Run from african_growth_forensics/.
"""
import json
import time
import urllib.request

import pandas as pd

INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth",          # real GDP growth, %
    "NY.GDP.PCAP.KD.ZG": "gdppc_growth",        # real GDP per-capita growth, %
    "NY.GDP.MKTP.CN": "gdp_lcu",                # nominal GDP, current LCU
    "NY.GDP.MKTP.KN": "gdp_klcu",               # real GDP, constant LCU
    "NY.GDP.DEFL.KD.ZG": "deflator_growth",     # GDP deflator inflation, %
    "FP.CPI.TOTL.ZG": "cpi_inflation",          # CPI inflation, %
    "SP.POP.TOTL": "population",
    "IQ.SPI.OVRL": "spi_overall",               # Statistical Performance Indicators
    # (IQ.SCI.OVRL was archived by the WB API; PWT 10.01 carries `statcap` instead)
    "NY.GDP.DISC.CN": "gdp_discrepancy_lcu",    # expenditure-side discrepancy
    "NE.CON.PRVT.CN": "cons_priv_lcu",
    "NV.AGR.TOTL.KD.ZG": "agri_growth",         # agriculture value-added growth
}

BASE = "https://api.worldbank.org/v2"


def get_json(url, retries=4):
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 ** (i + 1))


def fetch_indicator(code):
    rows = []
    page, pages = 1, 1
    while page <= pages:
        url = f"{BASE}/country/all/indicator/{code}?format=json&per_page=20000&page={page}"
        js = get_json(url)
        meta, data = js[0], js[1] or []
        pages = meta["pages"]
        for d in data:
            rows.append(
                (d["countryiso3code"], d["country"]["value"], int(d["date"]), d["value"])
            )
        page += 1
    df = pd.DataFrame(rows, columns=["iso3", "country", "year", INDICATORS[code]])
    return df[df.iso3.str.len() == 3]


def fetch_countries():
    js = get_json(f"{BASE}/country?format=json&per_page=400")
    rows = []
    for c in js[1]:
        rows.append(
            {
                "iso3": c["id"],
                "name": c["name"],
                "region": c["region"]["value"].strip(),
                "region_id": c["region"]["id"],
                "income": c["incomeLevel"]["value"],
                "income_id": c["incomeLevel"]["id"],
            }
        )
    df = pd.DataFrame(rows)
    return df[df.region_id != "NA"]  # drop aggregates


def main():
    countries = fetch_countries()
    countries.to_parquet("data/countries.parquet")
    print(f"countries: {len(countries)}")

    merged = None
    for code, name in INDICATORS.items():
        df = fetch_indicator(code)
        print(f"{code} -> {name}: {len(df)} rows")
        df = df.drop(columns=["country"]).drop_duplicates(subset=["iso3", "year"])
        merged = df if merged is None else merged.merge(df, on=["iso3", "year"], how="outer")

    merged = merged.merge(countries[["iso3", "region", "income"]], on="iso3", how="inner")
    merged = merged.sort_values(["iso3", "year"]).reset_index(drop=True)
    merged.to_parquet("data/wdi.parquet")
    print(f"wdi panel: {merged.shape}, years {merged.year.min()}-{merged.year.max()}")


if __name__ == "__main__":
    main()
