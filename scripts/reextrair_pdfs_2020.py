"""
Re-extrai os PDFs ACT 2019-2021 e Acórdão 2020-2021 com mapeamento
de IDs canônicos por similaridade.

Objetivo: gerar JSONs completos (79 e 29 cláusulas) para corrigir
a base que hoje tem 77 e 16.

Uso no Spyder:
    F5 (Run file)
"""
import json
import re
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    print("[ERRO] pdfplumber nao instalado. Rode: pip install pdfplumber")
    raise


RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
DADOS_DIR = RAIZ / "dados"
PASTA_SAIDA = RAIZ / "dados" / "export"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

# ================================================================
# PDFs para re-extrair
# ================================================================

ALVOS = [
    {
        "pdf": DADOS_DIR / "Acordao-2019-2021.pdf",
        "json_saida": DATA_DIR / "DC 2019-2021.json",
        "referencia": DATA_DIR / "ACT 2018-2019.json",
        "esperado_min": 70,
        "esperado_max": 95,
    },
    {
        "pdf": DADOS_DIR / "Acordao-2020-2021.pdf",
        "json_saida": DATA_DIR / "DC 2020-2021.json",
        "referencia": DATA_DIR / "DC 2020-2021.json",
        "esperado_min": 25,
        "esperado_max": 35,
    },
]


# ================================================================
# EXTRAÇÃO DE TEXTO
# ================================================================

def extrair_texto(caminho: Path) -> str:
    """Extrai texto completo do PDF."""
    partes = []
    with pdfplumber.open(caminho) as pdf:
        for i, pagina in enumerate(pdf.pages):
            txt = pagina.extract_text() or ""
            partes.append(f"\n--- PAGINA {i+1} ---\n{txt}")
    return "\n".join(partes)


