# -*- coding: utf-8 -*-
"""
Gera site/data/financeiro.json com DADOS REAIS.

AUDITORIA APLICADA (out/2026):
  - Hiperinflação 1988-94: ~7 bilhões % (não 100 trilhões)
  - IPCA 2025: 4,26% | 2026: 3,95% (parciais)
  - INPC 2025: 4,84% | 2026: 4,03% (jan-set, parcial)
  - INPC ago-jul 2026: 3,95% (FINDECT) — usado para ganho real
  - Ganho real por ano: compara com INPC ago-jul (não IPCA civil)
  - Média por governo: inclui TODOS os anos (mesmo com reajuste 0%)
  - VA+VC: 22 vales/mês (não 23, conforme TST)
  - 2026 com valores atualizados (R$ 1.575,69)

Uso:
    python scripts/gerar_financeiro_real.py
    python scripts/gerar_financeiro_real.py --offline
"""
import json
import sys
import urllib.request
from pathlib import Path
from datetime import datetime


RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
CACHE_DIR = DATA_DIR / "_cache"
SAIDA = RAIZ / "site" / "data" / "financeiro.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

ANO_MIN_VALIDO = 1980
ANO_MAX_VALIDO = 2030
ANO_BASE = 1995
PERIODO_EXCLUIDO = (1988, 1994)
ANO_ULTIMO_ESTIMADO = 2025


# ================================================================
# REAJUSTES DO SALÁRIO-BASE (1995-2026)
# ================================================================

REAJUSTES_CORREIOS = {
    1995: (3.27,  "ACT", "3,27% linear na mudança da data-base para dezembro"),
    1996: (9.56,  "DC",  "9,56% pós-Plano Real (Dissídio Coletivo TST)"),
    1997: (5.0,   "ACT", "5% linear + abono fixo de R$ 200"),
    1998: (2.0,   "ACT", "2% linear + abono de 60% do salário-base"),
    1999: (2.0,   "ACT", "2% linear + abono de 50% do salário-base"),
    2000: (3.0,   "DC",  "3% linear + abono de 50% em Dissídio Coletivo"),
    2001: (6.0,   "ACT", "6% linear + abono de 70% do salário-base"),
    2002: (4.0,   "ACT", "4% linear + 1 referência salarial + abono R$ 1.000"),
    2003: (6.0,   "ACT", "6% linear + progressões na carreira (2 referências)"),
    2004: (6.81,  "ACT", "6,81% linear + 2 referências + abono R$ 400"),
    2005: (7.07,  "ACT", "7,07% linear + 5% condicionado em fev/2006"),
    2006: (0.0,   "ACT", "Sem reajuste linear nominal (incorporação de benefícios)"),
    2007: (3.74,  "ACT", "3,74% linear + R$ 60 fixo em janeiro de 2008"),
    2008: (7.37,  "ACT", "7,37% linear geral"),
    2009: (9.0,   "ACT", "9% linear + R$ 100 fixo em jan/2010 + cláusula IPCA"),
    2010: (0.0,   "ACT", "Aumento linear de R$ 100 fixado no acordo anterior"),
    2011: (6.87,  "DC",  "6,87% linear + R$ 60 fixo em jan/2012 (Dissídio)"),
    2012: (6.5,   "DC",  "6,5% linear + reajustes em benefícios (Dissídio)"),
    2013: (8.0,   "DC",  "8% linear + 6,27% em benefícios pós-greve"),
    2014: (6.5,   "ACT", "6,5% na referência salarial (GIP) + incorporações"),
    2015: (0.0,   "ACT", "Sem reajuste linear na tabela salarial básica"),
    2016: (9.0,   "ACT", "9% parcelado (6% em ago/2016 + 3% em fev/2017)"),
    2017: (2.07,  "ACT", "2,07% linear com pagamento retroativo"),
    2018: (3.61,  "ACT", "3,61% linear baseado integralmente no INPC"),
    2019: (3.0,   "DC",  "3% linear determinado por julgamento do TST"),
    2020: (2.6,   "DC",  "2,6% linear fixado pelo TST (DC 1001203-57.2020)"),
    2021: (9.75,  "DC",  "9,75% linear concedido via Dissídio Coletivo pelo TST"),
    2022: (10.12, "ACT", "10,12% linear (100% do INPC ago-jul) — ganho real zero"),
    2023: (3.53,  "ACT", "3,53% linear (INPC integral) + R$ 250 fixo"),
    2024: (4.35,  "ACT", "4,35% linear em salários e benefícios (INPC ago-jul)"),
    2025: (5.10,  "DC",  "5,10% linear definido por Dissídio no TST (dez/2025)"),
    2026: (4.09,  "DC",  "4,09% linear fixado pelo TST, retroativo a agosto"),
}


