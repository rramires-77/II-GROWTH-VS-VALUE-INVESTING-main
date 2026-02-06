import pandas as pd
import yfinance as yf
from itertools import product

# ======= CONFIG =======
START_YEAR = 2016
END_YEAR = 2024

# Mapeie "Nome da Empresa" -> "ticker .SA" (IBOV > 1%)
TICKERS_BR = {
    "VALE": "VALE3.SA",
    "PETROBRAS PN": "PETR4.SA",
    "ITAUUNIBANCO": "ITUB4.SA",
    "PETROBRAS ON": "PETR3.SA",
    "BRADESCO PN": "BBDC4.SA",
    "BANCO DO BRASIL": "BBAS3.SA",
    "ELETROBRAS ON": "ELET3.SA",
    "B3": "B3SA3.SA",
    "AMBEV": "ABEV3.SA",
    "WEG": "WEGE3.SA",
    "ITAUSA": "ITSA4.SA",
    "LOCALIZA": "RENT3.SA",
    "PETRORIO": "PRIO3.SA",
    "SUZANO": "SUZB3.SA",
    "BTG PACTUAL": "BPAC11.SA",
    "EQUATORIAL": "EQTL3.SA",
    "RAIADROGASIL": "RADL3.SA",
    "REDE D'OR": "RDOR3.SA",
    "RUMO": "RAIL3.SA",
    "GERDAU PN": "GGBR4.SA",
    "VIBRA": "VBBR3.SA",
    "JBS": "JBSS3.SA",
    "ULTRAPAR": "UGPA3.SA",
    "BBSEGURIDADE": "BBSE3.SA",
    "SABESP": "SBSP3.SA",
}

OUT_CSV = "br_annual_prices_2016_2024.csv"
# ======================

def fetch_daily_all(ticker_map, start_year, end_year):
    start = f"{start_year}-01-01"
    end = f"{end_year}-12-31"
    data = yf.download(
        tickers=list(ticker_map.values()),
        start=start,
        end=end,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,   # igual ao seu: usamos Open/Close "crus"
        progress=False,
        threads=True,
    )
    return data

def annual_open_close_from_daily(data, company, ticker):
    """
    Extrai, para um ticker, o primeiro Open e o último Close de cada ano.
    Suporta retorno com MultiIndex (vários tickers simultâneos) e single-index.
    """
    try:
        if isinstance(data.columns, pd.MultiIndex):
            df_t = data.xs(ticker, level=0, axis=1).copy()
        else:
            # quando só há um ticker retornado, as colunas não são MultiIndex
            df_t = data.copy()
    except KeyError:
        return pd.DataFrame(columns=["Company", "Year", "Price_Begin", "Price_End"])

    if df_t.empty:
        return pd.DataFrame(columns=["Company", "Year", "Price_Begin", "Price_End"])

    df_t = df_t.reset_index().rename(columns={"Date": "date"})
    # yfinance retorna 'Date' já como datetime; garantimos:
    df_t["date"] = pd.to_datetime(df_t["date"])
    df_t["Year"] = df_t["date"].dt.year

    # Primeiro pregão (Open) e último pregão (Close) por ano
    df_t = df_t.sort_values(["Year", "date"])
    first_by_year = (
        df_t.groupby("Year", as_index=False)
            .first()[["Year", "Open"]]
            .rename(columns={"Open": "Price_Begin"})
    )
    last_by_year = (
        df_t.groupby("Year", as_index=False)
            .last()[["Year", "Close"]]
            .rename(columns={"Close": "Price_End"})
    )

    annual = pd.merge(first_by_year, last_by_year, on="Year", how="outer")
    annual["Company"] = company

    # restringe ao intervalo de anos desejado
    annual = annual[(annual["Year"] >= START_YEAR) & (annual["Year"] <= END_YEAR)]
    return annual[["Company", "Year", "Price_Begin", "Price_End"]]

def main():
    # baixa todos os diários de uma vez
    daily = fetch_daily_all(TICKERS_BR, START_YEAR, END_YEAR)

    # grade completa Company x Year para garantir linhas mesmo sem dado
    companies = list(TICKERS_BR.keys())
    years = list(range(START_YEAR, END_YEAR + 1))
    base = pd.DataFrame(product(companies, years), columns=["Company", "Year"])

    # calcula open/close por empresa
    pieces = []
    for company, ticker in TICKERS_BR.items():
        pieces.append(annual_open_close_from_daily(daily, company, ticker))
    if pieces:
        annual_all = pd.concat(pieces, ignore_index=True)
    else:
        annual_all = pd.DataFrame(columns=["Company", "Year", "Price_Begin", "Price_End"])

    # left-join na grade completa para manter todas as combinações
    out = base.merge(annual_all, on=["Company", "Year"], how="left")

    # Capital_Gain_% (retorno dentro do ano: abertura → fechamento)
    out["Capital_Gain_%"] = ((out["Price_End"] - out["Price_Begin"]) / out["Price_Begin"]) * 100

    # ordena e salva
    out = out.sort_values(["Company", "Year"]).reset_index(drop=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}")
    print(out.head(20))

if __name__ == "__main__":
    main()
