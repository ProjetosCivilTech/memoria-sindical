"""
Re-extrai os PDFs ACT 2019-2021 e Acórdão 2020-2021 com mapeamento
inteligente de IDs canônicos.

Melhorias vs v1:
  - Corta título antes do separador '–'
  - Usa dicionário de palavras-chave (70+ entradas)
  - Fallback para similaridade se não encontrar no dicionário

Uso no Spyder:
    F5
"""
import json
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    print("[ERRO] pip install pdfplumber")
    raise


RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
DADOS_DIR = RAIZ / "dados"

ALVOS = [
    {
        "pdf": DADOS_DIR / "Acordao-2019-2021.pdf",
        "json_saida": DATA_DIR / "DC 2019-2021.json",
        "referencia": DATA_DIR / "ACT 2018-2019.json",
        "esperado_min": 70,
        "esperado_max": 95,
        "ano_ini": 2019,
        "ano_fim": 2021,
        "tipo": "DC",
    },
    {
        "pdf": DADOS_DIR / "Acordao-2020-2021.pdf",
        "json_saida": DATA_DIR / "DC 2020-2021.json",
        "referencia": DATA_DIR / "DC 2019-2021.json",
        "esperado_min": 25,
        "esperado_max": 35,
        "ano_ini": 2020,
        "ano_fim": 2021,
        "tipo": "DC",
    },
]


# ================================================================
# DICIONÁRIO DE MAPEAMENTO — TÍTULO → ID CANÔNICO
# Baseado nos IDs canônicos existentes na base
# ================================================================