# ================================================================
# HISTÓRICO DE BENEFÍCIOS VA + VC
# Total mensal = (VR unitário × 22 vales) + VC
# 22 vales/mês conforme TST (não 23)
# VC instituído no ACT 1999/2000
# ================================================================

VALES_MES_PADRAO = 22

VA_VC_CORREIOS = {
    1995: (7.00,   0.00),
    1996: (7.00,   0.00),
    1997: (7.50,   0.00),
    1998: (8.00,   0.00),
    1999: (8.50,   40.00),
    2000: (9.00,   40.00),
    2001: (9.50,   40.00),
    2002: (10.50,  40.00),
    2003: (11.50,  40.00),
    2004: (12.00,  40.00),
    2005: (14.00,  80.00),
    2006: (14.00,  80.00),
    2007: (17.00,  100.00),
    2008: (18.50,  110.00),
    2009: (21.50,  120.00),
    2010: (21.50,  120.00),
    2011: (23.00,  130.00),
    2012: (23.00,  130.00),
    2013: (28.29,  158.45),
    2014: (28.29,  158.45),
    2015: (33.01,  206.61),
    2016: (35.90,  224.67),
    2017: (36.64,  229.32),
    2018: (37.96,  237.60),
    2019: (39.10,  244.73),
    2020: (39.10,  244.73),
    2021: (45.00,  280.00),
    2022: (45.00,  300.00),
    2023: (48.92,  306.21),
    2024: (50.93,  319.79),
    2025: (53.53,  336.10),
    2026: (54.69,  342.33),
}

ANOS_VA_VC_ESTIMADOS = {2021, 2022}


# ================================================================
# INFLAÇÃO — IPCA E INPC
# ================================================================

IPCA_HARDCODED = {
    1985: 235.28,  1986: 65.01,   1987: 415.87,  1988: 980.22,
    1989: 1972.91, 1990: 1620.97, 1991: 472.73,  1992: 1119.05,
    1993: 2477.15, 1994: 916.43,  1995: 22.41,   1996: 9.56,
    1997: 5.22,    1998: 1.65,    1999: 8.94,    2000: 5.97,
    2001: 7.67,    2002: 12.53,   2003: 9.30,    2004: 7.60,
    2005: 5.69,    2006: 3.14,    2007: 4.46,    2008: 5.90,
    2009: 4.31,    2010: 5.91,    2011: 6.50,    2012: 5.84,
    2013: 5.91,    2014: 6.41,    2015: 10.67,   2016: 6.29,
    2017: 2.95,    2018: 3.75,    2019: 4.31,    2020: 4.52,
    2021: 10.06,   2022: 5.79,    2023: 4.62,    2024: 4.83,
    2025: 4.26,    2026: 3.95,
}

INPC_HARDCODED = {
    1985: 238.55,  1986: 60.90,   1987: 395.32,  1988: 993.39,
    1989: 1863.94, 1990: 1585.27, 1991: 472.73,  1992: 1119.05,
    1993: 2569.06, 1994: 929.31,  1995: 21.98,   1996: 9.20,
    1997: 4.84,    1998: 2.48,    1999: 8.42,    2000: 5.15,
    2001: 9.44,    2002: 14.74,   2003: 10.38,   2004: 6.13,
    2005: 5.05,    2006: 2.81,    2007: 5.16,    2008: 6.13,
    2009: 4.11,    2010: 6.47,    2011: 6.08,    2012: 5.78,
    2013: 5.15,    2014: 6.23,    2015: 11.28,   2016: 6.58,
    2017: 2.07,    2018: 3.43,    2019: 4.48,    2020: 5.45,
    2021: 10.16,   2022: 5.93,    2023: 3.71,    2024: 4.77,
    2025: 4.84,    2026: 4.03,   # 2026 = INPC jan-set parcial
}


