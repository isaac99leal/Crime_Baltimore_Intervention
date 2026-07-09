#!/usr/bin/env python3
"""Fetch IMF datamapper series and World Bank governance indicators.

Outputs: data/imf_datamapper.parquet, data/wgi.parquet
"""
import json
import time
import urllib.request

import pandas as pd


def get_json(url, retries=4):
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** (i + 1))


def imf_datamapper(code):
    js = get_json(f"https://www.imf.org/external/datamapper/api/v1/{code}")
    vals = js["values"][code]
    rows = [(iso, int(y), v) for iso, series in vals.items() for y, v in series.items()]
    df = pd.DataFrame(rows, columns=["iso3", "year", code])
    return df[df.iso3.str.len() == 3]


def wdi_indicator(code, name, source=2):
    rows, page, pages = [], 1, 1
    while page <= pages:
        url = (
            "https://api.worldbank.org/v2/country/all/indicator/"
            f"{code}?format=json&per_page=20000&page={page}&source={source}"
        )
        js = get_json(url)
        meta, data = js[0], js[1] or []
        pages = meta["pages"]
        rows += [(d["countryiso3code"], int(d["date"]), d["value"]) for d in data]
        page += 1
    df = pd.DataFrame(rows, columns=["iso3", "year", name])
    return df[df.iso3.str.len() == 3].drop_duplicates(subset=["iso3", "year"])


def main():
    g = imf_datamapper("NGDP_RPCH")
    p = imf_datamapper("PCPIPCH")
    imf = g.merge(p, on=["iso3", "year"], how="outer").sort_values(["iso3", "year"])
    imf.to_parquet("data/imf_datamapper.parquet")
    print(f"imf: {imf.shape}")

    cc = wdi_indicator("GOV_WGI_CC.EST", "control_corruption", source=3)
    ge = wdi_indicator("GOV_WGI_GE.EST", "govt_effectiveness", source=3)
    va = wdi_indicator("GOV_WGI_VA.EST", "voice_accountability", source=3)
    wgi = cc.merge(ge, on=["iso3", "year"], how="outer").merge(
        va, on=["iso3", "year"], how="outer"
    )
    wgi.to_parquet("data/wgi.parquet")
    print(f"wgi: {wgi.shape}")


if __name__ == "__main__":
    main()
