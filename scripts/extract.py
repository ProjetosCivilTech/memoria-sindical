"""
Extração estruturada dos PDFs.

Uso:
    python -m scripts.extract                          # processa tudo
    python -m scripts.extract --apenas 2025-2026       # um doc
    python -m scripts.extract --forcar                 # sobrescreve existentes
    python -m scripts.extract --ocr                    # tenta OCR se PDF sem texto
"""
import os
import json
import argparse
from pathlib import Path

import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

from scripts.config import DOCUMENTOS
from scripts.schema import Documento

load_dotenv()

SYSTEM_PROMPT = """Você é um extrator estruturado de normas coletivas da ECT (Correios).

Receberá o texto integral de um ou mais PDFs que compõem UM ÚNICO documento
normativo (ACT, DC, DCG ou Cartilha). Pode haver continuação entre PDFs —
trate tudo como um documento só.

Devolva APENAS um JSON válido no schema `Documento`.

Regras críticas:
1. Se o texto for de ACÓRDÃO DO TST (tem "VOTO", "RELATÓRIO", "EMENTA"),
   extraia SOMENTE o que consta na PARTE DISPOSITIVA / SENTENÇA NORMATIVA.
   NÃO extraia cláusulas do voto, do relatório ou de pedidos não deferidos.
2. Se houver cláusulas deferidas parcialmente, marque status
   "PARCIALMENTE DEFERIDO" e registre em `detalhes` o que foi deferido e o
   que foi indeferido.
3. NÃO invente cláusulas. Se algo não se encaixa no schema, coloque em
   `temas_nao_mapeados`.
4. Se o PDF for um ADITAMENTO, TERMO ADITIVO, COMPLEMENTO ou ATA
   COMPLEMENTAR, devolva um JSON com:
       "tipo_documento": "ADITAMENTO",
       "base": "<id do doc base>",
       "memoria_negociacao_geral": [{"descricao": "...", "alteracoes": [...]}]
   Não gere cláusulas novas.
5. `id_canonico`: use o padrão existente (FIN_*, SOC_*, SIN_*, CON_*, TEC_*,
   PRO_*). Se não houver correspondência, crie um novo seguindo o padrão.
6. `status`: apenas "DEFERIDO", "INDEFERIDO", "PARCIALMENTE DEFERIDO",
   "PREJUDICADO", "EXTINTO".
7. `valor_atual`: número puro. `unidade`: "%", "BRL", "CRUZEIROS", "dias",
   "meses", "kg", "min".
8. Preserve a moeda da época em `detalhes.moeda` quando o valor não for em %.
9. Para o campo `ano_inicio`, use o ano de início da vigência (ex.: 2024 para
   ACT 2024-2025). `ano_fim` é o ano final.
"""


# ----------------------------------------------------------------
# Extração de texto
# ----------------------------------------------------------------

