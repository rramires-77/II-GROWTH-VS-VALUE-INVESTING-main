# -*- coding: utf-8 -*-
# Requer: pandas, numpy, scipy, statsmodels
import pandas as pd, numpy as np
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

BR = pd.read_csv("BR_data_fill.csv")
PT = pd.read_csv("portugal_psi20_data_filled.csv")

# 1) limpeza de nomes / números
def clean_cols(df):
    df = df.rename(columns=lambda c: c.strip().replace(" ", "_").replace("%","pct").replace(".","").replace("/","_"))
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(",", ".", regex=False)
            df[c] = pd.to_numeric(df[c], errors="ignore")
    return df

BR, PT = clean_cols(BR), clean_cols(PT)

# 2) padronizar campos
BR = BR.rename(columns={"DY_pct":"Dividend_Yield_pct", "IPCApct":"Inflation_pct"})
PT = PT.rename(columns={"IPC_pct":"Inflation_pct"})
for df in (BR, PT):
    df["Country"] = "BR" if df is BR else "PT"
    df["Period"] = np.where(df["Year"]<=2019, "Pre", "Post")

# 3) propagar inflação por ano (caso haja NaN linha-a-linha)
def spread_inflation(df):
    m = df[["Year","Inflation_pct"]].dropna().drop_duplicates("Year").set_index("Year")["Inflation_pct"]
    df["Inflation_pct"] = df["Year"].map(m)
    return df

BR, PT = spread_inflation(BR), spread_inflation(PT)

# 4) métricas reais e TSR
for df in (BR, PT):
    df["Real_CapGain_pct"] = pd.to_numeric(df["Capital_Gain_pct"], errors="coerce") - pd.to_numeric(df["Inflation_pct"], errors="coerce")
    df["TSR_pct"] = pd.to_numeric(df["Dividend_Yield_pct"], errors="coerce") + pd.to_numeric(df["Capital_Gain_pct"], errors="coerce")
    df["Real_TSR_pct"] = pd.to_numeric(df["Dividend_Yield_pct"], errors="coerce") + df["Real_CapGain_pct"]

ALL = pd.concat([BR, PT], ignore_index=True)

# ---------- TESTES 1 e 2 ----------
def run_pair_tests(df, d_expr, label):
    d = df.eval(d_expr).dropna()
    # normalidade simples (amostra grande -> central limit ajuda; usamos ambos)
    t = stats.ttest_1samp(d, popmean=0.0, nan_policy="omit")
    w = stats.wilcoxon(d) if len(d)>0 else (np.nan,np.nan)
    cohen_d = d.mean()/d.std(ddof=1) if d.std(ddof=1)>0 else np.nan
    return {"label": label, "n": len(d), "mean": d.mean(), "t_p": t.pvalue, "wilcoxon_p": (w.pvalue if hasattr(w,"pvalue") else np.nan), "cohen_d": cohen_d}

# BR: H1/H1A
BR_pre  = BR.query("Period=='Pre'")
BR_post = BR.query("Period=='Post'")
res_H1   = run_pair_tests(BR,       "Real_CapGain_pct - Dividend_Yield_pct", "BR 2016–2024")
res_H1pre= run_pair_tests(BR_pre,   "Real_CapGain_pct - Dividend_Yield_pct", "BR Pré")
res_H1pos= run_pair_tests(BR_post,  "Real_CapGain_pct - Dividend_Yield_pct", "BR Pós")

# PT: H2/H2A
PT_pre  = PT.query("Period=='Pre'")
PT_post = PT.query("Period=='Post'")
res_H2   = run_pair_tests(PT,       "Dividend_Yield_pct - Capital_Gain_pct", "PT 2016–2024")
res_H2pre= run_pair_tests(PT_pre,   "Dividend_Yield_pct - Capital_Gain_pct", "PT Pré")
res_H2pos= run_pair_tests(PT_post,  "Dividend_Yield_pct - Capital_Gain_pct", "PT Pós")

print("H1/H1A:", res_H1, res_H1pre, res_H1pos)
print("H2/H2A:", res_H2, res_H2pre, res_H2pos)

# ---------- TESTE 3: DiD sobre shares robustas ----------
def safe_shares(df):
    dy = pd.to_numeric(df["Dividend_Yield_pct"], errors="coerce")
    cg = pd.to_numeric(df["Capital_Gain_pct"], errors="coerce")
    denom = np.abs(dy) + np.abs(cg)
    out = df.copy()
    out["S_cap"] = np.where(denom>0, np.abs(cg)/denom, np.nan)
    out["S_div"] = np.where(denom>0, 1 - out["S_cap"], np.nan)
    out["Post"] = (out["Period"]=="Post").astype(int)
    out["BR"] = (out["Country"]=="BR").astype(int)
    return out.dropna(subset=["S_cap","Post","BR"])

ALL_sh = safe_shares(ALL)
model = smf.ols("S_cap ~ BR + Post + BR:Post", data=ALL_sh).fit(cov_type="HC3")
print(model.summary())

# ---------- TESTE 4: Painel (FE de firma, cluster por ano) ----------
# 1) Garantir a existência e tipo numérico das colunas usadas
for c in ("Real_CapGain_pct","Inflation_pct","SELIC","Interest_Rate_pct","REAL_USD","EURUSD_Change_pct"):
    if c not in ALL.columns:
        ALL[c] = np.nan
    ALL[c] = pd.to_numeric(ALL[c], errors="coerce")

ALL["Post"] = (ALL["Period"]=="Post").astype(int)
ALL["Country"] = ALL["Country"].astype("category")
ALL["Firm"] = (ALL["Country"].astype(str) + "|" + ALL["Company"].astype(str)).astype("category")
ALL["Year"] = pd.to_numeric(ALL["Year"], errors="coerce")

# 2) Monte um dataframe APENAS com as colunas da fórmula + Year para cluster
fe_cols = ["Real_CapGain_pct", "Inflation_pct", "Post", "Country", "Firm", "Year"]
df_fe = ALL[fe_cols].copy()

# 3) Remova linhas com NA nas colunas relevantes (isso define as observações do modelo)
df_fe = df_fe.dropna(subset=["Real_CapGain_pct", "Inflation_pct", "Post", "Country", "Firm", "Year"]).copy()

# 4) Garanta tipos corretos (category/numéricos) DEPOIS do dropna
df_fe["Country"] = df_fe["Country"].astype("category")
df_fe["Firm"] = df_fe["Firm"].astype("category")
df_fe["Post"] = pd.to_numeric(df_fe["Post"], errors="coerce")
df_fe["Inflation_pct"] = pd.to_numeric(df_fe["Inflation_pct"], errors="coerce")
df_fe["Real_CapGain_pct"] = pd.to_numeric(df_fe["Real_CapGain_pct"], errors="coerce")
df_fe["Year_grp"] = df_fe["Year"].astype(int)  # grupos de cluster alinhados linha a linha

# 5) Ajuste o modelo com FE de firma (C(Firm)) e cluster por ano
fe_formula = "Real_CapGain_pct ~ Inflation_pct + Post + C(Country) + C(Firm)"
fe = smf.ols(fe_formula, data=df_fe).fit(cov_type="cluster", cov_kwds={"groups": df_fe["Year_grp"]})

print(fe.summary())