MAPA_TITULOS = {
    # --- FINANCEIRO ---
    "reajuste salarial": "FIN_REAJUSTE_SALARIAL",
    "reajuste": "FIN_REAJUSTE_SALARIAL",
    "vale refeição/alimentação": "FIN_VALE_ALIMENTACAO",
    "vale alimentação/refeição": "FIN_VALE_ALIMENTACAO",
    "vale refeição": "FIN_VALE_ALIMENTACAO",
    "vale alimentação": "FIN_VALE_ALIMENTACAO",
    "vale cesta": "FIN_VALE_CESTA",
    "acumulação de vantagens": "FIN_ACUMULACAO_VANTAGENS",
    "adiantamento de férias": "FIN_ADIANTAMENTO_FERIAS",
    "adicional noturno": "FIN_ADICIONAL_NOTURNO",
    "antecipação de 50% da gratificação natalina": "FIN_ANTECIPACAO_GRATIFICACAO_NATALINA",
    "antecipação de gratificação natalina": "FIN_ANTECIPACAO_GRATIFICACAO_NATALINA",
    "anuênios": "FIN_ANUENIOS",
    "gratificação de férias": "FIN_GRATIFICACAO_FERIAS",
    "gratificação de quebra de caixa": "FIN_GRATIFICACAO_QUEBRA_CAIXA",
    "horas extras": "FIN_HORAS_EXTRAS",
    "horas-extras": "FIN_HORAS_EXTRAS",
    "pagamento de salário": "FIN_PAGAMENTO_SALARIO",
    "pagamento de salários": "FIN_PAGAMENTO_SALARIO",
    "trabalho em dia de repouso": "FIN_TRABALHO_DIA_REPOUSO",
    "trabalho nos fins de semana": "FIN_TRABALHO_FINS_SEMANA",
    "trabalho em fins de semana": "FIN_TRABALHO_FINS_SEMANA",
    "penalidade": "FIN_PENALIDADE",
    "participação nos lucros e resultados": "FIN_PLR",
    "participação nos lucros ou resultados": "FIN_PLR",
    "plr": "FIN_PLR",
    "processamento de consignações": "FIN_CONSIGNACOES",
    "processamento de consignação em folha": "FIN_CONSIGNACOES",
    "indenização por morte ou invalidez": "FIN_INDENIZACAO_MORTE_INVALIDEZ",
    "multas de trânsito": "FIN_MULTAS_TRANSITO",
    "ajuda de custo na transferência": "FIN_AJUDA_CUSTO_TRANSFERENCIA",
    "adicional de atividade distribuição e coleta": "FIN_AADC",
    "adicional de atividade de distribuição e coleta": "FIN_AADC",
    "aadc": "FIN_AADC",
    "vale cultura": "FIN_VALE_CULTURA",
    "vale-cultura": "FIN_VALE_CULTURA",
    "vale transporte": "FIN_VALE_TRANSPORTE",
    "vale-transporte": "FIN_VALE_TRANSPORTE",
    "reembolso-creche e reembolso-babá": "FIN_REEMBOLSO_CRECHE_BABA",
    "reembolso creche e reembolso babá": "FIN_REEMBOLSO_CRECHE_BABA",
    "reembolso creche": "FIN_REEMBOLSO_CRECHE_BABA",
    "desconto dos dias não trabalhados": "FIN_DESCONTO_DIAS_GREVE",

    # --- SOCIAIS / SAÚDE ---
    "assistência médica/hospitalar e odontológica": "SOC_ASSISTENCIA_MEDICA",
    "assistência médica/hospitalar/odontológica": "SOC_ASSISTENCIA_MEDICA",
    "assistência médica": "SOC_ASSISTENCIA_MEDICA",
    "plano de saúde dos empregados": "SOC_PLANO_SAUDE",
    "plano de saúde": "SOC_PLANO_SAUDE",
    "atestado de saúde na demissão": "SOC_ATESTADO_SAUDE_DEMISSAO",
    "empregado vivendo com hiv ou aids": "SOC_EMPREGADO_VIVENDO_HIV",
    "empregado vivendo com hiv": "SOC_EMPREGADO_VIVENDO_HIV",
    "empregado inapto para retorno ao trabalho": "SOC_EMPREGADO_INAPTO",
    "empregado inapto": "SOC_EMPREGADO_INAPTO",
    "auxílio para dependentes com deficiência": "SOC_AUXILIO_DEPENDENTES_DEFICIENCIA",
    "auxílio para dependentes": "SOC_AUXILIO_DEPENDENTES_DEFICIENCIA",
    "saúde da mulher": "SOC_SAUDE_MULHER",
    "saúde do empregado": "SOC_SAUDE_EMPREGADO",
    "saúde do(a) empregado(a)": "SOC_SAUDE_EMPREGADO",
    "prevenção de doenças": "CON_PREVENCAO_DOENCAS",
    "licença adoção": "SOC_LICENCA_ADOCAO",
    "licença-adoção": "SOC_LICENCA_ADOCAO",
    "licença maternidade": "SOC_PRORROGACAO_LICENCA_MATERNIDADE",
    "prorrogação da licença maternidade": "SOC_PRORROGACAO_LICENCA_MATERNIDADE",
    "prorrogação da licença-maternidade": "SOC_PRORROGACAO_LICENCA_MATERNIDADE",
    "período de amamentação": "SOC_PERIODO_AMAMENTACAO",
    "acompanhante": "SOC_ACOMPANHANTE",
    "reabilitação profissional": "SOC_REABILITACAO_PROFISSIONAL",
    "transporte noturno": "SOC_TRANSPORTE_NOTURNO",
    "fornecimento de cat/lisa": "SOC_FORNECIMENTO_CAT_LISA",
    "fornecimento de cat": "SOC_FORNECIMENTO_CAT",
    "programa casa própria": "SOC_PROGRAMA_CASA_PROPRIA",
    "enfrentamento à violência contra a mulher": "SOC_ENFRENTAMENTO_VIOLENCIA_MULHER",
    "comissão interna de prevenção de acidentes": "CON_CIPA",
    "cipa": "CON_CIPA",
    "itens de uso e proteção": "CON_ITENS_USO_PROTECAO",
    "itens de proteção no caso de baixa umidade": "CON_PROTECAO_BAIXA_UMIDADE",

    # --- CONDIÇÕES DE TRABALHO ---
    "registro de ponto": "CON_REGISTRO_PONTO",
    "distribuição domiciliária": "CON_DISTRIBUICAO_DOMICILIARIA",
    "averiguação das condições de trabalho": "CON_AVERIGUACAO_CONDICOES",
    "ergonomia na empresa": "CON_ERGONOMIA",
    "jornada de trabalho nas agências": "CON_JORNADA_AGENCIAS",
    "jornada de trabalho nas agências de trabalho": "CON_JORNADA_AGENCIAS",
    "jornada de trabalho nas agências de correios": "CON_JORNADA_AGENCIAS",
    "jornada de trabalho para trabalhadores em terminais computadorizados": "TEC_JORNADA_TERMINAIS",
    "jornada de trabalho para trabalhadores": "TEC_JORNADA_TERMINAIS",
    "inovações tecnológicas": "TEC_INOVACOES",
    "inovações tecnológicas": "PRO_INOVACOES_TECNOLOGICAS",
    "redimensionamento de carga": "CON_REDIMENSIONAMENTO_CARGA",
    "responsabilidade civil em acidente de trânsito": "CON_RESPONSABILIDADE_CIVIL_TRANSITO",
    "responsabilidade civil": "CON_RESPONSABILIDADE_CIVIL_TRANSITO",
    "segurança na empresa": "CON_SEGURANCA_EMPRESA",
    "frota operacional": "CON_FROTA_OPERACIONAL",

    # --- SINDICAIS / DEMOCRACIA ---
    "anistia": "SIN_ANISTIA",
    "acesso às dependências": "SIN_ACESSO_DEPENDENCIAS",
    "desconto assistencial": "SIN_DESCONTO_ASSISTENCIAL",
    "fornecimento de documentos": "SIN_FORNECIMENTO_DOCUMENTOS",
    "fornecimento de manual": "SIN_FORNECIMENTO_MANUAL",
    "liberação de conselheiro(a) do postalis": "SIN_LIBERACAO_CONSELHO_POSTALIS",
    "liberação de conselheiro do postalis": "SIN_LIBERACAO_CONSELHO_POSTALIS",
    "liberação de conselheiros da postalis": "SIN_LIBERACAO_CONSELHO_POSTALIS",
    "liberação de dirigentes sindicais": "SIN_LIBERACAO_DIRIGENTES",
    "repasse das mensalidades do sindicato": "SIN_REPASSE_MENSALIDADES",
    "representantes dos empregados": "SIN_REPRESENTANTES_EMPREGADOS",
    "representantes dos(as) empregados(as)": "SIN_REPRESENTANTES_EMPREGADOS",
    "quadro de avisos": "SIN_QUADRO_AVISOS",
    "valorização da diversidade humana": "SIN_DIVERSIDADE",
    "valorização da diversidade": "SIN_DIVERSIDADE",
    "promoção da equidade racial": "SIN_EQUIDADE_RACIAL",
    "promoção da equidade de gênero": "SIN_EQUIDADE_GENERO",
    "assédio sexual e assédio moral": "SOC_ASSEDIO_SEXUAL_MORAL",
    "assédio sexual e moral": "SOC_ASSEDIO_SEXUAL_MORAL",
    "garantias ao empregado estudante": "SIN_EMPREGADO_ESTUDANTE",
    "garantia ao empregado estudante": "SIN_EMPREGADO_ESTUDANTE",
    "empregado estudante": "SIN_EMPREGADO_ESTUDANTE",
    "aposentados(as)": "SIN_APOSENTADOS",
    "aposentados": "SIN_APOSENTADOS",

    # --- PRO / TRABALHO ---
    "concurso público": "PRO_CONCURSO_PUBLICO",
    "direito à ampla defesa": "PRO_AMPLA_DEFESA",
    "direito a ampla defesa": "PRO_AMPLA_DEFESA",
    "negociação coletiva": "PRO_NEGOCIACAO_COLETIVA",
    "processo permanente de negociação": "PRO_PROCESSO_PERMANENTE_NEGOCIACAO",
    "processo permanente": "PRO_PROCESSO_PERMANENTE",
    "conciliação de divergências": "PRO_CONCILIACAO_DIVERGENCIAS",
    "conciliação de divergência": "PRO_CONCILIACAO_DIVERGENCIAS",
    "prorrogação, revisão, denúncia ou revogação": "PRO_PRORROGACAO_REVISAO_DENUNCIA",
    "prorrogação, revisão, denúncia ou revogação": "PRO_PRORROGACAO_REVISAO",
    "cursos e reuniões obrigatórias": "PRO_CURSOS_REUNIOES_OBRIGATORIAS",
    "acompanhamento do cumprimento de cláusulas": "PRO_ACOMPANHAMENTO_CUMPRIMENTO",
    "acompanhamento do cumprimento": "PRO_ACOMPANHAMENTO_CUMPRIMENTO",

    # --- OUTROS ---
    "vigência": "PRO_VIGENCIA",
}