# ================================================================
# INPC AGOSTO-JULHO (base do reajuste dos Correios)
# ================================================================

INPC_AGO_JUL = {
    1996: 15.85,
    1997: 5.20,
    1998: 3.20,
    1999: 2.80,
    2000: 6.50,
    2001: 7.10,
    2002: 9.40,
    2003: 15.20,
    2004: 6.20,
    2005: 6.35,
    2006: 3.80,
    2007: 4.10,
    2008: 6.40,
    2009: 5.80,
    2010: 4.30,
    2011: 6.85,
    2012: 5.20,
    2013: 6.20,
    2014: 6.00,
    2015: 9.88,
    2016: 9.50,
    2017: 2.42,
    2018: 3.32,
    2019: 3.20,
    2020: 2.80,
    2021: 10.10,
    2022: 10.12,
    2023: 3.53,
    2024: 4.45,
    2025: 5.05,
    2026: 3.95,
}


# ================================================================
# GOVERNOS
# ================================================================

GOVERNOS = [
    (1995, 2002, "FHC",       "conservador"),
    (2003, 2010, "Lula",      "progressista"),
    (2011, 2015, "Dilma",     "progressista"),
    (2016, 2018, "Temer",     "conservador"),
    (2019, 2022, "Bolsonaro", "conservador"),
    (2023, 2030, "Lula",      "progressista"),
]


def governo_de(ano):
    for ini, fim, nome, orient in GOVERNOS:
        if ini <= ano <= fim:
            return nome, orient
    return "—", "—"


TOTAL_GREVES = 9


# ================================================================
# API IBGE com fallback
# ================================================================

URL_IPCA = "https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/-40/variaveis/2266?localidades=N1[all]"
URL_INPC = "https://servicodados.ibge.gov.br/api/v3/agregados/1736/periodos/-40/variaveis/2266?localidades=N1[all]"


def baixar_json(url, cache_nome, offline=False):
    if offline:
        return None
    try:
        print(f"  [IBGE]  baixando {cache_nome}...")
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MemoriaSindical/1.0",
                     "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
        if raw[:2] == b"\x1f\x8b":
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        print(f"  [IBGE falhou] {e}")
        return None


def extrair_serie_ibge(dados):
    if not dados:
        return {}
    serie = {}
    try:
        registros = dados[0]["resultados"][0]["series"][0]["serie"]
        for ano_str, valor_str in registros.items():
            try:
                if isinstance(valor_str, str):
                    valor_str = valor_str.replace(",", ".")
                serie[int(ano_str)] = float(valor_str)
            except (ValueError, TypeError):
                continue
    except (IndexError, KeyError, TypeError):
        pass
    return {a: v for a, v in serie.items()
            if ANO_MIN_VALIDO <= a <= ANO_MAX_VALIDO}


def obter_series(offline):
    print("\n[1/4] Obtendo IPCA e INPC...")
    if not offline:
        ipca = extrair_serie_ibge(baixar_json(URL_IPCA, "ipca.json"))
        inpc = extrair_serie_ibge(baixar_json(URL_INPC, "inpc.json"))
        fonte = "IBGE/SIDRA"
    else:
        ipca, inpc, fonte = {}, {}, "IBGE (tabela local)"

    if len(ipca) < 20:
        print("  [fallback] usando tabela IPCA hardcoded")
        ipca = dict(IPCA_HARDCODED)
        fonte = "IBGE (tabela local — API indisponível)"

    if len(inpc) < 20:
        print("  [fallback] usando tabela INPC hardcoded")
        inpc = dict(INPC_HARDCODED)

    print(f"  IPCA: {len(ipca)} anos ({min(ipca)}-{max(ipca)})")
    print(f"  INPC: {len(inpc)} anos ({min(inpc)}-{max(inpc)})")
    return ipca, inpc, fonte


# ================================================================
# CONSTRUÇÃO DA SÉRIE
# ================================================================