def limpar(txt: str) -> str:
    """Normaliza espaços e quebras."""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    # Remove hifenização de fim de linha
    txt = re.sub(r"-\n(\w)", r"\1", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt


# ================================================================
# DETECÇÃO DE CLÁUSULAS
# ================================================================

# Padrões testados em ACTs/DCs dos Correios:
#   "1ª) REAJUSTE SALARIAL"
#   "1ª - REAJUSTE SALARIAL"
#   "Cláusula 1 - REAJUSTE"
#   "1. REAJUSTE SALARIAL"
PADROES = [
    re.compile(r"^\s*(\d{1,3})\s*[ªº]\s*[\)\-]\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,120})$", re.MULTILINE),
    re.compile(r"^\s*Cl[áa]usula\s+(\d{1,3})\s*[-–]\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,120})$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*(\d{1,3})\.\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s\-/]{4,80})$", re.MULTILINE),
]


def detectar_clausulas(texto: str) -> list:
    """Detecta blocos de cláusulas no texto."""
    clausulas = []

    # Junta todos os padrões
    for padrao in PADROES:
        for match in padrao.finditer(texto):
            numero = int(match.group(1))
            titulo = match.group(2).strip()
            titulo = re.sub(r"\s+", " ", titulo)

            # Limita tamanho do título
            if len(titulo) > 100:
                titulo = titulo[:100]

            clausulas.append({
                "numero": numero,
                "titulo": titulo,
                "inicio": match.start(),
                "fim": match.end(),
                "padrao": padrao.pattern[:40],
            })

    # Deduplica por numero, mantendo primeiro
    vistos = {}
    for c in clausulas:
        if c["numero"] not in vistos:
            vistos[c["numero"]] = c

    resultado = sorted(vistos.values(), key=lambda x: x["inicio"])
    return resultado


def extrair_corpo(texto: str, clausulas: list) -> list:
    """Extrai o corpo entre cada cláusula."""
    for i, c in enumerate(clausulas):
        inicio_corpo = c["fim"]
        if i + 1 < len(clausulas):
            fim_corpo = clausulas[i + 1]["inicio"]
        else:
            fim_corpo = min(inicio_corpo + 2000, len(texto))

        corpo = texto[inicio_corpo:fim_corpo].strip()
        # Limpa cabeçalhos/rodapés
        corpo = re.sub(r"Assinado eletronicamente[^\n]*", "", corpo)
        corpo = re.sub(r"Juntado em:[^\n]*", "", corpo)
        corpo = re.sub(r"--- PAGINA \d+ ---", "", corpo)
        corpo = re.sub(r"\s+", " ", corpo).strip()
        c["texto"] = corpo[:2500]

    return clausulas


# ================================================================
# MAPEAMENTO DE IDs CANÔNICOS POR SIMILARIDADE
# ================================================================

def normalizar(txt: str) -> str:
    """Normaliza título para comparação."""
    if not txt:
        return ""
    txt = txt.lower()
    txt = re.sub(r"[^\w\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def similaridade(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def carregar_ids_referencia(caminho: Path) -> dict:
    """Carrega {id_canonico: titulo_original} de um JSON existente."""
    if not caminho.exists():
        return {}

    try:
        doc = json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return {}

    ref = {}
    for c in doc.get("clausulas", []):
        cid = c.get("id_canonico")
        tit = c.get("titulo_original")
        if cid and tit:
            ref[cid] = tit
    return ref


def mapear_id(titulo: str, ref_ids: dict, limiar: float = 0.55) -> tuple:
    """Retorna (id_canonico, score) mais similar ao título."""
    if not ref_ids or not titulo:
        return None, 0.0

    tit_norm = normalizar(titulo)
    melhor_id = None
    melhor_score = 0.0

    for cid, tit_ref in ref_ids.items():
        score = similaridade(tit_norm, normalizar(tit_ref))
        if score > melhor_score:
            melhor_score = score
            melhor_id = cid

    if melhor_score >= limiar:
        return melhor_id, melhor_score

    return None, melhor_score


def sugerir_novo_id(titulo: str) -> str:
    """Gera um ID heurístico quando não encontra match."""
    # Remove acentos
    import unicodedata
    titulo_sem_acento = unicodedata.normalize("NFKD", titulo)
    titulo_sem_acento = titulo_sem_acento.encode("ASCII", "ignore").decode()
    titulo_sem_acento = re.sub(r"[^\w\s]", "", titulo_sem_acento).upper()
    partes = titulo_sem_acento.split()[:4]
    return "GEN_" + "_".join(partes)[:60]


# ================================================================
# PROCESSAMENTO
# ================================================================

def processar(alvo: dict):
    print()
    print("=" * 100)
    print(f"PROCESSANDO: {alvo['pdf'].name}")
    print("=" * 100)

    if not alvo["pdf"].exists():
        print(f"  [ERRO] PDF não encontrado: {alvo['pdf']}")
        return None

    # 1. Extrai texto
    print("  [1/4] Extraindo texto do PDF...")
    texto = limpar(extrair_texto(alvo["pdf"]))
    print(f"        {len(texto):,} caracteres extraídos")

    # 2. Detecta cláusulas
    print("  [2/4] Detectando cláusulas...")
    clausulas = detectar_clausulas(texto)
    print(f"        {len(clausulas)} cláusulas detectadas")

    if not clausulas:
        print("        [AVISO] Nenhuma cláusula detectada. Verifique o PDF.")
        return None

    # 3. Extrai corpo
    print("  [3/4] Extraindo corpo das cláusulas...")
    clausulas = extrair_corpo(texto, clausulas)

    # 4. Mapeia IDs
    print("  [4/4] Mapeando IDs canônicos...")
    ref_ids = carregar_ids_referencia(alvo["referencia"])
    print(f"        {len(ref_ids)} IDs de referência em {alvo['referencia'].name}")

    mapeados = 0
    nao_mapeados = []
    for c in clausulas:
        cid, score = mapear_id(c["titulo"], ref_ids)
        c["score_similaridade"] = round(score, 3)

        if cid:
            c["id_canonico"] = cid
            mapeados += 1
        else:
            c["id_canonico"] = sugerir_novo_id(c["titulo"])
            c["novo"] = True
            nao_mapeados.append({
                "numero": c["numero"],
                "titulo": c["titulo"],
                "sugerido": c["id_canonico"],
                "score": score,
            })

    print(f"        Mapeados: {mapeados}/{len(clausulas)}")
    if nao_mapeados:
        print(f"        NÃO mapeados: {len(nao_mapeados)}")
        for nm in nao_mapeados[:10]:
            print(f"          [{nm['numero']:3}] {nm['titulo'][:60]:60} (score {nm['score']:.2f})")
        if len(nao_mapeados) > 10:
            print(f"          ... (+{len(nao_mapeados) - 10})")

    # Gera JSON
    ano_ini = None
    m = re.search(r"(\d{4})", alvo["json_saida"].name)
    if m:
        ano_ini = int(m.group(1))

    saida = {
        "metadados_documento": {
            "tipo": "DC" if "DC" in alvo["json_saida"].name else "ACT",
            "ano_inicio": ano_ini,
            "ano_fim": (ano_ini + 1) if ano_ini else None,
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
            "grupo": f"{ano_ini}-{ano_ini+1}" if ano_ini else None,
            "papel": "FENTECT",
            "observacao": (
                f"Re-extraído automaticamente em {datetime.now().strftime('%Y-%m-%d')}. "
                f"{len(clausulas)} cláusulas detectadas. "
                f"{mapeados} mapeadas para IDs canônicos existentes, "
                f"{len(nao_mapeados)} receberam IDs novos (prefixo GEN_)."
            ),
        },
        "clausulas": [],
        "notas_metodologicas": [
            {
                "tipo": "REEXTRACAO",
                "descricao": (
                    f"Documento re-extraído de {alvo['pdf'].name} via pdfplumber. "
                    f"Mapeamento automático por similaridade de título (limiar 0.55). "
                    f"IDs não encontrados receberam sufixo GEN_ para revisão manual."
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
            "score_similaridade": c.get("score_similaridade", 0),
            "novo_id": c.get("novo", False),
        })

    # Salva
    alvo["json_saida"].write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    esperado_min = alvo["esperado_min"]
    esperado_max = alvo["esperado_max"]
    status = "OK" if esperado_min <= len(clausulas) <= esperado_max else "ATENCAO"

    print(f"  [OK] Salvo: {alvo['json_saida'].name}")
    print(f"       Status: {status} ({len(clausulas)} cláusulas, esperado: {esperado_min}-{esperado_max})")

    return {
        "pdf": alvo["pdf"].name,
        "json_saida": alvo["json_saida"].name,
        "clausulas": len(clausulas),
        "mapeadas": mapeados,
        "nao_mapeadas": len(nao_mapeados),
        "status": status,
    }


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 100)
    print("RE-EXTRAÇÃO DE PDFs — ACT 2019-2021 E DC 2020-2021")
    print("=" * 100)

    resultados = []
    for alvo in ALVOS:
        resultado = processar(alvo)
        if resultado:
            resultados.append(resultado)

    # Resumo
    print()
    print("=" * 100)
    print("RESUMO")
    print("=" * 100)
    print(f"{'PDF':<35} {'JSON':<35} {'Cláus':>6} {'Mapead':>7} {'Novos':>6} {'Status':>8}")
    print("-" * 100)
    for r in resultados:
        print(f"{r['pdf'][:33]:<35} {r['json_saida'][:33]:<35} "
              f"{r['clausulas']:>6} {r['mapeadas']:>7} {r['nao_mapeadas']:>6} "
              f"{r['status']:>8}")

    print()
    print("PRÓXIMOS PASSOS:")
    print("  1. Verificar os JSONs gerados em data/")
    print("  2. Rodar: python scripts/auditar_retirada_2020.py")
    print("  3. Confirmar os números: 79 vs 29 → 50 cláusulas retiradas")


if __name__ == "__main__":
    main()