def _ocr_pdf(pdf_path: Path) -> str:
    """Fallback OCR (requer pytesseract + pdf2image + poppler)."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        raise RuntimeError(
            "OCR solicitado mas pytesseract/pdf2image não instalados."
        ) from e
    paginas = convert_from_path(str(pdf_path))
    return "\n".join(pytesseract.image_to_string(p, lang="por") for p in paginas)


def extrair_texto(arquivos: list[Path], usar_ocr: bool = False) -> str:
    partes = []
    for pdf_path in arquivos:
        with pdfplumber.open(pdf_path) as pdf:
            texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
        if not texto.strip():
            if usar_ocr:
                texto = _ocr_pdf(pdf_path)
            if not texto.strip():
                raise ValueError(f"PDF sem texto extraível: {pdf_path.name}")
        partes.append(f"\n\n### ARQUIVO: {pdf_path.name}\n\n{texto}")
    return "\n".join(partes)


# ----------------------------------------------------------------
# Chunking para acórdãos longos
# ----------------------------------------------------------------

def chunkar(texto: str, max_chars: int = 120_000, overlap: int = 3_000):
    if len(texto) <= max_chars:
        yield texto
        return
    ini = 0
    while ini < len(texto):
        fim = min(ini + max_chars, len(texto))
        yield texto[ini:fim]
        if fim == len(texto):
            break
        ini = fim - overlap


# ----------------------------------------------------------------
# LLM
# ----------------------------------------------------------------

def chamar_llm(texto: str, client: OpenAI, model: str) -> dict:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": texto},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def consolidar_chunks(chunks: list[dict]) -> dict:
    base = chunks[0]
    ids_vistos = {c["id_canonico"] for c in base.get("clausulas", [])}
    for extra in chunks[1:]:
        for c in extra.get("clausulas", []):
            if c["id_canonico"] not in ids_vistos:
                base["clausulas"].append(c)
                ids_vistos.add(c["id_canonico"])
    # concatena demais listas
    for campo in ("temas_nao_mapeados", "notas_metodologicas",
                  "memoria_negociacao_geral"):
        for extra in chunks[1:]:
            base.setdefault(campo, []).extend(extra.get(campo, []))
    return base


# ----------------------------------------------------------------
# Processamento de um documento
# ----------------------------------------------------------------

def processar(doc_id: str, cfg: dict, base_dir: Path,
              out_dir: Path, client: OpenAI, model: str,
              usar_ocr: bool, forcar: bool) -> Path:
    out_path = out_dir / f"{doc_id}.json"
    if out_path.exists() and not forcar:
        print(f"[skip] {doc_id} já existe")
        return out_path

    arquivos = [base_dir / a for a in cfg["arquivos"]]
    faltando = [a for a in arquivos if not a.exists()]
    if faltando:
        raise FileNotFoundError(f"Faltando em {doc_id}: {[f.name for f in faltando]}")

    texto = extrair_texto(arquivos, usar_ocr=usar_ocr)
    respostas = [chamar_llm(c, client, model) for c in chunkar(texto)]
    resultado = consolidar_chunks(respostas)

    # Aditamento: anexa ao base e encerra
    if resultado.get("tipo_documento") == "ADITAMENTO":
        base_id = cfg["base"]
        base_path = out_dir / f"{base_id}.json"
        if not base_path.exists():
            raise FileNotFoundError(
                f"Aditamento {doc_id}: base {base_id} não existe ainda."
            )
        base_doc = json.loads(base_path.read_text(encoding="utf-8"))
        base_doc.setdefault("memoria_negociacao_geral", []).append({
            "origem": doc_id,
            "arquivos": [a.name for a in arquivos],
            **resultado,
        })
        base_path.write_text(
            json.dumps(base_doc, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return base_path

    # Documento normal: preenche metadados
    resultado.setdefault("metadados_documento", {})
    md = resultado["metadados_documento"]
    md["tipo"] = cfg["tipo"]
    md["entidades_profissionais"] = cfg.get("entidades", [])
    md["arquivo_origem"] = "; ".join(a.name for a in arquivos)
    if "grupo" in cfg: md["grupo"] = cfg["grupo"]
    if "papel" in cfg: md["papel"] = cfg["papel"]
    if "greve" in cfg: md["greve"] = cfg["greve"]
    if "observacao" in cfg: md["observacao"] = cfg["observacao"]

    doc = Documento(**resultado)
    out_path.write_text(
        doc.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )
    return out_path


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="dados/")
    ap.add_argument("--out", default="data/raw/")
    ap.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-4o"))
    ap.add_argument("--base-url", default=os.getenv("LLM_BASE_URL"))
    ap.add_argument("--apenas", default=None)
    ap.add_argument("--forcar", action="store_true")
    ap.add_argument("--ocr", action="store_true")
    args = ap.parse_args()

    client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=args.base_url)

    base_dir = Path(args.base)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ids = [args.apenas] if args.apenas else list(DOCUMENTOS.keys())

    for doc_id in ids:
        try:
            p = processar(doc_id, DOCUMENTOS[doc_id], base_dir,
                          out_dir, client, args.model, args.ocr, args.forcar)
            print(f"[OK] {doc_id} -> {p.name}")
        except Exception as e:
            print(f"[ERRO] {doc_id}: {e}")


if __name__ == "__main__":
    main()