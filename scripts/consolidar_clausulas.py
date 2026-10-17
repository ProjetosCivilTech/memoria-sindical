# -*- coding: utf-8 -*-
"""
consolidar_clausulas.py — Tabela de cláusulas + relatório de qualidade.

Lê dados/extraidos/*/texto_paginas.txt (com marcadores --- p.N ---), detecta
cláusulas, extrai campos do documento (data-base, vigência, assinatura, greve)
e valores por cláusula (R$, %), mapeia para ID canônico via dicionário, e
gera:

    dados/consolidado/clausulas.json    (uma linha por cláusula, com texto)
    dados/consolidado/clausulas.csv     (achatado, sem texto completo)
    dados/consolidado/qualidade.txt     (relatório legível)
    dados/consolidado/resumo.json       (contadores por tipo e por documento)
    dados/consolidado/_pendentes.json   (cláusulas sem ID canônico)

REGRA: não corrige nem normaliza. Preserva o que está no documento.

Uso no Spyder:
    %cd F:\\AUTOMAÇÕES\\projeto_memoria_sindicato
    %run scripts/consolidar_clausulas.py
    %run scripts/consolidar_clausulas.py --only "1988"
    %run scripts/consolidar_clausulas.py --com-texto-completo
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

RAIZ       = Path(r"F:\AUTOMAÇÕES\projeto_memoria_sindicato")
DADOS      = RAIZ / "dados"
EXTRAIDOS  = DADOS / "extraidos"
CONSOLID   = DADOS / "consolidado"
DICIONARIO_JSON = DADOS / "dicionario_ids.json"

SAIDA_JSON  = CONSOLID / "clausulas.json"
SAIDA_CSV   = CONSOLID / "clausulas.csv"
SAIDA_QUAL  = CONSOLID / "qualidade.txt"
SAIDA_RES   = CONSOLID / "resumo.json"
SAIDA_PEND  = CONSOLID / "_pendentes.json"


# ===========================================================================
# DICIONÁRIO PADRÃO (embutido). Se existir dicionario_ids.json, ele vence.
# ===========================================================================

DICIONARIO_PADRAO = {
    # financeiro
    "reajuste salarial": "FIN_REAJUSTE_SALARIAL",
    "reajuste": "FIN_REAJUSTE_SALARIAL",
    "vale alimentacao": "FIN_VALE_ALIMENTACAO",
    "vale alimentação": "FIN_VALE_ALIMENTACAO",
    "vale refeicao": "FIN_VALE_ALIMENTACAO",
    "vale refeição": "FIN_VALE_ALIMENTACAO",
    "vale cesta": "FIN_VALE_CESTA",
    "vale transporte": "FIN_VALE_TRANSPORTE",
    "vale-transporte": "FIN_VALE_TRANSPORTE",
    "vale cultura": "FIN_VALE_CULTURA",
    "adicional noturno": "FIN_ADICIONAL_NOTURNO",
    "horas extras": "FIN_HORAS_EXTRAS",
    "adicional de atividade distribuicao e coleta": "FIN_AADC",
    "adicional de atividade distribuição e coleta": "FIN_AADC",
    "aadc": "FIN_AADC",
    "gratificacao de ferias": "FIN_GRATIFICACAO_FERIAS",
    "gratificação de férias": "FIN_GRATIFICACAO_FERIAS",
    "anuênios": "FIN_ANUENIOS",
    "anuenios": "FIN_ANUENIOS",
    "plr": "FIN_PLR",
    "participacao nos lucros": "FIN_PLR",
    "participação nos lucros": "FIN_PLR",
    "reembolso creche": "FIN_REEMBOLSO_CRECHE_BABA",
    "reembolso-creche": "FIN_REEMBOLSO_CRECHE_BABA",
    "antecipacao de gratificacao natalina": "FIN_ANTECIPACAO_GRATIFICACAO_NATALINA",
    "antecipação de gratificação natalina": "FIN_ANTECIPACAO_GRATIFICACAO_NATALINA",
    "assistencia medica": "SOC_ASSISTENCIA_MEDICA",
    "assistência médica": "SOC_ASSISTENCIA_MEDICA",
    "plano de saude": "SOC_PLANO_SAUDE",
    "plano de saúde": "SOC_PLANO_SAUDE",
    "auxilio para dependentes": "SOC_AUXILIO_DEPENDENTES_DEFICIENCIA",
    "auxílio para dependentes": "SOC_AUXILIO_DEPENDENTES_DEFICIENCIA",
    "licenca adocao": "SOC_LICENCA_ADOCAO",
    "licença adoção": "SOC_LICENCA_ADOCAO",
    "licenca maternidade": "SOC_PRORROGACAO_LICENCA_MATERNIDADE",
    "licença maternidade": "SOC_PRORROGACAO_LICENCA_MATERNIDADE",
    "saude da mulher": "SOC_SAUDE_MULHER",
    "saúde da mulher": "SOC_SAUDE_MULHER",
    "assedio sexual": "SOC_ASSEDIO_SEXUAL_MORAL",
    "assédio sexual": "SOC_ASSEDIO_SEXUAL_MORAL",
    "cipa": "CON_CIPA",
    "comissao interna de prevencao": "CON_CIPA",
    "comissão interna de prevenção": "CON_CIPA",
    "registro de ponto": "CON_REGISTRO_PONTO",
    "jornada de trabalho": "CON_JORNADA_AGENCIAS",
    "distribuicao domiciliaria": "CON_DISTRIBUICAO_DOMICILIARIA",
    "distribuição domiciliária": "CON_DISTRIBUICAO_DOMICILIARIA",
    "ergonomia": "CON_ERGONOMIA",
    "itens de protecao": "CON_ITENS_USO_PROTECAO",
    "itens de proteção": "CON_ITENS_USO_PROTECAO",
    "anistia": "SIN_ANISTIA",
    "desconto assistencial": "SIN_DESCONTO_ASSISTENCIAL",
    "liberacao de dirigentes sindicais": "SIN_LIBERACAO_DIRIGENTES",
    "liberação de dirigentes sindicais": "SIN_LIBERACAO_DIRIGENTES",
    "quadro de avisos": "SIN_QUADRO_AVISOS",
    "diversidade": "SIN_DIVERSIDADE",
    "equidade racial": "SIN_EQUIDADE_RACIAL",
    "equidade de genero": "SIN_EQUIDADE_GENERO",
    "equidade de gênero": "SIN_EQUIDADE_GENERO",
    "empregado estudante": "SIN_EMPREGADO_ESTUDANTE",
    "aposentados": "SIN_APOSENTADOS",
    "concurso publico": "PRO_CONCURSO_PUBLICO",
    "concurso público": "PRO_CONCURSO_PUBLICO",
    "ampla defesa": "PRO_AMPLA_DEFESA",
    "negociacao coletiva": "PRO_NEGOCIACAO_COLETIVA",
    "negociação coletiva": "PRO_NEGOCIACAO_COLETIVA",
    "processo permanente": "PRO_PROCESSO_PERMANENTE",
    "conciliacao de divergencias": "PRO_CONCILIACAO_DIVERGENCIAS",
    "conciliação de divergências": "PRO_CONCILIACAO_DIVERGENCIAS",
    "vigencia": "PRO_VIGENCIA",
    "vigência": "PRO_VIGENCIA",
    "prorrogacao": "PRO_PRORROGACAO_REVISAO",
    "prorrogação": "PRO_PRORROGACAO_REVISAO",
}


def normalizar(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = txt.encode("ASCII", "ignore").decode()
    txt = re.sub(r"[^\w\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


# ===========================================================================
# REGEX
# ===========================================================================

# 3 padrões de cláusula (numeração 1ª, 1., Cláusula 1)
RE_CLAUSULA = [
    re.compile(
        r"^\s*(\d{1,3})\s*[ªº]\s*[\)\-–]\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,200})$",
        re.MULTILINE),
    re.compile(
        r"^\s*Cl[áa]usula\s+(\d{1,3})\s*[-–]\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,200})$",
        re.MULTILINE | re.IGNORECASE),
    re.compile(
        r"^\s*(\d{1,3})\.\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s\-/]{4,120})$",
        re.MULTILINE),
]

RE_PAGINA = re.compile(r"---\s*p\.(\d+)[^\-]*---")

# Regex de extração (por documento)
RX = {
    "data_base": re.compile(
        r"data[\s\-]?base[^\n]{0,120}", re.IGNORECASE),
    "data_base_explicita": re.compile(
        r"\b\d{1,2}\s*[ºo°]?\s*de\s+(janeiro|fevereiro|março|abril|maio|"
        r"junho|julho|agosto|setembro|outubro|novembro|dezembro)",
        re.IGNORECASE),
    "vigencia": re.compile(
        r"vig[êe]ncia[^\n]{0,180}", re.IGNORECASE),
    "periodo": re.compile(
        r"\b\d{2}/\d{2}/\d{2,4}\s*(?:a|à|até|-)\s*\d{2}/\d{2}/\d{2,4}\b",
        re.IGNORECASE),
    "assinatura": re.compile(
        r"[^\n]{0,80}assinad[oa][^\n]{0,120}", re.IGNORECASE),
    "brasilia_data": re.compile(
        r"Bras[íi]lia[^\n]{0,10},?\s*\d{1,2}\s*de\s+\w+\s*de\s*\d{4}",
        re.IGNORECASE),
    "greve": re.compile(
        r"\bgreve\b", re.IGNORECASE),
    "data_numerica": re.compile(
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    "valor_brl": re.compile(
        r"R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?"),
    "percentual": re.compile(
        r"\b\d{1,3}(?:[.,]\d{1,4})?\s*%"),
    "data_base_nomeada": re.compile(
        r"1\s*[ºo°]?\s*de\s+(setembro|agosto|julho|outubro|novembro)",
        re.IGNORECASE),
}


# ===========================================================================
# HELPERS
# ===========================================================================

def carregar_dicionario() -> dict:
    if DICIONARIO_JSON.exists():
        try:
            d = json.loads(DICIONARIO_JSON.read_text(encoding="utf-8"))
            print(f"[OK] Dicionário externo carregado: "
                  f"{len(d)} entradas ({DICIONARIO_JSON.name})")
            return d
        except Exception as e:
            print(f"[AVISO] {DICIONARIO_JSON.name} inválido: {e}")
    print(f"[info] Usando dicionário embutido ({len(DICIONARIO_PADRAO)} entradas)")
    return DICIONARIO_PADRAO


def classificar_tipo(nome: str) -> tuple[str, str]:
    """Retorna (tipo, motivo). Preserva ordem de prioridade."""
    n = nome.lower()
    if "acórdão" in n or "acordao" in n:
        return "DC", "acórdão no nome"
    if n.startswith("act-") or " act-" in n or "-act-" in n:
        return "ACT", "ACT no nome"
    if "acordo-coletivo" in n or "acordo coletivo" in n:
        return "ACT", "Acordo-Coletivo no nome"
    if re.match(r"^dc\s", n):
        return "DC", "prefixo DC"
    if "termo_aditivo" in n or "termo aditivo" in n:
        return "ACT", "Termo Aditivo"
    return "OUTRO", "não classificado"


def parse_anos(nome: str) -> tuple[int | None, int | None]:
    """Extrai ano_inicio e ano_fim do nome do arquivo."""
    anos = re.findall(r"\b(19\d{2}|20\d{2})\b", nome)
    if not anos:
        return None, None
    if len(anos) == 1:
        return int(anos[0]), int(anos[0])
    return int(anos[0]), int(anos[1])


def indexar_paginas(texto: str) -> list[tuple[int, int, int]]:
    """Devolve [(pos_inicio, pos_fim, numero_pagina), ...]."""
    intervalos = []
    marcadores = list(RE_PAGINA.finditer(texto))
    for i, m in enumerate(marcadores):
        inicio = m.end()
        fim = marcadores[i + 1].start() if i + 1 < len(marcadores) else len(texto)
        intervalos.append((inicio, fim, int(m.group(1))))
    return intervalos


def pagina_de(posicao: int, intervalos: list) -> int | None:
    for ini, fim, pag in intervalos:
        if ini <= posicao < fim:
            return pag
    return None


# ===========================================================================
# DETECÇÃO DE CLÁUSULAS
# ===========================================================================

def detectar_clausulas(texto: str) -> list[dict]:
    achados = []
    for rx in RE_CLAUSULA:
        for m in rx.finditer(texto):
            achados.append({
                "numero": int(m.group(1)),
                "titulo_original": m.group(2).strip(),
                "_start": m.start(),
                "_end":   m.end(),
            })
    # deduplicar por (numero, posição aproximada)
    vistos = {}
    for a in achados:
        chave = (a["numero"], a["_start"] // 200)
        if chave not in vistos:
            vistos[chave] = a
    return sorted(vistos.values(), key=lambda x: x["_start"])


def extrair_corpo(texto: str, clausulas: list, tam_max: int = 3000) -> None:
    for i, c in enumerate(clausulas):
        ini = c["_end"]
        fim = clausulas[i + 1]["_start"] if i + 1 < len(clausulas) \
              else min(ini + tam_max, len(texto))
        corpo = texto[ini:fim]
        corpo = re.sub(r"---\s*p\.\d+[^\-]*---", " ", corpo)
        corpo = re.sub(r"\s+", " ", corpo).strip()
        c["texto"] = corpo[:tam_max]


# ===========================================================================
# EXTRAÇÃO POR DOCUMENTO
# ===========================================================================

def extrair_metadados_documento(texto: str) -> dict:
    out = {}
    # data-base — pega o trecho bruto (não interpreta)
    m = RX["data_base"].search(texto)
    out["data_base_trecho"] = m.group(0).strip() if m else None

    # Data-base nomeada (ex: "1º de setembro")
    m = RX["data_base_nomeada"].search(texto)
    out["data_base_nomeada"] = m.group(0) if m else None

    # Vigência — trecho bruto
    m = RX["vigencia"].search(texto)
    out["vigencia_trecho"] = m.group(0).strip() if m else None

    # Período numérico dd/mm/aaaa a dd/mm/aaaa
    m = RX["periodo"].search(texto)
    out["vigencia_periodo"] = m.group(0) if m else None

    # Assinatura
    m = RX["assinatura"].search(texto)
    out["assinatura_trecho"] = m.group(0).strip() if m else None

    m = RX["brasilia_data"].search(texto)
    out["data_assinatura_brasilia"] = m.group(0) if m else None

    # Greve — conta ocorrências
    out["greve_mencoes"] = len(RX["greve"].findall(texto))

    return out


# ===========================================================================
# MAPEAMENTO DE ID
# ===========================================================================

def mapear_id(titulo: str, dicionario: dict) -> tuple[str | None, str]:
    t_norm = normalizar(titulo)
    if t_norm in dicionario:
        return dicionario[t_norm], "dicionario_exato"
    # substring: procura chave mais longa contida no título
    candidatos = [(k, v) for k, v in dicionario.items()
                  if normalizar(k) and normalizar(k) in t_norm]
    if candidatos:
        candidatos.sort(key=lambda x: -len(x[0]))
        return candidatos[0][1], "dicionario_substring"
    return None, "nao_encontrado"


def gerar_id_generico(titulo: str) -> str:
    t = unicodedata.normalize("NFKD", titulo)
    t = t.encode("ASCII", "ignore").decode().upper()
    t = re.sub(r"[^\w\s]", "", t)
    return "GEN_" + "_".join(t.split()[:5])[:80]


# ===========================================================================
# PROCESSAMENTO POR DOCUMENTO
# ===========================================================================

def processar_documento(pasta: Path, dicionario: dict,
                        incluir_texto: bool) -> dict:
    # prefere texto_paginas.txt
    arq = pasta / "texto_paginas.txt"
    if not arq.exists():
        arq = pasta / "texto.txt"
    if not arq.exists():
        return {"erro": "sem txt"}

    texto = arq.read_text(encoding="utf-8")

    paginas = indexar_paginas(texto)
    meta_doc = extrair_metadados_documento(texto)
    clausulas = detectar_clausulas(texto)
    extrair_corpo(texto, clausulas)

    tipo, motivo_tipo = classificar_tipo(pasta.name)
    ano_ini, ano_fim = parse_anos(pasta.name)

    linhas = []
    for c in clausulas:
        # valor bruto do corpo (sem normalizar)
        m_brl = RX["valor_brl"].search(c.get("texto", ""))
        m_pct = RX["percentual"].search(c.get("texto", ""))
        valor_atual = None
        unidade = None
        if m_brl:
            valor_atual, unidade = m_brl.group(0), "R$"
        if m_pct:
            # se ambos, prioriza R$ se estiver no primeiro 200 chars
            if not valor_atual:
                valor_atual, unidade = m_pct.group(0), "%"

        id_canon, fonte_id = mapear_id(c["titulo_original"], dicionario)
        novo = id_canon is None
        if novo:
            id_canon = gerar_id_generico(c["titulo_original"])

        linhas.append({
            "arquivo": pasta.name,
            "tipo": tipo,
            "tipo_motivo": motivo_tipo,
            "ano_inicio": ano_ini,
            "ano_fim": ano_fim,
            "data_base": meta_doc.get("data_base_nomeada"),
            "data_base_trecho": meta_doc.get("data_base_trecho"),
            "vigencia": meta_doc.get("vigencia_periodo"),
            "vigencia_trecho": meta_doc.get("vigencia_trecho"),
            "data_assinatura": meta_doc.get("data_assinatura_brasilia"),
            "greve": meta_doc["greve_mencoes"] > 0,
            "greve_mencoes": meta_doc["greve_mencoes"],
            "numero_clausula_original": c["numero"],
            "id_canonico": id_canon,
            "id_fonte": fonte_id,
            "titulo_original": c["titulo_original"],
            "status": "MANTIDO",              # preserva hipótese padrão
            "valor_atual": valor_atual,
            "unidade": unidade,
            "pagina_referencia": pagina_de(c["_start"], paginas),
            "observacao": None,
            "novo_id": novo,
            "chars_texto": len(c.get("texto", "")),
            **({"texto": c.get("texto", "")} if incluir_texto else {}),
        })

    return {
        "arquivo": pasta.name,
        "tipo": tipo,
        "ano_inicio": ano_ini,
        "ano_fim": ano_fim,
        "clausulas_detectadas": len(clausulas),
        "metadados_doc": meta_doc,
        "linhas": linhas,
        "erro": None,
    }


# ===========================================================================
# RELATÓRIO DE QUALIDADE
# ===========================================================================

def gerar_relatorio(docs: list[dict], linhas_todas: list[dict]) -> str:
    L = []
    L.append("=" * 78)
    L.append("RELATÓRIO DE QUALIDADE — CONSOLIDAÇÃO DE CLÁUSULAS")
    L.append("=" * 78)
    L.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L.append(f"Documentos processados: {len(docs)}")
    L.append(f"Total de cláusulas:     {len(linhas_todas):,}")
    L.append("")

    # Contadores por tipo
    por_tipo = Counter(l["tipo"] for l in linhas_todas)
    L.append("--- CLÁUSULAS POR TIPO ---")
    for k, v in por_tipo.most_common():
        L.append(f"  {k:<8} {v:>6,}")
    L.append("")

    # Documentos sem metadados
    sem_data_base = [d["arquivo"] for d in docs
                     if not d["metadados_doc"].get("data_base_nomeada")
                     and not d["metadados_doc"].get("data_base_trecho")]
    sem_assinatura = [d["arquivo"] for d in docs
                      if not d["metadados_doc"].get("data_assinatura_brasilia")
                      and not d["metadados_doc"].get("assinatura_trecho")]
    sem_vigencia = [d["arquivo"] for d in docs
                    if not d["metadados_doc"].get("vigencia_periodo")
                    and not d["metadados_doc"].get("vigencia_trecho")]

    L.append(f"--- DOCUMENTOS SEM DATA-BASE ({len(sem_data_base)}) ---")
    for a in sem_data_base:
        L.append(f"  {a}")
    L.append("")

    L.append(f"--- DOCUMENTOS SEM ASSINATURA ({len(sem_assinatura)}) ---")
    for a in sem_assinatura:
        L.append(f"  {a}")
    L.append("")

    L.append(f"--- DOCUMENTOS SEM VIGÊNCIA ({len(sem_vigencia)}) ---")
    for a in sem_vigencia:
        L.append(f"  {a}")
    L.append("")

    # Status distintos
    L.append("--- STATUS DISTINTOS ---")
    for s, n in Counter(l["status"] for l in linhas_todas).most_common():
        L.append(f"  {s:<20} {n:>6,}")
    L.append("")

    # IDs repetidos no mesmo documento
    L.append("--- IDs CANÔNICOS REPETIDOS NO MESMO DOCUMENTO ---")
    contador = defaultdict(list)
    for l in linhas_todas:
        contador[(l["arquivo"], l["id_canonico"])].append(
            l["numero_clausula_original"])
    repetidos = {k: v for k, v in contador.items() if len(v) > 1}
    if not repetidos:
        L.append("  (nenhum)")
    else:
        for (arq, cid), nums in sorted(repetidos.items()):
            L.append(f"  {arq} :: {cid} -> cláusulas {nums}")
    L.append("")

    # Cláusulas sem ID
    pendentes = [l for l in linhas_todas if l["novo_id"]]
    L.append(f"--- CLÁUSULAS SEM ID CANÔNICO ({len(pendentes)}) ---")
    for l in pendentes[:60]:
        L.append(f"  [{l['arquivo'][:40]:<40}] "
                 f"nº {l['numero_clausula_original']:>3} :: "
                 f"{l['titulo_original'][:60]}")
    if len(pendentes) > 60:
        L.append(f"  ... (+{len(pendentes) - 60})")
    L.append("")

    # Resumo por documento
    L.append("--- CLÁUSULAS POR DOCUMENTO ---")
    L.append(f"{'arquivo':<55} {'tipo':<6} {'cláus':>6}")
    L.append("-" * 78)
    for d in sorted(docs, key=lambda x: (x["ano_inicio"] or 0, x["arquivo"])):
        L.append(f"{d['arquivo'][:53]:<55} {d['tipo']:<6} "
                 f"{d['clausulas_detectadas']:>6}")
    L.append("")

    # Greves
    docs_com_greve = [d for d in docs if d["metadados_doc"].get("greve_mencoes", 0) > 0]
    L.append(f"--- DOCUMENTOS QUE MENCIONAM 'GREVE' ({len(docs_com_greve)}) ---")
    for d in docs_com_greve:
        L.append(f"  {d['arquivo'][:60]:<60} "
                 f"({d['metadados_doc']['greve_mencoes']} menções)")
    L.append("")

    return "\n".join(L)


# ===========================================================================
# CSV
# ===========================================================================

CAMPOS_CSV = [
    "arquivo", "tipo", "ano_inicio", "ano_fim",
    "data_base", "data_base_trecho",
    "vigencia", "vigencia_trecho",
    "data_assinatura",
    "greve", "greve_mencoes",
    "numero_clausula_original",
    "id_canonico", "id_fonte", "novo_id",
    "titulo_original", "status",
    "valor_atual", "unidade",
    "pagina_referencia", "chars_texto", "observacao",
]


def salvar_csv(linhas: list[dict]) -> None:
    with SAIDA_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_CSV, extrasaction="ignore",
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for l in linhas:
            w.writerow({k: l.get(k) for k in CAMPOS_CSV})
    tam = SAIDA_CSV.stat().st_size / 1024
    print(f"[OK] {SAIDA_CSV.name} ({tam:.0f} KB)")


# ===========================================================================
# CLI
# ===========================================================================

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="",
                    help="Filtro por substring no nome da pasta do PDF.")
    ap.add_argument("--com-texto-completo", action="store_true",
                    help="Inclui o texto integral da cláusula no JSON "
                         "(o CSV nunca inclui).")
    return ap.parse_args()


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    args = parse_args()
    CONSOLID.mkdir(parents=True, exist_ok=True)

    if not EXTRAIDOS.exists():
        sys.exit(f"[ERRO] Não encontrei: {EXTRAIDOS}\n"
                 f"       Rode antes: scripts/extrair_tudo.py")

    pastas = sorted([p for p in EXTRAIDOS.iterdir() if p.is_dir()])
    if args.only:
        pastas = [p for p in pastas if args.only.lower() in p.name.lower()]
    print(f"[SCAN] {len(pastas)} documentos em {EXTRAIDOS}")

    dicionario = carregar_dicionario()

    print(f"[PROCESSANDO] ...")
    docs, linhas_todas = [], []
    for i, p in enumerate(pastas, 1):
        res = processar_documento(p, dicionario, args.com_texto_completo)
        if res.get("erro"):
            print(f"  [{i:>2}/{len(pastas)}] {p.name} -> [SKIP] {res['erro']}")
            continue
        docs.append(res)
        linhas_todas.extend(res["linhas"])
        print(f"  [{i:>2}/{len(pastas)}] {p.name:<50} "
              f"{res['clausulas_detectadas']:>4} cláusulas")

    print(f"\n[EXPORTANDO]")
    # JSON completo
    payload = {
        "metadados": {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "total_documentos": len(docs),
            "total_clausulas": len(linhas_todas),
            "com_texto_completo": args.com_texto_completo,
        },
        "por_documento": [
            {k: v for k, v in d.items() if k != "linhas"}
            for d in docs
        ],
        "clausulas": linhas_todas,
    }
    SAIDA_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8")
    tam = SAIDA_JSON.stat().st_size / 1024
    print(f"[OK] {SAIDA_JSON.name} ({tam:.0f} KB)")

    salvar_csv(linhas_todas)

    rel = gerar_relatorio(docs, linhas_todas)
    SAIDA_QUAL.write_text(rel, encoding="utf-8")
    print(f"[OK] {SAIDA_QUAL.name}")

    # Resumo compacto
    resumo = {
        "total_documentos": len(docs),
        "total_clausulas": len(linhas_todas),
        "por_tipo": dict(Counter(l["tipo"] for l in linhas_todas)),
        "por_ano": dict(sorted(Counter(
            (l["ano_inicio"], l["tipo"]) for l in linhas_todas).items())),
        "por_status": dict(Counter(l["status"] for l in linhas_todas)),
        "sem_id_canonico": sum(1 for l in linhas_todas if l["novo_id"]),
    }
    SAIDA_RES.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[OK] {SAIDA_RES.name}")

    # Pendentes
    pend = [l for l in linhas_todas if l["novo_id"]]
    SAIDA_PEND.write_text(
        json.dumps(pend, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[OK] {SAIDA_PEND.name} ({len(pend)} cláusulas)")

    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    print(f"  Documentos:  {len(docs)}")
    print(f"  Cláusulas:   {len(linhas_todas):,}")
    print(f"  Por tipo:    {dict(Counter(l['tipo'] for l in linhas_todas))}")
    print(f"  Sem ID:      {len(pend)}")
    print(f"\n  Abra o relatório completo em:\n  {SAIDA_QUAL}")


if __name__ == "__main__":
    main()