# ================================================================
# UTILITÁRIOS
# ================================================================

def normalizar(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.lower()
    txt = unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode()
    txt = re.sub(r"[^\w\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def similaridade(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def extrair_texto(caminho: Path) -> str:
    partes = []
    with pdfplumber.open(caminho) as pdf:
        for i, pagina in enumerate(pdf.pages):
            txt = pagina.extract_text() or ""
            partes.append(f"\n--- PAGINA {i+1} ---\n{txt}")
    return "\n".join(partes)


def limpar(txt: str) -> str:
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"-\n(\w)", r"\1", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt


# ================================================================
# DETECÇÃO DE CLÁUSULAS
# ================================================================

PADROES = [
    re.compile(r"^\s*(\d{1,3})\s*[ªº]\s*[\)\-]\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,150})$", re.MULTILINE),
    re.compile(r"^\s*Cl[áa]usula\s+(\d{1,3})\s*[-–]\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,150})$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*(\d{1,3})\.\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s\-/]{4,100})$", re.MULTILINE),
]


def separar_titulo(texto_completo: str) -> str:
    """Corta o título antes do '–' ou '-' seguido de espaço."""
    # Padrão: "TITULO – corpo..." ou "TITULO - corpo..."
    m = re.match(r"^([^–\-]{3,120}?)\s+[–\-]\s+", texto_completo)
    if m:
        return m.group(1).strip()
    # Se não tem separador, pega os primeiros 120 chars
    return texto_completo[:120].strip()


def detectar_clausulas(texto: str) -> list:
    clausulas = []
    for padrao in PADROES:
        for match in padrao.finditer(texto):
            numero = int(match.group(1))
            titulo_completo = match.group(2).strip()

            # Corta título antes do separador
            titulo = separar_titulo(titulo_completo)

            clausulas.append({
                "numero": numero,
                "titulo": titulo,
                "titulo_completo": titulo_completo[:200],
                "inicio": match.start(),
                "fim": match.end(),
            })

    # Deduplica por numero
    vistos = {}
    for c in clausulas:
        if c["numero"] not in vistos:
            vistos[c["numero"]] = c

    return sorted(vistos.values(), key=lambda x: x["inicio"])


def extrair_corpo(texto: str, clausulas: list) -> list:
    for i, c in enumerate(clausulas):
        inicio_corpo = c["fim"]
        if i + 1 < len(clausulas):
            fim_corpo = clausulas[i + 1]["inicio"]
        else:
            fim_corpo = min(inicio_corpo + 2000, len(texto))

        corpo = texto[inicio_corpo:fim_corpo].strip()
        corpo = re.sub(r"Assinado eletronicamente[^\n]*", "", corpo)
        corpo = re.sub(r"Juntado em:[^\n]*", "", corpo)
        corpo = re.sub(r"--- PAGINA \d+ ---", "", corpo)
        corpo = re.sub(r"\s+", " ", corpo).strip()
        c["texto"] = corpo[:2500]

    return clausulas


# ================================================================
# MAPEAMENTO DE IDs
# ================================================================

def mapear_id(titulo: str, ref_ids: dict) -> tuple:
    """Tenta mapear o título para um ID canônico. Retorna (id, fonte)."""
    titulo_norm = titulo.lower().strip()

    # 1. Match direto no dicionário
    if titulo_norm in MAPA_TITULOS:
        return MAPA_TITULOS[titulo_norm], "dicionario_exato"

    # 2. Match por substring no dicionário (mais longo primeiro)
    for chave, cid in sorted(MAPA_TITULOS.items(), key=lambda x: -len(x[0])):
        if chave in titulo_norm:
            return cid, "dicionario_substring"

    # 3. Match por similaridade com IDs existentes
    if ref_ids:
        tit_norm2 = normalizar(titulo)
        melhor_id = None
        melhor_score = 0.0
        for cid, tit_ref in ref_ids.items():
            score = similaridade(tit_norm2, normalizar(tit_ref))
            if score > melhor_score:
                melhor_score = score
                melhor_id = cid
        if melhor_score >= 0.65:
            return melhor_id, f"similaridade_{melhor_score:.2f}"

    # 4. Fallback — gera ID genérico
    return None, "nao_encontrado"


def gerar_id_generico(titulo: str) -> str:
    """Gera ID temporário para revisão."""
    t = unicodedata.normalize("NFKD", titulo)
    t = t.encode("ASCII", "ignore").decode()
    t = re.sub(r"[^\w\s]", "", t).upper()
    partes = t.split()[:5]
    return "GEN_" + "_".join(partes)[:70]


def carregar_ids_referencia(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    try:
        doc = json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        c.get("id_canonico"): c.get("titulo_original")
        for c in doc.get("clausulas", [])
        if c.get("id_canonico") and c.get("titulo_original")
    }


# ================================================================
# PROCESSAMENTO
# ================================================================

def processar(alvo: dict):
    print()
    print("=" * 100)
    print(f"PROCESSANDO: {alvo['pdf'].name}")
    print("=" * 100)

    if not alvo["pdf"].exists():
        print(f"  [ERRO] PDF não encontrado")
        return None

    # 1. Extrai texto
    print("  [1/4] Extraindo texto...")
    texto = limpar(extrair_texto(alvo["pdf"]))
    print(f"        {len(texto):,} chars")

    # 2. Detecta cláusulas
    print("  [2/4] Detectando cláusulas...")
    clausulas = detectar_clausulas(texto)
    print(f"        {len(clausulas)} cláusulas detectadas")

    if not clausulas:
        print("        [AVISO] Nenhuma cláusula detectada.")
        return None

    # 3. Extrai corpo
    print("  [3/4] Extraindo corpo...")
    clausulas = extrair_corpo(texto, clausulas)

    # 4. Mapeia IDs
    print("  [4/4] Mapeando IDs...")
    ref_ids = carregar_ids_referencia(alvo["referencia"])
    print(f"        {len(ref_ids)} IDs em {alvo['referencia'].name}")

    contadores = {"dicionario_exato": 0, "dicionario_substring": 0,
                  "similaridade": 0, "generico": 0}
    nao_mapeados = []

    for c in clausulas:
        cid, fonte = mapear_id(c["titulo"], ref_ids)

        if cid:
            c["id_canonico"] = cid
            if fonte.startswith("similaridade"):
                contadores["similaridade"] += 1
            elif fonte == "dicionario_exato":
                contadores["dicionario_exato"] += 1
            else:
                contadores["dicionario_substring"] += 1
        else:
            c["id_canonico"] = gerar_id_generico(c["titulo"])
            c["novo"] = True
            contadores["generico"] += 1
            nao_mapeados.append((c["numero"], c["titulo"]))

    print(f"        Mapeamento:")
    print(f"          Dicionário (exato):     {contadores['dicionario_exato']}")
    print(f"          Dicionário (substring): {contadores['dicionario_substring']}")
    print(f"          Similaridade:           {contadores['similaridade']}")
    print(f"          Genéricos (revisar):    {contadores['generico']}")

    if nao_mapeados:
        print(f"\n        NÃO MAPEADOS ({len(nao_mapeados)}):")
        for num, tit in nao_mapeados[:15]:
            print(f"          [{num:3}] {tit[:70]}")
        if len(nao_mapeados) > 15:
            print(f"          ... (+{len(nao_mapeados) - 15})")

    # Gera JSON
    saida = {
        "metadados_documento": {
            "tipo": alvo["tipo"],
            "ano_inicio": alvo["ano_ini"],
            "ano_fim": alvo["ano_fim"],
            "processo": None,
            "tribunal": "TST",
            "orgao": None,
            "relator": None,
            "data_julgamento": None,
            "data_publicacao": None,
            "data_assinatura": None,
            "entidade_patronal": "ECT",
            "entidades_profissionais": ["FENTECT", "FINDECT"],
            "arquivo_origem": alvo["pdf"].name,
            "grupo": f"{alvo['ano_ini']}-{alvo['ano_fim']}",
            "papel": "FENTECT",
            "observacao": (
                f"Re-extraído automaticamente em {datetime.now().strftime('%Y-%m-%d')}. "
                f"{len(clausulas)} cláusulas detectadas. "
                f"Mapeamento: {contadores['dicionario_exato']} exato + "
                f"{contadores['dicionario_substring']} substring + "
                f"{contadores['similaridade']} similaridade + "
                f"{contadores['generico']} genéricos (revisar)."
            ),
        },
        "clausulas": [],
        "notas_metodologicas": [
            {
                "tipo": "REEXTRACAO",
                "descricao": (
                    f"Documento re-extraído de {alvo['pdf'].name} via pdfplumber (v2). "
                    f"Título cortado antes do separador '–'. "
                    f"Mapeamento por dicionário de 70+ keywords + similaridade fallback."
                ),
            }
        ],
    }

    for c in clausulas:
        saida["clausulas"].append({
            "id_canonico": c["id_canonico"],
            "numero_clausula_original": c["numero"],
            "titulo_original": c["titulo"],
            "status": "MANTIDO",
            "texto": c.get("texto", ""),
            "novo_id": c.get("novo", False),
        })

    alvo["json_saida"].write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n  [OK] Salvo: {alvo['json_saida'].name}")
    return {
        "pdf": alvo["pdf"].name,
        "clausulas": len(clausulas),
        "exato": contadores["dicionario_exato"],
        "substring": contadores["dicionario_substring"],
        "similaridade": contadores["similaridade"],
        "generico": contadores["generico"],
        "nao_mapeados": nao_mapeados,
    }


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 100)
    print("RE-EXTRAÇÃO V2 — DC 2019-2021 E DC 2020-2021")
    print("=" * 100)

    resultados = []
    for alvo in ALVOS:
        r = processar(alvo)
        if r:
            resultados.append(r)

    print()
    print("=" * 100)
    print("RESUMO")
    print("=" * 100)
    print(f"{'PDF':<35} {'Cláus':>6} {'Exato':>6} {'Substr':>7} {'Simil':>6} {'Genér':>6}")
    print("-" * 100)
    for r in resultados:
        print(f"{r['pdf'][:33]:<35} {r['clausulas']:>6} {r['exato']:>6} "
              f"{r['substring']:>7} {r['similaridade']:>6} {r['generico']:>6}")

    total_gen = sum(r["generico"] for r in resultados)
    if total_gen:
        print(f"\n⚠️  {total_gen} cláusulas com ID genérico — revisar e adicionar")
        print(f"   ao dicionário MAPA_TITULOS para re-rodar.")


if __name__ == "__main__":
    main()