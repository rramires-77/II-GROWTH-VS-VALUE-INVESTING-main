import pandas as pd
import os 

# -------- Ajuste o caminho se necessário --------
BASE_DIR = "/Users/zzxd/Projetos/progresso/Rogerio/artigo-2/Dados"
os.makedirs(BASE_DIR, exist_ok=True)

# -------- Anos e empresas (PSI-20 do paper) --------
years = list(range(2016, 2025))
companies = [
    "ALTRI SGPS",
    "B.COM.PORTUGUES",
    "CORTICEIRA AMORIM",
    "CTT CORREIOS PORT",
    "EDP",
    "EDP RENOVAVEIS",
    "GALP ENERGIA-NOM",
    "IBERSOL, SGPS",
    "J.MARTINS, SGPS",
    "MOTA ENGIL",
    "NOS, SGPS",
    "NOVABASE, SGPS",
    "PHAROL",
    "RAMADA",
    "REN",
    "SEMAPA",
    "SONAE",
    "THE NAVIGATOR CO."
]


# -------- Colunas do template --------
columns = [
    # Remuneração
    "Dividend_Yield_%",                 # informar em %
    "Dividend_Payout_%",                # informar em %
    "Price_Begin",                      # preço no início do ano
    "Price_End",                        # preço no fim do ano
    "Capital_Gain_%",                   # (End - Begin)/Begin * 100
    "Total_Shareholder_Return_%",       # Dividend_Yield_% + Capital_Gain_%

    # Macro (Portugal)
    "IPC_%",                            # inflação anual (INE)
    "Interest_Rate_%",                  # taxa de juro (BdP)
    "EURUSD_Change_%",                  # variação anual EUR/USD (BCE)

    # Observações
    "Notes"                             # retenção de lucros, dividendos extraordinários, etc.
]

# -------- Construção do DataFrame (MultiIndex: Empresa x Ano) --------
index = pd.MultiIndex.from_product([companies, years], names=["Company", "Year"])
df = pd.DataFrame(index=index, columns=columns)

# Tipos numéricos (exceto Notes)
for c in columns:
    if c != "Notes":
        df[c] = pd.to_numeric(df[c], errors="coerce")

# -------- Opcional: função para calcular colunas derivadas após preencher preços e DY --------
def compute_derived_cols(_df: pd.DataFrame) -> pd.DataFrame:
    """
    Após preencher Price_Begin, Price_End e Dividend_Yield_%,
    rode esta função para preencher Capital_Gain_% e Total_Shareholder_Return_%.
    """
    _df = _df.copy()
    with pd.option_context('mode.chained_assignment', None):
        _df["Capital_Gain_%"] = ((_df["Price_End"] - _df["Price_Begin"]) / _df["Price_Begin"]) * 100
        _df["Total_Shareholder_Return_%"] = _df["Dividend_Yield_%"] + _df["Capital_Gain_%"]
    return _df

# -------- Salvar arquivos --------
excel_path = os.path.join(BASE_DIR, "portugal_psi20_data_template.xlsx")
csv_path   = os.path.join(BASE_DIR, "portugal_psi20_data_template.csv")

df.to_excel(excel_path, merge_cells=False)
df.to_csv(csv_path, index=True)

# ---------------------------
# Uso sugerido após preencher:
# df_filled = pd.read_excel(excel_path, index_col=[0,1])  # ou ler o CSV
# df_filled = compute_derived_cols(df_filled)
# df_filled.to_excel(os.path.join(BASE_DIR, "portugal_psi20_data_filled.xlsx"))
# ---------------------------
