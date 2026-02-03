import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Função para limpar nome da aba no Excel
def limpar_nome_aba(nome):
    nome_limpo = re.sub(r'[\\/*?:\[\]]', '', nome)
    return nome_limpo[:31]

# Função para obter Dividend Yield anual (2016–2024)
def obter_dividend_yield(slug):
    url = f"https://companiesmarketcap.com/{slug}/dividend-yield/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    tabela = soup.find("table")
    if not tabela:
        print(f"❌ Tabela não encontrada para {slug}")
        return None
    
    dados = []
    for row in tabela.find_all("tr")[1:]:
        cols = row.find_all("td")
        raw = cols[0].text.strip()
        if not raw[:4].isdigit():
            continue  # ignora se não começa com ano
        try:
            ano = int(raw[:4])
            valor_raw = cols[1].text.strip().replace('%', '').replace(',', '.')
            valor_float = float(valor_raw) / 100  # converter para decimal
            dados.append({"Ano": ano, "Dividend Yield": valor_float})
        except:
            continue
    return pd.DataFrame(dados)

# Slugs usados na URL do site CompaniesMarketCap
empresas_slugs = {
    "AMBEV S/A ON": "ambev",
    "B3 ON": "b3",
    "BRASIL ON": "banco-do-brasil",
    "BRADESCO PN": "bradesco",
    "BBSEGURIDADE ON": "bb-seguridade",
    "BTGP BANCO UNT": "btg-pactual",
    "ELETROBRAS ON": "eletrobras",
    "EQUATORIAL ON": "equatorial",
    "GERDAU PN": "gerdau",
    "ITAUSA PN": "itausa",
    "ITAUUNIBANCO PN": "itau-unibanco",
    "JBS ON": "jbs",
    "PETROBRAS ON": "petrobras",
    "PETRORIO ON": "prio",
    "RAIADROGASIL ON": "raiadrogasil",
    "RUMO S.A. ON": "rumo",
    "REDE D OR ON": "rede-dor",
    "LOCALIZA ON": "localiza",
    "SABESP ON": "sabesp",
    "SUZANO S.A. ON": "suzano",
    "ULTRAPAR ON": "ultrapar",
    "VALE ON": "vale",
    "VIBRA ON": "vibra",
    "WEG ON": "weg"
}

# Cria o arquivo Excel
writer = pd.ExcelWriter("dividend_yield_2016_2024.xlsx", engine="openpyxl")

# Coleta de dados para todas as empresas
for nome, slug in empresas_slugs.items():
    print(f"🔍 Coletando DY de {nome}...")
    df = obter_dividend_yield(slug)
    if df is not None:
        df = df[df["Ano"].between(2016, 2024)]
        aba = limpar_nome_aba(nome)
        df.to_excel(writer, sheet_name=aba, index=False)
    else:
        print(f"⚠️ Sem dados para {nome}")

# Salva o Excel
writer.close()
print("✅ Arquivo 'dividend_yield_2016_2024.xlsx' criado com sucesso.")
