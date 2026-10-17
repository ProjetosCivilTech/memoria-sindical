"""
OCR nos PDFs escaneados dos ACTs/DCs dos Correios.

Extrai:
  - Valores de VA / VR / Vale Cesta / Auxílio-Alimentação
  - Percentuais de desconto (participação do empregado)
  - Salário-base / piso salarial

Saída:
  - dados/export/ocr_beneficios.csv
  - dados/export/ocr_salario_base.csv
  - dados/export/ocr_relatorio.txt

Uso no Spyder:
    F5 (Run file)
"""

# ============================================================
# CONFIGURACAO
# ============================================================

# >>> AJUSTE AQUI SE INSTALOU EM OUTRO LUGAR <<<
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PASTA_PDFS = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados"
PASTA_SAIDA = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados\export"

# DPI para renderizacao (200 = bom; 300 = melhor mas 2x lento)
DPI = 250

# Idioma do OCR
IDIOMA = "por"

# ============================================================

import os
import re
import csv
import time
from pathlib import Path
from datetime import datetime

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except ImportError:
    print("[ERRO] pytesseract nao instalado. Rode: pip install pytesseract")
    raise

try:
    import fitz  # PyMuPDF
except ImportError:
    print("[ERRO] pymupdf nao instalado. Rode: pip install pymupdf")
    raise

from PIL import Image
import io


PASTA_PDFS = Path(PASTA_PDFS)
PASTA_SAIDA = Path(PASTA_SAIDA)
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)


# ============================================================
# LISTA DE PDFs PARA OCR (só os escaneados)
# ============================================================

# Todos que extrairam < 500 chars no script anterior
PDFS_ESCANEADOS = [
    "Acordo-Coletivo-1988_red.pdf",
    "Acordo-Coletivo-1989.pdf",
    "Acordo-Coletivo-1990-Suplementar.pdf",
    "Acordo-Coletivo-1990_red.pdf",
    "Acordo-Coletivo-1991-parcial.pdf",
    "Acordo-Coletivo-1992_red.pdf",
    "Acordo-Coletivo-1993_red.pdf",
    "Acordo-coletivo-1994-1995.pdf",
    "Acordo-Coletivo-1995-1996-Aditamento.pdf",
    "Acordo-Coletivo-1995-1996.pdf",
    "Acordo-Coletivo-1997-1998.pdf",
    "Acordo-Coletivo-1998-1999.pdf",
    "Acordo-Coletivo-1999-2000.pdf",
    "Acordo-Coletivo-2000-2001.pdf",
    "Acordo-Coletivo-2001-2002_redP1.pdf",
    "Acordo-Coletivo-2001-2002_redp2.pdf",
    "Acordo-Coletivo-2002-2003.pdf",
    "Acordo-Coletivo-2003-2004_redP1.pdf",
    "Acordo-Coletivo-2003-2004_redp2.pdf",
    "Acordo-Coletivo-2003-2004_redp3.pdf",
    "Acordo-Coletivo-2004-2005_P1.pdf",
    "Acordo-Coletivo-2004-2005_p2.pdf",
    "Acordo-Coletivo-2005-2006_red.pdf",
    "Acordo-Coletivo-2007-2008_redp1.pdf",
    "Acordo-Coletivo-2007-2008_redp2.pdf",
    "Acordo-Coletivo-2008-2009-Complem-Ata-do-dia-13.10.2008.pdf",
    "Acordo-Coletivo-2008-2009-Complem-Ata-do-dia-14.10.2008.pdf",
    "Acordo-Coletivo-2008-2009-Minuta-do-ACT-2008-2009_red.pdf",
    "Acordo-Coletivo-2009-2011_redp1.pdf",
    "Acordo-Coletivo-2009-2011_redp2.pdf",
    "Acordo-Coletivo-2013-2014-FINDECT_red.pdf",
    "Acordo-Coletivo-2013-2014-Sindicatos-Unificados.pdf",
    "ACT-2015-2016-Assinado-no-TST-Gabriel-2.pdf",
    "ACT-2016-2017-Assinado.pdf",
    "acordo-coletivo-2017-2018.pdf",
]


# ============================================================
# KEYWORDS
# ============================================================

KW_BENEFICIOS = [
    "vale alimentação", "vale-alimentação", "vale alimentacao",
    "vale refeição", "vale-refeição", "vale refeicao",
    "vale cesta", "vale-cesta",
    "vale refeição/alimentação",
    "auxílio alimentação", "auxilio alimentacao",
    "auxílio-alimentação",
    "auxílio refeição",
    "cesta básica", "cesta basica",
    "ticket alimentação",
    "participação", "participacao", "compartilhamento",
    "desconto", "custeio",
]