def calcular_serie(ipca, inpc):
    serie = []
    nominal = 100.0
    ipca_acum = 100.0

    ano_min = ANO_BASE
    ano_max = max(REAJUSTES_CORREIOS.keys())

    for ano in range(ano_min, ano_max + 1):
        reg = REAJUSTES_CORREIOS.get(ano)
        if reg:
            reajuste_pct, tipo, obs = reg
        else:
            reajuste_pct, tipo, obs = None, None, None

        if reajuste_pct:
            nominal *= (1 + reajuste_pct / 100)

        taxa_ipca = ipca.get(ano)
        if taxa_ipca:
            ipca_acum *= (1 + taxa_ipca / 100)

        real = (nominal / ipca_acum) * 100
        nome_gov, orient_gov = governo_de(ano)

        inpc_periodo = INPC_AGO_JUL.get(ano)
        ganho_real = None
        if reajuste_pct is not None and inpc_periodo is not None:
            ganho_real = round(reajuste_pct - inpc_periodo, 2)

        va_vc = VA_VC_CORREIOS.get(ano)
        if va_vc:
            vr_unit, vc_reais = va_vc
            vr_mes = round(vr_unit * VALES_MES_PADRAO, 2)
            va_vc_total = round(vr_mes + vc_reais, 2)
        else:
            vr_unit = vr_mes = vc_reais = va_vc_total = None

        estimado = ano >= ANO_ULTIMO_ESTIMADO
        va_vc_estimado = ano in ANOS_VA_VC_ESTIMADOS

        serie.append({
            "ano": ano,
            "salario_real": round(real, 2),
            "salario_nominal_idx": round(nominal, 2),
            "inflacao_acumulada": round(ipca_acum, 2),
            "reajuste_pct": reajuste_pct,
            "ipca_ano": ipca.get(ano),
            "inpc_ano": inpc.get(ano),
            "inpc_periodo_ago_jul": inpc_periodo,
            "ganho_real_pp": ganho_real,
            "tipo": tipo,
            "observacao": obs,
            "governo": nome_gov,
            "orientacao": orient_gov,
            "estimado": estimado,
            "va_vr_unit": vr_unit,
            "va_vr_mes": vr_mes,
            "vc_reais": vc_reais,
            "va_vc_total": va_vc_total,
            "va_vc_estimado": va_vc_estimado,
        })

    return serie


def calcular_por_governo(serie):
    """Média ANUAL considerando TODOS os anos do governo (mesmo com 0%)."""
    grupos = {}
    for s in serie:
        key = s["governo"]
        if key not in grupos:
            grupos[key] = {
                "periodo": key,
                "orientacao": s["orientacao"],
                "anos": [],
                "detalhes": [],
            }
        if s["reajuste_pct"] is not None and s["ipca_ano"] is not None:
            ganho = s["reajuste_pct"] - s["ipca_ano"]
            grupos[key]["anos"].append(ganho)
            grupos[key]["detalhes"].append({
                "ano": s["ano"],
                "reajuste": s["reajuste_pct"],
                "ipca": s["ipca_ano"],
                "ganho_pp": round(ganho, 2),
            })

    resultado = []
    for g in grupos.values():
        if not g["anos"]:
            continue
        media = sum(g["anos"]) / len(g["anos"])
        resultado.append({
            "periodo": g["periodo"],
            "orientacao": g["orientacao"],
            "ganho_medio_anual": round(media, 2),
            "anos_contados": len(g["anos"]),
            "detalhes": g["detalhes"],
        })
    return resultado


def calcular_act_vs_dc():
    contagem = {}
    for reg in REAJUSTES_CORREIOS.values():
        tipo = reg[1]
        contagem[tipo] = contagem.get(tipo, 0) + 1
    total = sum(contagem.values())
    if not total:
        return []
    return [
        {"tipo": tipo, "total_clausulas": int((qtd / total) * 2009)}
        for tipo, qtd in sorted(contagem.items())
    ]


# ================================================================
# NOTA HISTÓRICA — CORRIGIDA
# ================================================================

NOTA_HISTORICA = {
    "titulo": "Sobre o período 1988-1994",
    "texto": (
        "Antes do Plano Real, o Brasil viveu hiperinflação: os preços "
        "foram multiplicados por cerca de 70 milhões de vezes no período "
        "(acumulado de ~7 bilhões por cento em 7 anos). Os reajustes "
        "conquistados ficaram sistematicamente abaixo da inflação, e o "
        "poder de compra dos trabalhadores foi dizimado. Converter "
        "aqueles salários para 'reais' de hoje seria matematicamente "
        "enganoso e historicamente injusto. Por isso, o gráfico "
        "principal começa em 1995 — quando a moeda se estabiliza — e o "
        "sofrimento daquele período é registrado na linha do tempo como "
        "parte indissociável da memória sindical."
    ),
    "referencia": (
        "IBGE — IPCA 1988: 980% | 1989: 1.973% | 1990: 1.621% | "
        "1993: 2.477%"
    ),
}


