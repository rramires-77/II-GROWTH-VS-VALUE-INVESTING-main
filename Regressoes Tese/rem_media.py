# -*- coding: utf-8 -*-
# Requisitos: pandas>=1.5, numpy
# Arquivos esperados:
#   - BR_data_fill.csv (colunas: Company, Year, Capital_Gain_%, DY_%, IPCA%)
#   - portugal_psi20_data_filled.csv (colunas: Company, Year, Dividend_Yield_%, Capital_Gain_%, IPC_%)

import pandas as pd
import numpy as np
from pathlib import Path

BR_PATH = "BR_data_fill.csv"
PT_PATH = "portugal_psi20_data_filled.csv"

def to_float_comma(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, str):
        x = x.replace("%", "").replace(",", ".").strip()
    return pd.to_numeric(x, errors="coerce")

def load_brazil(path):
    br = pd.read_csv(path)
    # Ajustes de tipo
    for col in ["Capital_Gain_%", "DY_%", "IPCA%"]:
        if col in br.columns:
            br[col] = pd.to_numeric(br[col], errors="coerce")
    if "Year" in br.columns:
        br["Year"] = pd.to_numeric(br["Year"], errors="coerce").astype("Int64")
    # TSR nominal e real
    br["TSR_%"] = br["DY_%"] + br["Capital_Gain_%"]
    br["TSR_real_%"] = ((1 + br["TSR_%"]/100.0) / (1 + br["IPCA%"]/100.0) - 1) * 100
    br_tidy = br[["Company", "Year", "DY_%", "Capital_Gain_%", "TSR_%", "TSR_real_%"]].copy()
    br_tidy["Country"] = "Brazil"
    return br_tidy

def load_portugal(path):
    pt = pd.read_csv(path)
    pt["Year"] = pd.to_numeric(pt["Year"], errors="coerce").astype("Int64")
    pt["Dividend_Yield_%"] = pt["Dividend_Yield_%"].apply(to_float_comma)
    pt["Capital_Gain_%"] = pd.to_numeric(pt["Capital_Gain_%"], errors="coerce")
    pt["IPC_%"] = pt["IPC_%"].apply(to_float_comma)
    # TSR nominal e real
    pt["TSR_%"] = pt["Dividend_Yield_%"] + pt["Capital_Gain_%"]
    pt["TSR_real_%"] = ((1 + pt["TSR_%"]/100.0) / (1 + pt["IPC_%"]/100.0) - 1) * 100
    pt_tidy = pt[["Company", "Year", "Dividend_Yield_%", "Capital_Gain_%", "TSR_%", "TSR_real_%"]].copy()
    pt_tidy = pt_tidy.rename(columns={"Dividend_Yield_%": "DY_%"})
    pt_tidy["Country"] = "Portugal"
    return pt_tidy

def period_label(y):
    if 2016 <= y <= 2019:
        return "2016-2019"
    if 2020 <= y <= 2024:
        return "2020-2024"
    return "out-of-scope"

def main():
    br_tidy = load_brazil(BR_PATH)
    pt_tidy = load_portugal(PT_PATH)
    df = pd.concat([br_tidy, pt_tidy], ignore_index=True)
    df = df.dropna(subset=["Year", "TSR_%"])
    # 1) Média por país
    country_mean = df.groupby("Country").agg(
        mean_TSR_pct=("TSR_%", "mean"),
        mean_TSR_real_pct=("TSR_real_%", "mean"),
        n_obs=("TSR_%", "count"),
        n_companies=("Company", pd.Series.nunique),
    ).reset_index()
    # 2) Média por ano e país
    year_country_mean = df.groupby(["Year", "Country"]).agg(
        mean_TSR_pct=("TSR_%", "mean"),
        mean_TSR_real_pct=("TSR_real_%", "mean"),
        n_obs=("TSR_%", "count"),
    ).reset_index().sort_values(["Year", "Country"])
    # 3) 2016–2019 vs 2020–2024
    df["Period"] = df["Year"].apply(period_label)
    period_country_mean = (
        df[df["Period"].isin(["2016-2019", "2020-2024"])]
        .groupby(["Period", "Country"])
        .agg(
            mean_TSR_pct=("TSR_%", "mean"),
            mean_TSR_real_pct=("TSR_real_%", "mean"),
            years=("Year", lambda s: sorted(s.unique().tolist())),
            n_obs=("TSR_%", "count"),
        )
        .reset_index()
        .sort_values(["Period", "Country"])
    )
    # Salvar
    out_dir = Path(".")
    country_mean.to_csv(out_dir / "tsr_overall_country.csv", index=False)
    year_country_mean.to_csv(out_dir / "tsr_yearly_country.csv", index=False)
    period_country_mean.to_csv(out_dir / "tsr_periods_country.csv", index=False)
    print("Arquivos salvos:")
    print(" - tsr_overall_country.csv")
    print(" - tsr_yearly_country.csv")
    print(" - tsr_periods_country.csv")

if __name__ == "__main__":
    main()
