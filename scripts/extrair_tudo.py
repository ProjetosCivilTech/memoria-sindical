# -*- coding: utf-8 -*-
"""
extrair_tudo.py — Extração COMPLETA de todos os PDFs do projeto usando EasyOCR.

Objetivo: capturar o máximo de informação estruturada e bruta para decisão
posterior. Não tenta normalizar IDs, não classifica cláusulas, não gera
schema final.

Para cada PDF gera (em dados/extraidos/{stem}/):
    texto.txt           texto corrido, hyphen-join aplicado
    texto_paginas.txt   texto com marcadores --- p.N (metodo) ---
    tabelas.json        tabelas detectadas por pdfplumber
    metadados.json      metadados do PDF + stats por página
    padroes.json        regex extraídos (datas, R$, %, cláusulas, processos)

Consolidado (em dados/extraidos/):
    _manifest.json      hash + status de cada PDF (à prova de crash)
    _todos.txt          tudo concatenado em ordem cronológica
    _revisar.txt        OCR com confiança < CONF_MINIMA

Uso:
    %cd F:\\AUTOMAÇÕES\\projeto_memoria_sindicato
    %run scripts/extrair_tudo.py --limit 3
    %run scripts/extrair_tudo.py
    %run scripts/extrair_tudo.py --only "1988"
    %run scripts/extrair_tudo.py --force
    %run scripts/extrair_tudo.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pdfplumber
import easyocr
from PIL import Image

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

RAIZ     = Path(r"F:\AUTOMAÇÕES\projeto_memoria_sindicato")
DADOS    = RAIZ / "dados"
SAIDA    = DADOS / "extraidos"
MANIFEST = SAIDA / "_manifest.json"
TODOS    = SAIDA / "_todos.txt"
REVISAR  = SAIDA / "_revisar.txt"

DPI_OCR        = 300
MIN_CHARS      = 100
CONF_MINIMA    = 80.0

# Inicializar EasyOCR uma única vez (carrega os modelos na memória)
# 'por' = português. 'gpu'=True se tiver placa NVIDIA, senão False
print("[EasyOCR] Carregando modelos... (isso pode levar alguns segundos)")
reader = easyocr.Reader(['pt'], gpu=False)
print("[EasyOCR] Modelos carregados com sucesso.")


# ---------------------------------------------------------------------------
# REGEX (padrões que valem a pena ter à mão depois)
# ---------------------------------------------------------------------------

RE_PADROES = {
    "datas_br":     re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    "datas_ext":    re.compile(
        r"\b\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|"
        r"julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4}\b",
        re.IGNORECASE),
    "valores_brl":  re.compile(r"R\$\s*[\d]{1,3}(?:\.\d{3})*(?:,\d{1,2})?"),
    "percentuais":  re.compile(r"\b\d{1,3}(?:[.,]\d{1,4})?\s*%"),
    "clausulas":    re.compile(
        r"^\s*(?:Cl[áa]usula\s+)?(\d{1,3})\s*[ªº]?\s*[\)\-–]",
        re.MULTILINE | re.IGNORECASE),
    "processos_tst": re.compile(
        r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b"),
    "cnpj":         re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    "artigos":      re.compile(r"\bArt(?:igo)?\.?\s*\d+\b", re.IGNORECASE),
    "incisos":      re.compile(r"\b(?:inciso\s+)?[IVXLCDM]{1,6}\b"),
    "paragrafos":   re.compile(r"§\s*\d+[º°]?"),
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def sha256_arquivo(p: Path, bloco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(bloco), b""):
            h.update(chunk)
    return h.hexdigest()


def carregar_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"versao": "2.0", "atualizado_em": None, "extraidos": {}}


def salvar_manifest(m: dict) -> None:
    m["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2),
                        encoding="utf-8")


def limpar_hyphen(txt: str) -> str:
    """coope-\nração → cooperação ; mantém parágrafos."""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"-\n(\w)", r"\1", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt


def normalizar_tabela(tabela: list) -> list:
    """Limpa células None, espaços, quebras internas."""
    if not tabela:
        return []
    saida = []
    for linha in tabela:
        nova = []
        for cel in linha:
            if cel is None:
                nova.append("")
            else:
                nova.append(re.sub(r"\s+", " ", str(cel)).strip())
        saida.append(nova)
    return saida


def render_pagina_para_imagem(pagina) -> Image.Image:
    """Renderiza página em 300dpi via pdfplumber (usa pypdfium2)."""
    img = pagina.to_image(resolution=DPI_OCR)
    return img.original  # PIL.Image


def ocr_pagina(pil_img) -> tuple[str, float]:
    """Usa EasyOCR para extrair texto da imagem."""
    try:
        # EasyOCR retorna lista de (bounding_box, texto, confianca)
        resultados = reader.readtext(pil_img, detail=1, paragraph=True)
        
        if not resultados:
            return "", 0.0
        
        # Junta o texto e calcula a confiança média
        textos = []
        confiancas = []
        
        for resultado in resultados:
            bbox, texto, confianca = resultado
            texto = texto.strip()
            if texto:
                textos.append(texto)
                confiancas.append(confianca * 100)  # EasyOCR retorna 0-1, converter para 0-100
        
        if not confiancas:
            return "", 0.0
        
        conf_media = round(sum(confiancas) / len(confiancas), 1)
        texto_final = "\n".join(textos)
        
        return texto_final, conf_media
        
    except Exception as e:
        return f"[ERRO EasyOCR: {e}]", 0.0


def extrair_padroes(texto: str) -> dict:
    """Extrai amostras de cada padrão. Limita a 500 por tipo p/ não inflar."""
    out = {}
    for nome, rx in RE_PADROES.items():
        achados = rx.findall(texto)
        # alguns padrões têm grupo de captura
        valores = []
        for a in achados:
            valores.append(a if isinstance(a, str) else a[0])
        valores = [v for v in valores if v]
        out[nome] = {
            "total": len(valores),
            "amostra": valores[:50],
        }
    return out


# ---------------------------------------------------------------------------
# NÚCLEO
# ---------------------------------------------------------------------------

def processar_pdf(pdf: Path, forcar_ocr: bool) -> dict:
    t0 = time.time()

    texto_paginas: list[str] = []
    texto_limpo: list[str] = []
    tabelas_out: list[dict] = []
    paginas_info: list[dict] = []
    confs_ocr: list[float] = []

    with pdfplumber.open(str(pdf)) as doc:
        meta = doc.metadata or {}
        total_pag = len(doc.pages)

        for i, pagina in enumerate(doc.pages):
            try:
                nativo = (pagina.extract_text() or "").strip()
            except Exception:
                nativo = ""

            precisa_ocr = forcar_ocr or len(nativo) < MIN_CHARS

            if precisa_ocr:
                try:
                    img = render_pagina_para_imagem(pagina)
                    txt_ocr, conf = ocr_pagina(img)
                    metodo = "EasyOCR"
                    confs_ocr.append(conf)
                except Exception as e:
                    txt_ocr = f"[ERRO OCR p.{i+1}: {e}]"
                    conf = 0.0
                    metodo = "OCR-erro"
                txt = txt_ocr
                aviso = " ⚠REVISAR" if conf < CONF_MINIMA else ""
                cab = f"\n--- p.{i+1} ({metodo} conf={conf}{aviso}) ---\n"
            else:
                txt = nativo
                conf = None
                metodo = "nativo"
                cab = f"\n--- p.{i+1} (nativo) ---\n"

            texto_paginas.append(cab + txt)
            texto_limpo.append(txt)

            # Tabelas (só vale a pena tentar se tem texto nativo)
            if not precisa_ocr:
                try:
                    tabs = pagina.extract_tables() or []
                    for j, t in enumerate(tabs):
                        tabs_norm = normalizar_tabela(t)
                        if tabs_norm:
                            tabelas_out.append({
                                "pagina": i + 1,
                                "indice": j,
                                "linhas": len(tabs_norm),
                                "colunas": max(len(r) for r in tabs_norm),
                                "dados": tabs_norm,
                            })
                except Exception:
                    pass

            paginas_info.append({
                "pagina": i + 1,
                "metodo": metodo,
                "chars": len(txt),
                "conf_ocr": conf,
            })

    texto_corrido = limpar_hyphen("\n".join(texto_limpo))
    texto_paginas_txt = limpar_hyphen("\n".join(texto_paginas))

    if all(p["metodo"].startswith("EasyOCR") or p["metodo"].startswith("OCR") for p in paginas_info):
        metodo_geral = "easyocr"
    elif all(p["metodo"] == "nativo" for p in paginas_info):
        metodo_geral = "nativo"
    else:
        metodo_geral = "hibrido"

    return {
        "texto": texto_corrido,
        "texto_paginas": texto_paginas_txt,
        "tabelas": tabelas_out,
        "metadados_pdf": {
            "titulo": meta.get("Title"),
            "autor": meta.get("Author"),
            "assunto": meta.get("Subject"),
            "criador": meta.get("Creator"),
            "produtor": meta.get("Producer"),
            "criado_em": meta.get("CreationDate"),
            "modificado_em": meta.get("ModDate"),
        },
        "paginas_info": paginas_info,
        "paginas_total": total_pag,
        "paginas_ocr": sum(1 for p in paginas_info if p["metodo"].startswith("EasyOCR") or p["metodo"].startswith("OCR")),
        "conf_ocr_media": round(sum(confs_ocr) / len(confs_ocr), 1) if confs_ocr else None,
        "metodo": metodo_geral,
        "tempo_s": round(time.time() - t0, 2),
    }


# ---------------------------------------------------------------------------
# CONSOLIDAÇÃO
# ---------------------------------------------------------------------------

def gerar_consolidado() -> None:
    pastas = sorted([p for p in SAIDA.iterdir() if p.is_dir()])
    partes = []
    for p in pastas:
        txt = p / "texto_paginas.txt"
        if txt.exists():
            partes.append(f"\n\n{'=' * 78}\n## {p.name}\n{'=' * 78}\n")
            partes.append(txt.read_text(encoding="utf-8"))
    TODOS.write_text("".join(partes), encoding="utf-8")


def gerar_lista_revisao(m: dict) -> None:
    criticos = []
    for nome, meta in m["extraidos"].items():
        conf = meta.get("conf_ocr_media")
        if conf is not None and conf < CONF_MINIMA:
            criticos.append((nome, conf, meta.get("paginas_ocr", 0)))
    if not criticos:
        if REVISAR.exists():
            REVISAR.unlink()
        return
    linhas = [f"# OCR abaixo de {CONF_MINIMA}% — revisar manualmente\n"]
    for nome, conf, pags in sorted(criticos, key=lambda x: x[1]):
        linhas.append(f"{conf:>5.1f}%  {pags:>3}p OCR  {nome}")
    REVISAR.write_text("\n".join(linhas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="Reprocessa mesmo se hash bateu.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Processa só os N primeiros pendentes.")
    ap.add_argument("--only", type=str, default="",
                    help="Filtro por substring no nome.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Lista o que faria, sem processar.")
    ap.add_argument("--no-consolidado", action="store_true",
                    help="Não regenera _todos.txt.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    SAIDA.mkdir(parents=True, exist_ok=True)

    manifest = carregar_manifest()
    pdfs = sorted(DADOS.glob("*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if args.only.lower() in p.name.lower()]

    pendentes = []
    for p in pdfs:
        h = sha256_arquivo(p)
        meta = manifest["extraidos"].get(p.name, {})
        if meta.get("sha256") == h and not args.force:
            continue
        pendentes.append((p, h))

    if args.limit:
        pendentes = pendentes[:args.limit]

    print(f"\n[SCAN] {len(pdfs)} PDFs | {len(pendentes)} pendentes | "
          f"{len(pdfs) - len(pendentes)} já extraídos\n")

    if args.dry_run:
        for p, _ in pendentes:
            print(f"  {p.name}")
        return

    t_ini = time.time()
    for i, (pdf, h) in enumerate(pendentes, 1):
        print(f"[{i:>2}/{len(pendentes)}] {pdf.name}", end="  ", flush=True)
        try:
            res = processar_pdf(pdf, forcar_ocr=args.force)
        except Exception as e:
            print(f"[FALHOU] {e}")
            continue

        pasta = SAIDA / pdf.stem
        pasta.mkdir(exist_ok=True)

        (pasta / "texto.txt").write_text(res["texto"], encoding="utf-8")
        (pasta / "texto_paginas.txt").write_text(res["texto_paginas"],
                                                 encoding="utf-8")
        (pasta / "tabelas.json").write_text(
            json.dumps(res["tabelas"], ensure_ascii=False, indent=2),
            encoding="utf-8")
        (pasta / "metadados.json").write_text(
            json.dumps({
                "arquivo_origem": pdf.name,
                "metadados_pdf": res["metadados_pdf"],
                "paginas_info": res["paginas_info"],
                "paginas_total": res["paginas_total"],
                "paginas_ocr": res["paginas_ocr"],
                "conf_ocr_media": res["conf_ocr_media"],
                "metodo": res["metodo"],
                "tempo_s": res["tempo_s"],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8")

        padroes = extrair_padroes(res["texto"])
        (pasta / "padroes.json").write_text(
            json.dumps(padroes, ensure_ascii=False, indent=2),
            encoding="utf-8")

        manifest["extraidos"][pdf.name] = {
            "pasta": pdf.stem,
            "sha256": h,
            "paginas_total": res["paginas_total"],
            "paginas_ocr": res["paginas_ocr"],
            "conf_ocr_media": res["conf_ocr_media"],
            "metodo": res["metodo"],
            "tempo_s": res["tempo_s"],
            "extraido_em": datetime.now().isoformat(timespec="seconds"),
        }
        salvar_manifest(manifest)

        conf_txt = (f"conf={res['conf_ocr_media']}"
                    if res["conf_ocr_media"] is not None else "—")
        print(f"[OK] {res['metodo']:>7} | "
              f"{res['paginas_total']:>2}p ({res['paginas_ocr']} OCR) | "
              f"{conf_txt:>10} | {res['tempo_s']:>5}s")

    if not args.no_consolidado and pendentes:
        print("\n[CONSOLIDANDO] _todos.txt ...", end=" ", flush=True)
        gerar_consolidado()
        tam = TODOS.stat().st_size / 1024
        print(f"OK ({tam:.0f} KB)")

    gerar_lista_revisao(manifest)
    if REVISAR.exists():
        print(f"[REVISAR] {REVISAR.name}")

    print(f"\n[DONE] {len(pendentes)} PDFs em {time.time() - t_ini:.1f}s")
    print(f"[OUT] {SAIDA}")


if __name__ == "__main__":
    main()