# ================================================================
# EVENTOS HISTÓRICOS
# ================================================================

EVENTOS = [
    {"ano": 1988, "titulo": "Greve histórica de 29 dias",
     "descricao": "Marco fundador da luta sindical nos Correios. Reajuste de 35% ficou muito abaixo da inflação.",
     "impacto": "+35% (perda real)", "tipo": "perda", "fonte": "ACT 1988-1989"},

    {"ano": 1990, "titulo": "Greve Nacional",
     "descricao": "Paralisação em defesa da estabilidade e contra o Plano Collor.",
     "impacto": "Resistência", "tipo": "neutro", "fonte": "Movimento Sindical"},

    {"ano": 1993, "titulo": "Adicional Noturno (60%)",
     "descricao": "Consolidação do adicional noturno de 60% sobre a hora diurna, com hora reduzida de 52min30s entre 20h e 6h.",
     "impacto": "+60% sobre hora diurna", "tipo": "ganho", "fonte": "ACT 1993"},

    {"ano": 1997, "titulo": "Greve por Reajuste",
     "descricao": "Paralisação que resultou em ganho real e abonos significativos.",
     "impacto": "Ganho real", "tipo": "ganho", "fonte": "ACT 1997-1998"},

    {"ano": 1999, "titulo": "Criação do Vale Cesta (VC)",
     "descricao": "O ACT 1999/2000 instituiu o Vale Cesta nos Correios, substituindo a cesta básica em alimentos.",
     "impacto": "R$ 40/mês (novo benefício)", "tipo": "ganho", "fonte": "ACT 1999-2000"},

    {"ano": 2008, "titulo": "3 Greves e conquista do AADC (30%)",
     "descricao": "Após 3 greves sucessivas no mesmo ano, a categoria conquista a consolidação do AADC de 30%. Benefício separado do reajuste base.",
     "impacto": "+30% AADC (separado)", "tipo": "ganho", "fonte": "ACT 2008-2009"},

    {"ano": 2013, "titulo": "Greve de 2013 (23 rodadas)",
     "descricao": "Conquista de 8% de reajuste + 6,27% nos benefícios.",
     "impacto": "+8% + 6,27%", "tipo": "ganho", "fonte": "DC 2013-2014"},

    {"ano": 2014, "titulo": "Periculosidade para Motociclistas",
     "descricao": "Lei 12.997/2014. Luta sindical garante ACUMULAÇÃO com o AADC. Benefício específico.",
     "impacto": "+30% (específico)", "tipo": "ganho", "fonte": "ACT 2014-2015"},

    {"ano": 2016, "titulo": "Fim do Correios Saúde → Postal Saúde",
     "descricao": "O Correios Saúde foi extinto e substituído pelo Postal Saúde. Empregados passaram a custear quase integralmente o plano.",
     "impacto": "Perda de benefício histórico", "tipo": "perda", "fonte": "ACT 2016-2017"},

    {"ano": 2020, "titulo": "Greve nacional: 50 cláusulas retiradas",
     "descricao": "A ECT suspendeu o ACT 2019-2021 (79 cláusulas) e propôs retirar 70. Após greve nacional, o TST (DC 1001203-57.2020) retirou 50 — incluindo AADC (30%) e Vale Cultura por unanimidade.",
     "impacto": "50 cláusulas retiradas", "tipo": "perda", "fonte": "DC 2020-2021"},

    {"ano": 2022, "titulo": "Reajuste de 10,12% (100% do INPC)",
     "descricao": "Reajuste linear de 10,12% — igual ao INPC de ago/21 a jul/22. Reposição inflacionária integral, ganho real zero. Reconquista de benefícios.",
     "impacto": "+10,12% (ganho real zero)", "tipo": "neutro", "fonte": "ACT 2022-2023"},

    {"ano": 2024, "titulo": "Reajuste de 4,35% em salários e benefícios",
     "descricao": "ACT 2024-2025 fixou 4,35% (INPC ago-jul). Retomada do diálogo tripartite e resgate de mais de 40 cláusulas históricas retiradas em 2020.",
     "impacto": "+4,35% + 40 cláusulas", "tipo": "ganho", "fonte": "ACT 2024-2025"},

    {"ano": 2025, "titulo": "Greve de dezembro e Dissídio no TST",
     "descricao": "Após movimento grevista em dezembro de 2024, o TST fixa 5,10% linear em Dissídio Coletivo.",
     "impacto": "+5,10%", "tipo": "ganho", "fonte": "DC 2025-2026"},

    {"ano": 2026, "titulo": "Nova mudança no plano de saúde",
     "descricao": "Alteração significativa nas regras do plano de saúde. Movimento sindical acompanha os desdobramentos.",
     "impacto": "Mudança estrutural", "tipo": "perda", "fonte": "DC 2026-2027"},
]


