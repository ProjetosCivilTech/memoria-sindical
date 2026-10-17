"""
Busca valores de VALE ALIMENTAÇÃO, VALE REFEIÇÃO e SALÁRIO-BASE
em todos os PDFs dos ACTs/DCs dos Correios (1988-2026).

Uso no Spyder:
    - Abrir este arquivo
    - F5 (Run file)
    - OU no Console IPython: runfile('caminho/buscar_va_vr_salario.py', wdir='...')

Saída:
    - dados/export/busca_va_vr.csv
    - dados/export/busca_salario_base.csv
    - Relatório no console
"""

# ============================================================
# IMPORTS
# ============================================================

import re
import csv
from pathlib import Path
from datetime import datetime

# Bibliotecas de PDF
try:
    import pdfplumber
    TEM_PDFPLUMBER = True
except ImportError:
    TEM_PDFPLUMBER = False
    print("[AVISO] pdfplumber nao instalado. Rode: pip install pdfplumber")

try:
    from pypdf import PdfReader
    TEM_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        TEM_PYPDF = True
    except ImportError:
        TEM_PYPDF = False
        print("[AVISO] pypdf nao instalado. Rode: pip install pypdf")


# ============================================================
# CONFIGURACAO
# ============================================================

PASTA_PDFS = Path(r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados")
PASTA_SAIDA = PASTA_PDFS / "export"
PASTA_SAIDA.mkdir(exist_ok=True)

# --- Palavras-chave VA / VR ---
KEYWORDS_VA_VR = [
    "vale alimentação",
    "vale-alimentação",
    "vale alimentacao",
    "vale refeição",
    "vale-refeição",
    "vale refeicao",
    "vale cesta",
    "vale-cesta",
    "vale alimentacao e refeicao",
    "ticket alimentação",
    "ticket alimentacao",
    "auxílio alimentação",
    "auxilio alimentacao",
    "auxílio-alimentação",
    "auxílio refeição",
    "cesta básica",
    "cesta basica",
    "vale refeição/alimentação",
]

# --- Palavras-chave SALARIO-BASE ---
KEYWORDS_SALARIO = [
    "salário-base",
    "salario-base",
    "salário base",
    "salario base",
    "piso salarial",
    "salário inicial",
    "salario inicial",
    "vencimento básico",
    "vencimento basico",
    "tabela salarial",
    "salário de ingresso",
    "salario de ingresso",
    "referência inicial",
    "referencia inicial",
    "valor facial",
    "NM-01",
    "NS-01",
    "salário mínimo",
    "salario minimo",
    "salário-mínimo",
]

# --- Regex de valores monetarios ---
# Captura: R$ 1.234,56 | R$1.234,56 | R$ 1234,56 | R$ 123,45
REGEX_RS = re.compile(
    r"R\$\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|[\d]{1,3},\d{2})"
)

# --- Regex de ano a partir do nome do arquivo ---
REGEX_ANO = re.compile(r"(\d{4})(?:-(\d{4}))?")


# ============================================================
# FUNCOES DE EXTRACAO
# ============================================================

def ano_do_nome(nome: str):
    """Extrai (ano_inicio, ano_fim) do nome do arquivo."""
    m = REGEX_ANO.search(nome)
    if not m:
        return (None, None)
    return (int(m.group(1)), int(m.group(2)) if m.group(2) else None)


def extrair_texto_pdfplumber(caminho: Path) -> str:
    """Extrai texto de todas as paginas usando pdfplumber."""
    texto_completo = []
    try:
        with pdfplumber.open(caminho) as pdf:
            for i, pagina in enumerate(pdf.pages):
                try:
                    txt = pagina.extract_text() or ""
                    texto_completo.append(f"\n--- PAGINA {i+1} ---\n{txt}")
                except Exception as e:
                    texto_completo.append(f"\n[ERRO pag {i+1}: {e}]")
        return "\n".join(texto_completo)
    except Exception as e:
        return f"[ERRO pdfplumber: {e}]"


def extrair_texto_pypdf(caminho: Path) -> str:
    """Fallback: extrai texto usando pypdf."""
    texto_completo = []
    try:
        reader = PdfReader(str(caminho))
        for i, pagina in enumerate(reader.pages):
            try:
                txt = pagina.extract_text() or ""
                texto_completo.append(f"\n--- PAGINA {i+1} ---\n{txt}")
            except Exception as e:
                texto_completo.append(f"\n[ERRO pag {i+1}: {e}]")
        return "\n".join(texto_completo)
    except Exception as e:
        return f"[ERRO pypdf: {e}]"


def extrair_texto(caminho: Path) -> str:
    """Tenta pdfplumber, cai para pypdf se necessario."""
    if TEM_PDFPLUMBER:
        txt = extrair_texto_pdfplumber(caminho)
        if txt and "[ERRO pdfplumber" not in txt and len(txt) > 500:
            return txt
    if TEM_PYPDF:
        return extrair_texto_pypdf(caminho)
    return "[ERRO: nenhuma biblioteca de PDF disponivel]"


# ============================================================
# BUSCA POR KEYWORDS
# ============================================================

def limpar_texto(txt: str) -> str:
    """Normaliza espacos e quebras de linha."""
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    return txt


def buscar_keywords(texto: str, keywords: list) -> list:
    """Retorna lista de (keyword, contexto) onde keyword aparece."""
    resultados = []
    linhas = texto.split("\n")

    for i, linha in enumerate(linhas):
        linha_lower = linha.lower()
        for kw in keywords:
            if kw.lower() in linha_lower:
                # Pega contexto: linha anterior + atual + proxima
                ini = max(0, i - 1)
                fim = min(len(linhas), i + 3)
                contexto = " ".join(linhas[ini:fim])
                contexto = re.sub(r"\s+", " ", contexto).strip()

                # Extrai valores R$ do contexto
                valores = REGEX_RS.findall(contexto)

                resultados.append({
                    "keyword": kw,
                    "linha": i + 1,
                    "contexto": contexto[:400],
                    "valores_rs": ["R$ " + v for v in valores],
                })
                break  # nao repete mesma linha para multiplas keywords

    return resultados


# ============================================================
# PROCESSAMENTO PRINCIPAL
# ============================================================

def processar_pdfs():
    """Roda a busca em todos os PDFs e retorna resultados."""
    pdfs = sorted(PASTA_PDFS.glob("*.pdf"))

    print("=" * 100)
    print(f"BUSCA EM {len(pdfs)} PDFs")
    print("=" * 100)

    todos_va_vr = []
    todos_salario = []
    sumario = []

    for idx, pdf in enumerate(pdfs, 1):
        nome = pdf.name
        ano_ini, ano_fim = ano_do_nome(nome)
        ano_str = f"{ano_ini}-{ano_fim}" if ano_fim else str(ano_ini)

        print(f"\n[{idx}/{len(pdfs)}] {nome}  (ano {ano_str})")

        # Extrai texto
        texto = extrair_texto(pdf)
        texto = limpar_texto(texto)

        if "[ERRO" in texto or len(texto) < 200:
            print(f"    [AVISO] Texto extraido muito curto ({len(texto)} chars). "
                  f"PDF pode ser escaneado (imagem).")

        # Busca VA/VR
        achados_va = buscar_keywords(texto, KEYWORDS_VA_VR)
        for a in achados_va:
            a["arquivo"] = nome
            a["ano"] = ano_str
            todos_va_vr.append(a)

        # Busca salario
        achados_sal = buscar_keywords(texto, KEYWORDS_SALARIO)
        for a in achados_sal:
            a["arquivo"] = nome
            a["ano"] = ano_str
            todos_salario.append(a)

        print(f"    VA/VR: {len(achados_va)} mencoes  |  Salario: {len(achados_sal)} mencoes")

        sumario.append({
            "arquivo": nome,
            "ano": ano_str,
            "chars_extraidos": len(texto),
            "mencoes_va_vr": len(achados_va),
            "mencoes_salario": len(achados_sal),
        })

    return todos_va_vr, todos_salario, sumario


# ============================================================
# EXPORTACAO
# ============================================================

def exportar_csv(resultados: list, caminho: Path):
    """Exporta lista de dicts para CSV."""
    if not resultados:
        print(f"    [SKIP] Sem dados para {caminho.name}")
        return

    campos = ["ano", "arquivo", "keyword", "linha", "contexto", "valores_rs"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in resultados:
            linha = r.copy()
            linha["valores_rs"] = " | ".join(linha.get("valores_rs", []))
            writer.writerow({k: linha.get(k, "") for k in campos})

    print(f"    [OK] Salvo: {caminho}  ({len(resultados)} linhas)")


def imprimir_sumario(sumario: list):
    """Imprime tabela resumo."""
    print()
    print("=" * 100)
    print("SUMARIO POR ARQUIVO")
    print("=" * 100)
    print(f"{'Ano':<12} {'Chars':>8} {'VA/VR':>7} {'Salario':>8}   Arquivo")
    print("-" * 100)

    for s in sumario:
        print(f"{s['ano']:<12} {s['chars_extraidos']:>8} "
              f"{s['mencoes_va_vr']:>7} {s['mencoes_salario']:>8}   {s['arquivo'][:55]}")


def imprimir_valores_unicos(resultados: list, titulo: str):
    """Imprime valores R$ unicos encontrados."""
    print()
    print("=" * 100)
    print(titulo)
    print("=" * 100)

    # Agrupa por ano
    por_ano = {}
    for r in resultados:
        ano = r["ano"] or "?"
        por_ano.setdefault(ano, set())
        for v in r.get("valores_rs", []):
            por_ano[ano].add(v)

    for ano in sorted(por_ano.keys(), key=lambda x: str(x)):
        valores = sorted(por_ano[ano])
        if valores:
            print(f"\n  ANO {ano}:")
            for v in valores[:20]:
                print(f"    {v}")
            if len(valores) > 20:
                print(f"    ... (+{len(valores) - 20} valores)")


# ============================================================
# MAIN
# ============================================================

def main():
    inicio = datetime.now()

    todos_va_vr, todos_salario, sumario = processar_pdfs()

    # Sumario
    imprimir_sumario(sumario)

    # Exportar
    print()
    print("=" * 100)
    print("EXPORTANDO")
    print("=" * 100)

    exportar_csv(todos_va_vr, PASTA_SAIDA / "busca_va_vr.csv")
    exportar_csv(todos_salario, PASTA_SAIDA / "busca_salario_base.csv")

    # Resumo de valores
    imprimir_valores_unicos(todos_va_vr, "VALORES R$ ENCONTRADOS -- VA/VR")
    imprimir_valores_unicos(todos_salario, "VALORES R$ ENCONTRADOS -- SALARIO-BASE")

    # Totais
    print()
    print("=" * 100)
    print("RESUMO FINAL")
    print("=" * 100)
    print(f"  VA/VR:      {len(todos_va_vr)} mencoes totais")
    print(f"  Salario:    {len(todos_salario)} mencoes totais")
    print(f"  Tempo:      {(datetime.now() - inicio).total_seconds():.1f}s")
    print(f"  Saida:      {PASTA_SAIDA}")
    print("=" * 100)


if __name__ == "__main__":
    main()