KW_SALARIO = [
    "salário-base", "salario-base", "salário base", "salario base",
    "piso salarial", "salário inicial", "salario inicial",
    "vencimento básico", "vencimento basico",
    "tabela salarial",
    "salário de ingresso",
    "NM-01", "NS-01",
    "salário mínimo", "salario minimo",
    "salário-mínimo",
    "R$",
]

# Regex valores
REGEX_RS = re.compile(
    r"R\$\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|[\d]{1,3},\d{2})"
)
REGEX_PCT = re.compile(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%")


# ============================================================
# OCR
# ============================================================

def pdf_para_imagens(caminho_pdf: Path, dpi: int = 250):
    """Renderiza cada pagina do PDF como imagem."""
    imagens = []
    try:
        doc = fitz.open(str(caminho_pdf))
        for i, pagina in enumerate(doc):
            try:
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = pagina.get_pixmap(matrix=mat, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                imagens.append((i + 1, img))
            except Exception as e:
                print(f"      [ERRO pag {i+1}]: {e}")
        doc.close()
    except Exception as e:
        print(f"      [ERRO abrir PDF]: {e}")
    return imagens


def ocr_imagem(img: Image.Image, lang: str = "por") -> str:
    """Aplica OCR em uma imagem."""
    try:
        return pytesseract.image_to_string(img, lang=lang)
    except Exception as e:
        return f"[ERRO OCR: {e}]"


# ============================================================
# BUSCA
# ============================================================

def limpar_texto(txt: str) -> str:
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    return txt


def buscar(texto: str, keywords: list, contexto_linhas: int = 3) -> list:
    resultados = []
    linhas = texto.split("\n")

    for i, linha in enumerate(linhas):
        linha_lower = linha.lower()
        for kw in keywords:
            if kw.lower() in linha_lower:
                ini = max(0, i - 1)
                fim = min(len(linhas), i + contexto_linhas)
                contexto = " ".join(linhas[ini:fim])
                contexto = re.sub(r"\s+", " ", contexto).strip()

                valores = REGEX_RS.findall(contexto)
                percentuais = REGEX_PCT.findall(contexto)

                resultados.append({
                    "keyword": kw,
                    "linha": i + 1,
                    "contexto": contexto[:500],
                    "valores_rs": ["R$ " + v for v in valores],
                    "percentuais": [p + "%" for p in percentuais],
                })
                break

    return resultados


def ano_do_nome(nome: str):
    m = re.search(r"(\d{4})(?:-(\d{4}))?", nome)
    if not m:
        return (None, None)
    return (int(m.group(1)), int(m.group(2)) if m.group(2) else None)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 100)
    print("OCR -- PDFs ESCANEADOS DOS ACTs/DCs DOS CORREIOS")
    print("=" * 100)
    print(f"Tesseract: {TESSERACT_PATH}")
    print(f"PDFs a processar: {len(PDFS_ESCANEADOS)}")
    print(f"DPI: {DPI} | Idioma: {IDIOMA}")
    print()

    inicio = datetime.now()

    todos_beneficios = []
    todos_salario = []
    relatorio = []

    for idx, nome_pdf in enumerate(PDFS_ESCANEADOS, 1):
        caminho = PASTA_PDFS / nome_pdf

        if not caminho.exists():
            print(f"[{idx}/{len(PDFS_ESCANEADOS)}] [SKIP] Nao encontrado: {nome_pdf}")
            continue

        ano_ini, ano_fim = ano_do_nome(nome_pdf)
        ano_str = f"{ano_ini}-{ano_fim}" if ano_fim else str(ano_ini)

        print(f"[{idx}/{len(PDFS_ESCANEADOS)}] {nome_pdf}  (ano {ano_str})")

        t0 = time.time()
        imagens = pdf_para_imagens(caminho, dpi=DPI)
        print(f"    {len(imagens)} paginas renderizadas")

        # OCR pagina por pagina
        texto_completo = []
        for num_pag, img in imagens:
            txt = ocr_imagem(img, lang=IDIOMA)
            texto_completo.append(f"\n--- PAGINA {num_pag} ---\n{txt}")

        texto = limpar_texto("\n".join(texto_completo))

        # Salva texto bruto para auditoria
        txt_saida = PASTA_SAIDA / f"ocr_txt_{Path(nome_pdf).stem}.txt"
        try:
            txt_saida.write_text(texto, encoding="utf-8")
        except Exception as e:
            print(f"    [AVISO] Nao conseguiu salvar txt: {e}")

        # Busca
        achados_ben = buscar(texto, KW_BENEFICIOS)
        achados_sal = buscar(texto, KW_SALARIO)

        for a in achados_ben:
            a["arquivo"] = nome_pdf
            a["ano"] = ano_str
            todos_beneficios.append(a)

        for a in achados_sal:
            a["arquivo"] = nome_pdf
            a["ano"] = ano_str
            todos_salario.append(a)

        dt = time.time() - t0
        print(f"    Beneficios: {len(achados_ben)} | Salario: {len(achados_sal)} | {dt:.1f}s")

        relatorio.append({
            "arquivo": nome_pdf,
            "ano": ano_str,
            "paginas": len(imagens),
            "chars_ocr": len(texto),
            "mencoes_beneficios": len(achados_ben),
            "mencoes_salario": len(achados_sal),
            "tempo_s": round(dt, 1),
        })

    # ---- CSV beneficios ----
    print()
    print("=" * 100)
    print("EXPORTANDO")
    print("=" * 100)

    campos = ["ano", "arquivo", "keyword", "linha", "contexto", "valores_rs", "percentuais"]
    if todos_beneficios:
        with open(PASTA_SAIDA / "ocr_beneficios.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            for r in todos_beneficios:
                linha = r.copy()
                linha["valores_rs"] = " | ".join(linha.get("valores_rs", []))
                linha["percentuais"] = " | ".join(linha.get("percentuais", []))
                w.writerow({k: linha.get(k, "") for k in campos})
        print(f"    [OK] ocr_beneficios.csv  ({len(todos_beneficios)} linhas)")

    if todos_salario:
        with open(PASTA_SAIDA / "ocr_salario_base.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            for r in todos_salario:
                linha = r.copy()
                linha["valores_rs"] = " | ".join(linha.get("valores_rs", []))
                linha["percentuais"] = " | ".join(linha.get("percentuais", []))
                w.writerow({k: linha.get(k, "") for k in campos})
        print(f"    [OK] ocr_salario_base.csv  ({len(todos_salario)} linhas)")

    # ---- Relatorio ----
    with open(PASTA_SAIDA / "ocr_relatorio.txt", "w", encoding="utf-8") as f:
        f.write("RELATORIO OCR -- PDFs ESCANEADOS\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Tesseract: {TESSERACT_PATH}\n")
        f.write(f"DPI: {DPI} | Idioma: {IDIOMA}\n\n")
        f.write(f"{'Ano':<12} {'Pags':>5} {'Chars':>8} {'Benef':>6} {'Sal':>5} {'Tempo':>7}  Arquivo\n")
        f.write("-" * 100 + "\n")
        for r in relatorio:
            f.write(f"{r['ano']:<12} {r['paginas']:>5} {r['chars_ocr']:>8} "
                    f"{r['mencoes_beneficios']:>6} {r['mencoes_salario']:>5} "
                    f"{r['tempo_s']:>6}s  {r['arquivo'][:50]}\n")
    print(f"    [OK] ocr_relatorio.txt")

    # ---- Resumo console ----
    print()
    print("=" * 100)
    print("RESUMO")
    print("=" * 100)
    print(f"  PDFs processados:      {len(relatorio)}")
    print(f"  Mencoes de beneficios: {len(todos_beneficios)}")
    print(f"  Mencoes de salario:    {len(todos_salario)}")
    print(f"  Tempo total:           {(datetime.now() - inicio).total_seconds():.0f}s")
    print()

    # Valores unicos de beneficios
    print("=" * 100)
    print("VALORES R$ -- BENEFICIOS")
    print("=" * 100)
    por_ano = {}
    for r in todos_beneficios:
        ano = r["ano"] or "?"
        por_ano.setdefault(ano, set())
        for v in r.get("valores_rs", []):
            por_ano[ano].add(v)

    for ano in sorted(por_ano.keys(), key=lambda x: str(x)):
        valores = sorted(por_ano[ano])
        if valores:
            print(f"\n  ANO {ano}:")
            for v in valores[:15]:
                print(f"    {v}")
            if len(valores) > 15:
                print(f"    ... (+{len(valores) - 15})")


if __name__ == "__main__":
    main()