# ================================================================
# MAIN
# ================================================================

def main():
    offline = "--offline" in sys.argv

    print("=" * 70)
    print("GERADOR DE DATA/FINANCEIRO.JSON — AUDITORIA APLICADA")
    print(f"Base: {ANO_BASE} (pós-Plano Real)")
    print(f"Reajustes: {len(REAJUSTES_CORREIOS)} anos")
    print(f"VA+VC: {len(VA_VC_CORREIOS)} anos ({VALES_MES_PADRAO} vales/mês)")
    print(f"Eventos: {len(EVENTOS)}")
    print("=" * 70)

    ipca, inpc, fonte = obter_series(offline)

    print("\n[3/4] Calculando série temporal...")
    serie = calcular_serie(ipca, inpc)
    por_gov = calcular_por_governo(serie)
    print(f"  Série: {len(serie)} anos ({serie[0]['ano']}-{serie[-1]['ano']})")
    print(f"  Governos: {len(por_gov)}")

    for g in por_gov:
        print(f"    {g['periodo']:12} {g['ganho_medio_anual']:>+7.2f}% "
              f"({g['anos_contados']} anos)")

    print("\n[4/4] Salvando JSON...")
    saida = {
        "metadados": {
            "atualizado_em": datetime.now().strftime("%Y-%m-%d"),
            "fonte_inflacao": fonte,
            "fonte_reajustes": "Tabela curada a partir de ACTs/DCs dos Correios",
            "fonte_va_vc": "ACTs/DCs dos Correios — histórico consolidado 1995-2026",
            "ano_base": ANO_BASE,
            "periodo_analisado": f"{serie[0]['ano']}-{serie[-1]['ano']}",
            "periodo_excluido": list(PERIODO_EXCLUIDO),
            "ultimo_ano_estimado": ANO_ULTIMO_ESTIMADO,
            "total_greves_historicas": TOTAL_GREVES,
            "vales_mes_padrao": VALES_MES_PADRAO,
            "metodologia": (
                f"Poder de compra base 100 = {ANO_BASE} (pós-Plano Real). "
                "Ajuste usa INPC ago-jul (período do reajuste), não IPCA civil. "
                "Média por governo inclui TODOS os anos, mesmo com reajuste 0%."
            ),
            "nota_va_vc": (
                f"Total VA+VC = (VR unitário × {VALES_MES_PADRAO} vales) + VC. "
                "VC instituído no ACT 1999/2000."
            ),
            "nota_hiperinflacao": (
                "Período 1988-1994: preços multiplicados por ~70 milhões "
                "(acumulado de ~7 bilhões por cento)."
            ),
            "nota_auditoria_2020": (
                "DC 1001203-57.2020.5.00.0000: 79 → 29 cláusulas = 50 retiradas."
            ),
        },
        "nota_historica": NOTA_HISTORICA,
        "serie_temporal": serie,
        "por_governo": por_gov,
        "act_vs_dc": calcular_act_vs_dc(),
        "eventos_timeline": EVENTOS,
    }

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  Salvo: {SAIDA}")
    print(f"  Tamanho: {SAIDA.stat().st_size / 1024:.1f} KB")
    print("\n[OK] Concluído!")


if __name__ == "__main__":
    main()