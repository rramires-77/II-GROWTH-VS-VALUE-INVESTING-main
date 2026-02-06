import re
import argparse
import pandas as pd

# ======= COLE O TEXTO AQUI SE QUISER USAR EMBUTIDO =========
RAW_OCR_TEXT = r"""
D.Yield/ano 2016 2017 2018 2019 2020 2021 2022 Média
VALE 0,65% 3.29% 3,86% 265% 275% 18,77% 8,53% 5,79%
PETROBRAS 0,00% 000% 397% 3,11% 000% 19.87% 68,32% 13,61%
ITAUUNIBANCO 4.72% 3.52% 60% 7,56% 4.12% 433% 4,08% 4,90%
PETROBRAS 0,00% 000% 098% 1,56% 0.83% 18.41% 59,70% 11,64%
BRADESCO 4,56% 366% 296% 5,54% 256% 5,30% 2,76% 3,90%
BRASIL 325% 297% 326% 483% 381% 7,85% 11,99% 5,42%
ELETROBRAS 0,00% 000% 000% 219% 442% 7,14% 1,75% 2,21%
B3 305% 199% 260% 1,89% 3.14% 10,00% 3,57% 3,75%
AMBEV S/A 3,90% 254% 3,58% 263% 264% 441% 5,25% 3,56%
WEG 243% 148% 180% 0,98% 1,34% 1,41%
ITAUSA 6.99% 439% 736% 845% 6,84% 6,25%
LOCALIZA 261% 1,12% 091% 0,83% 248% 1,33%
PETRORIO 0,00% 000% 000% 0,00% 0,00% 0,00%
SUZANO S.A. 000% 000% 0,50% 1,12% 6.49% 1,16%
BTGP BANCO 000% 000% 5.77% 1,85% 2,74% 1,93%
EQUATORIAL 1,71% 0,88% 162% 0,83% 2,37% 1,71%
RAIADROGASIL 0.97% 067% 111% 0,57% 1,07% 0,83%
REDE D OR 0,00% 000% 000% 0,00% 1,37% 0,66%
RUMO S.A. 0,00% 000% 000% 0,00% 0,10% 0,01%
GERDAU 046% 040% 256% 140% 12,36% 4,25%
VIBRA 0,00% 000% 5,54% 8,73% 420% 946% 5,51% 4,78%
JBS 3,56% 034% 040% 001% 228% 7,95% 9,10% 3,38%
ULTRAPAR 234% 229% 274% 216% 101% 440% 4,62% 2,80%
BBSEGURIDADE 5,89% 5,75% 11,22% 419% 939% 480% 5,82% 6,72%
SABESP 0,76% 3,51% 3.27% 1,91% 3,10% 0,99% 1,65% 217%
""".strip()
# ===========================================================

YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022]
EXTRA_YEARS = [2023, 2024]  # anos extras a adicionar no formato long

def normalize_percent_token(tok: str):
    """
    Converte tokens tipo '3,86%', '265%', '000%', '3.29%', '60%' em float (ex.: 3.86, 2.65, 0.0, 3.29, 6.0)
    Regras:
     - troca vírgula por ponto, remove '%'
     - se tem ponto, tenta converter direto
     - se só dígitos:
         len>=3  -> divide por 100 (265 -> 2.65)
         len==2  -> divide por 10  (60  -> 6.0)
         len==1  -> valor direto    (0   -> 0.0)
    """
    tok = tok.strip().replace('%', '').replace(',', '.')
    # mantém apenas dígitos e ponto (um)
    parts = re.findall(r'\d+|\.', tok)
    if not parts:
        return None
    s = ''.join(parts)

    if '.' in s and s != '.':
        try:
            return float(s)
        except ValueError:
            pass

    digits = re.sub(r'\D', '', s)
    if digits == '':
        return None
    d_noz = digits.lstrip('0') or '0'
    n = len(d_noz)
    val = int(d_noz)
    if n >= 3:
        return val / 100.0
    elif n == 2:
        return val / 10.0
    else:
        return float(val)

def parse_raw_text(raw_text: str):
    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith('d.yield/ano'):
            continue

        # encontra tokens percentuais
        percs = re.findall(r'[\d.,]+%|[0-9]{1,3}%|[0-9]{1,3}[.,][0-9]{1,2}%', line)
        if not percs:
            continue

        first_idx = line.find(percs[0])
        company = line[:first_idx].strip()
        company = re.sub(r'\s{2,}', ' ', company)

        values = [normalize_percent_token(p) for p in percs]
        # mapeia os 7 primeiros para 2016..2022; 8º (se existir) é Média
        values = values[:len(YEARS) + 1]
        if len(values) < len(YEARS):
            values += [None] * (len(YEARS) - len(values))

        data = {'Empresa': company}
        for i, y in enumerate(YEARS):
            data[str(y)] = values[i] if i < len(values) else None
        if len(values) > len(YEARS):
            data['Media'] = values[len(YEARS)]
        rows.append(data)

    wide_df = pd.DataFrame(rows)
    # ordena e organiza colunas
    ordered_cols = ['Empresa'] + [str(y) for y in YEARS] + (['Media'] if 'Media' in wide_df.columns else [])
    wide_df = wide_df[ordered_cols].sort_values('Empresa').reset_index(drop=True)
    return wide_df

def to_long_with_extra_years(wide_df: pd.DataFrame, extra_years=None):
    if extra_years is None:
        extra_years = []
    long_df = wide_df.melt(
        id_vars=['Empresa'],
        value_vars=[str(y) for y in YEARS],
        var_name='Ano',
        value_name='DY_%'
    )
    long_df['Ano'] = long_df['Ano'].astype(int)

    # adiciona 2023 e 2024 vazios para cada empresa
    extras = []
    for emp in wide_df['Empresa'].unique():
        for y in extra_years:
            extras.append({'Empresa': emp, 'Ano': y, 'DY_%': None})
    if extras:
        long_df = pd.concat([long_df, pd.DataFrame(extras)], ignore_index=True)

    long_df = long_df.sort_values(['Empresa', 'Ano']).reset_index(drop=True)
    return long_df

def main():
    ap = argparse.ArgumentParser(description="Gera planilha de DY a partir de texto OCR e adiciona anos 2023 e 2024.")
    ap.add_argument('--txt', help='Caminho de um arquivo .txt com o conteúdo OCR (opcional).')
    ap.add_argument('--out-prefix', default='dy_ocr', help='Prefixo dos arquivos de saída (CSV/XLSX).')
    args = ap.parse_args()

    if args.txt:
        with open(args.txt, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    else:
        raw_text = RAW_OCR_TEXT

    wide_df = parse_raw_text(raw_text)
    long_df = to_long_with_extra_years(wide_df, extra_years=EXTRA_YEARS)

    # salva arquivos
    csv_wide = f'{args.out_prefix}_wide.csv'
    csv_long = f'{args.out_prefix}_long.csv'
    xlsx = f'{args.out_prefix}.xlsx'

    wide_df.to_csv(csv_wide, index=False, encoding='utf-8')
    long_df.to_csv(csv_long, index=False, encoding='utf-8')

    with pd.ExcelWriter(xlsx, engine='xlsxwriter') as writer:
        wide_df.to_excel(writer, sheet_name='wide', index=False)
        long_df.to_excel(writer, sheet_name='long', index=False)

    print(f'OK -> {csv_wide}')
    print(f'OK -> {csv_long}')
    print(f'OK -> {xlsx}')

if __name__ == '__main__':
    main()
