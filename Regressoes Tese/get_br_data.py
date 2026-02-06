import re
import time
from collections import defaultdict

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"
    )
}

ANOS = list(range(2016, 2025))  # 2016..2024


def _ptbr_to_float(s: str) -> float:
    # "1.234,56" -> 1234.56
    s = s.strip().replace("\xa0", " ")
    s = s.replace(".", "").replace(",", ".")
    num = re.sub(r"[^0-9.\-]", "", s)
    return float(num) if num else 0.0


def _is_div_or_jcp(texto: str) -> bool:
    """Detecta linhas de Dividendos ou JCP."""
    t = texto.strip().lower()
    return (
        "DIVIDENDO" in t              # "Dividendo", "Dividendos"
        or "JRS CAP PROPRIO" in t           # "Juros sobre Capital Próprio"
    )


def get_proventos_por_ano_fundamentus(ticker: str) -> tuple[str, dict]:
    """
    Lê proventos do Fundamentus (tipo=1, 'todos'), filtra Dividendos/JCP,
    soma por ano e retorna (empresa, {ano: total}).
    """
    url = f"https://www.fundamentus.com.br/proventos.php?papel={ticker}&tipo=1"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Empresa no cabeçalho (se existir)
    empresa = ticker
    h = soup.find(["h1", "h2"])
    if h and "-" in h.get_text():
        partes = [p.strip() for p in h.get_text().split("-")]
        if len(partes) >= 2:
            empresa = partes[-1] or ticker

    # Localiza tabela que tenha cabeçalhos Data / Valor / Tipo
    tabela = None
    for tb in soup.find_all("table"):
        ths = [th.get_text(strip=True).lower() for th in tb.find_all("th")]
        if ("data" in " ".join(ths)) and ("valor" in " ".join(ths)):
            tabela = tb
            break
    if not tabela:
        return empresa, {}

    por_ano = defaultdict(float)
    for tr in tabela.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        data_txt = tds[0].get_text(strip=True)  # dd/mm/aaaa
        valor_txt = tds[1].get_text(strip=True)
        tipo_txt = tds[2].get_text(strip=True)

        if not _is_div_or_jcp(tipo_txt):
            continue

        m = re.search(r"(\d{4})", data_txt)
        if not m:
            continue
        ano = int(m.group(1))
        if ano not in ANOS:
            continue

        try:
            val = _ptbr_to_float(valor_txt)
        except Exception:
            val = 0.0
        por_ano[ano] += val

    # Garante anos ausentes como zero (série completa)
    for ano in ANOS:
        por_ano[ano] = por_ano.get(ano, 0.0)

    return empresa, dict(por_ano)


def preco_ano_yf(ticker: str, ano: int, metodo: str = "ultimo"):
    """
    Retorna preço anual via yfinance:
      - metodo='ultimo': fechamento do último pregão do ano
      - metodo='media': média dos fechamentos do ano
    """
    tk = yf.Ticker(f"{ticker}.SA")
    # pega até poucos dias do ano seguinte para garantir último pregão
    df = tk.history(start=f"{ano}-01-01", end=f"{ano+1}-01-05", interval="1d", auto_adjust=False)
    if df.empty:
        return None
    close = df["Close"].dropna()
    if close.empty:
        return None

    if metodo == "media":
        return float(close.mean())

    # default: último pregão do ano
    return float(close.iloc[-1])


def calcular_dy_2016_2024(ticker: str, metodo_preco: str = "ultimo"):
    """
    Monta linhas para 2016..2024 com Empresa, Ticker, Ano, Dividendos_Ano, Preco_Ano, DY_%.
    """
    empresa, divs_por_ano = get_proventos_por_ano_fundamentus(ticker)
    linhas = []
    for ano in ANOS:
        total_div = float(divs_por_ano.get(ano, 0.0))
        preco = preco_ano_yf(ticker, ano, metodo=metodo_preco)
        if not preco or preco <= 0:
            # sem preço (papel pode não existir no ano)
            continue
        dy = (total_div / preco) * 100.0
        linhas.append(
            {
                "Empresa": empresa,
                "Ticker": ticker,
                "Ano": ano,
                "Dividendos_Ano": round(total_div, 4),
                "Preco_Ano": round(preco, 4),
                "DY_%": round(dy, 2),
            }
        )
    return linhas


if __name__ == "__main__":
    # Liste aqui os tickers desejados
    tickers = [
        "VALE3","PETR4","ITUB4","PETR3","BBDC4","BBAS3","ELET3","B3SA3","ABEV3","WEGE3",
        "ITSA4","RENT3","PRIO3","SUZB3","BPAC11","EQTL3","RADL3","RDOR3","RAIL3","GGBR4",
        "VBBR3","JBSS3","UGPA3","BBSE3","SBSP3"
    ]

    todas = []
    for tk in tickers:
        try:
            linhas = calcular_dy_2016_2024(tk, metodo_preco="ultimo")  # troque para "media" se preferir
            todas.extend(linhas)
            time.sleep(0.7)  
        except Exception as e:
            print(f"[ERRO] {tk}: {e}")

    df = pd.DataFrame(todas).sort_values(["Empresa", "Ano"])
    print(df.to_string(index=False))
    df.to_csv("dy_2016_2024.csv", index=False, encoding="utf-8")
    print("\nOK -> dy_2016_2024.csv gerado.")
