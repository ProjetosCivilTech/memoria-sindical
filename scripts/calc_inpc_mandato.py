"""
Gera site/data/inpc_mandato.json cruzando:
  - INPC acumulado por mandato (IBGE/SIDRA Tabela 1736)
  - Reajuste acumulado dos Correios (financeiro.json)

Uso:
    python scripts/gerar_inpc_mandato.py
    python scripts/gerar_inpc_mandato.py --xlsx "dados/Tabela 1736.xlsx"
"""
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("Rode: pip install pandas openpyxl")
    sys.exit(1)


RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
SITE_DATA = RAIZ / "site" / "data"
XLSX_DEFAULT = RAIZ / "dados" / "Tabela 1736.xlsx"
FINANCEIRO = SITE_DATA / "financeiro.json"
SAIDA = SITE_DATA / "inpc_mandato.json"


MANDATOS = [
    {"nome": "FHC 1",            "ini": 1995, "fim": 1998, "orientacao": "conservador"},
    {"nome": "FHC 2",            "ini": 1999, "fim": 2002, "orientacao": "conservador"},
    {"nome": "Lula 1",           "ini": 2003, "fim": 2006, "orientacao": "progressista"},
    {"nome": "Lula 2",           "ini": 2007, "fim": 2010, "orientacao": "progressista"},
    {"nome": "Dilma 1",          "ini": 2011, "fim": 2014, "orientacao": "progressista"},
    {"nome": "Dilma 2 / Temer",  "ini": 2015, "fim": 2018, "orientacao": "misto"},
    {"nome": "Bolsonaro",        "ini": 2019, "fim": 2022, "orientacao": "conservador"},
    {"nome": "Lula 3",           "ini": 2023, "fim": 2026, "orientacao": "progressista"},
]


def parse_valor(v):
    """Converte '1,44' ou '1.44' em float."""
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def ler_inpc_mensal(xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx, sheet_name="Tabela", header=None)

    # Encontra linha de meses
    linha_meses = None
    for i, row in df.iterrows():
        vals = [str(v).lower() for v in row if pd.notna(v)]
        if any("janeiro 1995" in v for v in vals):
            linha_meses = i
            break

    if linha_meses is None:
        raise ValueError("Linha 'janeiro 1995' não encontrada na planilha")

    meses = df.iloc[linha_meses].values
    valores = df.iloc[linha_meses + 1].values

    dados = []
    for mes, valor in zip(meses, valores):
        if pd.isna(mes):
            continue
        partes = str(mes).strip().split()
        if len(partes) != 2:
            continue
        nome_mes, ano = partes
        try:
            ano_int = int(ano)
        except ValueError:
            continue
        v = parse_valor(valor)
        if v is None:
            continue
        dados.append({"ano": ano_int, "mes": nome_mes, "valor": v})

    return pd.DataFrame(dados)


def inpc_acumulado(df_mensal: pd.DataFrame, ini: int, fim: int) -> tuple:
    """Retorna (valor_pct, qtd_meses)."""
    sub = df_mensal[(df_mensal["ano"] >= ini) & (df_mensal["ano"] <= fim)]
    if sub.empty:
        return None, 0
    fator = (1 + sub["valor"] / 100).prod()
    return round((fator - 1) * 100, 2), len(sub)


def reajuste_acumulado(financeiro: dict, ini: int, fim: int) -> tuple:
    """Compõe reajustes do financeiro.json no período. Retorna (valor_pct, qtd_anos)."""
    serie = financeiro.get("serie_temporal", [])
    fator = 1.0
    anos = 0
    for s in serie:
        if ini <= s["ano"] <= fim:
            r = s.get("reajuste_pct")
            if r is not None and r > 0:
                fator *= (1 + r / 100)
                anos += 1
    if anos == 0:
        return 0.0, 0
    return round((fator - 1) * 100, 2), anos


def main():
    xlsx = XLSX_DEFAULT
    if "--xlsx" in sys.argv:
        idx = sys.argv.index("--xlsx")
        if idx + 1 < len(sys.argv):
            xlsx = Path(sys.argv[idx + 1])

    if not xlsx.exists():
        print(f"[ERRO] Planilha não encontrada: {xlsx}")
        return

    if not FINANCEIRO.exists():
        print(f"[ERRO] financeiro.json não encontrado. Rode gerar_financeiro_real.py antes.")
        return

    print(f"[1/3] Lendo planilha: {xlsx.name}")
    df_mensal = ler_inpc_mensal(xlsx)
    print(f"      {len(df_mensal)} meses lidos ({df_mensal['ano'].min()}-{df_mensal['ano'].max()})")

    print(f"[2/3] Lendo financeiro.json")
    financeiro = json.loads(FINANCEIRO.read_text(encoding="utf-8"))

    print(f"[3/3] Calculando por mandato...")
    resultado = []
    for m in MANDATOS:
        inpc, qtd_meses = inpc_acumulado(df_mensal, m["ini"], m["fim"])
        reaj, qtd_anos = reajuste_acumulado(financeiro, m["ini"], m["fim"])

        if inpc is None:
            continue

        # Ganho real via fator (mais preciso que diferença p.p.)
        fator_inpc = 1 + inpc / 100
        fator_reaj = 1 + reaj / 100
        ganho_real = round((fator_reaj / fator_inpc - 1) * 100, 2)

        # Parcial se menos meses que esperado
        meses_esperados = (m["fim"] - m["ini"] + 1) * 12
        parcial = qtd_meses < meses_esperados

        resultado.append({
            "nome": m["nome"],
            "periodo": [m["ini"], m["fim"]],
            "orientacao": m["orientacao"],
            "meses_contados": qtd_meses,
            "parcial": parcial,
            "inpc_acumulado": inpc,
            "reajuste_acumulado": reaj,
            "ganho_real_pct": ganho_real,
        })
        print(f"      {m['nome']:20} INPC {inpc:>6}%  |  Reaj {reaj:>6}%  |  "
              f"Real {ganho_real:>+7.2f}%")

    # Total 1995-2026
    inpc_total, qtd_total = inpc_acumulado(df_mensal, 1995, 2026)
    fator_total = 1 + inpc_total / 100
    print()
    print(f"      {'TOTAL 1995-2026':20} INPC {inpc_total:>6}%  ({qtd_total} meses)")

    saida = {
        "metadados": {
            "atualizado_em": datetime.now().strftime("%Y-%m-%d"),
            "fonte_inpc": "IBGE/SIDRA — Tabela 1736 (INPC mensal)",
            "fonte_reajustes": "ACTs/DCs dos Correios (financeiro.json)",
            "metodologia": (
                "INPC acumulado por mandato = composição das variações mensais oficiais "
                "do IBGE. Reajuste acumulado = composição dos reajustes do salário-base "
                "no mesmo período. Ganho real = (fator_reajuste / fator_inpc - 1) × 100."
            ),
            "inpc_total_1995_2026": inpc_total,
        },
        "mandatos": resultado,
    }

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] Salvo: {SAIDA}")
    print(f"     Tamanho: {SAIDA.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()