"""
Busca valores de VA/VR/VC nos OCRs de 1995-2004 (período fragmentado).

Uso no Spyder:
    F5
"""
import re
from pathlib import Path


PASTA_OCR = Path(r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados\export")

# Anos que queremos investigar
ANOS_FOCO = [1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004]

# Keywords mais específicas
KEYWORDS = [
    "vale alimentação", "vale-alimentação", "vale alimentacao",
    "vale refeição", "vale-refeição", "vale refeicao",
    "vale cesta", "vale-cesta",
    "vale refeição/alimentação",
    "auxílio alimentação", "auxilio alimentacao",
    "cesta básica", "cesta basica",
    "ticket alimentação",
    "ticket refeição",
    "valor facial",
    "vale-transporte",
    "alimentação", "alimentacao",
    "refeição", "refeicao",
]

REGEX_RS = re.compile(r"R\$\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|[\d]{1,3},\d{2})")
REGEX_QTD = re.compile(r"(\d{2})\s*\([^)]*\)\s*(?:vales|tickets)", re.IGNORECASE)


def extrair_ano(nome_arquivo: str):
    m = re.search(r"(\d{4})(?:-(\d{4}))?", nome_arquivo)
    if not m:
        return None
    return int(m.group(1))


def buscar_no_txt(caminho: Path):
    """Lê um arquivo OCR e retorna todas as menções com contexto."""
    try:
        texto = caminho.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return []

    # Corrige encoding (Tesseract salvou cp1252 mas conteúdo é utf-8)
    try:
        texto = texto.encode("cp1252", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        pass

    resultados = []
    linhas = texto.split("\n")

    for i, linha in enumerate(linhas):
        linha_lower = linha.lower()
        for kw in KEYWORDS:
            if kw.lower() in linha_lower:
                # Contexto de 5 linhas (antes e depois)
                ini = max(0, i - 2)
                fim = min(len(linhas), i + 6)
                contexto = " ".join(linhas[ini:fim])
                contexto = re.sub(r"\s+", " ", contexto).strip()

                valores = REGEX_RS.findall(contexto)
                qtds = REGEX_QTD.findall(contexto)

                resultados.append({
                    "linha": i + 1,
                    "keyword": kw,
                    "contexto": contexto[:600],
                    "valores": ["R$ " + v for v in valores],
                    "quantidades": qtds,
                })
                break

    return resultados


def main():
    print("=" * 100)
    print("BUSCA -- VA/VR/VC EM 1995-2004 (via OCR)")
    print("=" * 100)

    # Lista arquivos OCR
    arquivos = sorted(PASTA_OCR.glob("ocr_txt_Acordo-Coletivo-*.txt"))

    for arq in arquivos:
        ano = extrair_ano(arq.name)
        if not ano or ano not in ANOS_FOCO:
            continue

        print()
        print("=" * 100)
        print(f"ARQUIVO: {arq.name}")
        print("=" * 100)

        achados = buscar_no_txt(arq)

        if not achados:
            print("  (nenhuma menção encontrada)")
            continue

        # Deduplica
        vistos = set()
        for a in achados:
            chave = a["contexto"][:100]
            if chave in vistos:
                continue
            vistos.add(chave)

            print(f"\n  Linha {a['linha']} [{a['keyword']}]")
            if a["valores"]:
                print(f"    VALORES: {' | '.join(a['valores'])}")
            if a["quantidades"]:
                print(f"    QTD: {' | '.join(a['quantidades'])}")
            print(f"    CONTEXTO: {a['contexto'][:400]}")
            print()

    # Resumo de valores únicos
    print()
    print("=" * 100)
    print("RESUMO -- TODOS OS VALORES ENCONTRADOS")
    print("=" * 100)

    todos_valores = {}
    for arq in arquivos:
        ano = extrair_ano(arq.name)
        if not ano or ano not in ANOS_FOCO:
            continue

        achados = buscar_no_txt(arq)
        for a in achados:
            for v in a["valores"]:
                todos_valores.setdefault(ano, set()).add(v)

    for ano in sorted(todos_valores.keys()):
        valores = sorted(todos_valores[ano])
        print(f"\n  ANO {ano}:")
        for v in valores:
            print(f"    {v}")


if __name__ == "__main__":
    main()