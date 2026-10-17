"""
Uso:
    export LLM_API_KEY="..."
    python scripts/extract.py --pdfs pdfs/ --out data/raw/
"""
import os
import json
import argparse
from pathlib import Path

import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

from schema import Documento

load_dotenv()

SYSTEM_PROMPT = """Você é um extrator estruturado de normas coletivas da ECT (Correios).
Receberá o texto integral de um ACT, DC ou DCG e deve devolver APENAS um JSON
que valide o schema `Documento` (metadados_documento + clausulas + ...).

Regras:
- id_canonico: use o padrão canônico existente (FIN_*, SOC_*, SIN_*, CON_*, TEC_*, PRO_*).
- status: apenas "DEFERIDO", "INDEFERIDO", "PARCIALMENTE DEFERIDO", "PREJUDICADO", "EXTINTO".
- valor_atual: número puro (sem símbolo). unidade: "%", "BRL", "CRUZEIROS", "dias", "meses".
- detalhes: objeto livre com subparágrafos, percentuais, prazos, valores.
- memoria_negociacao: o que foi pedido vs. concedido (quando houver).
- NÃO invente cláusulas. Se algo não se encaixa, coloque em temas_nao_mapeados.
"""


def extrair_texto(pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


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


def processar(pdf_path: Path, out_dir: Path, client: OpenAI, model: str) -> Path:
    texto = extrair_texto(pdf_path)
    bruto = chamar_llm(texto, client, model)
    bruto.setdefault("metadados_documento", {})["arquivo_origem"] = pdf_path.name
    doc = Documento(**bruto)
    out_path = out_dir / f"{pdf_path.stem}.json"
    out_path.write_text(
        doc.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdfs", default="pdfs/")
    ap.add_argument("--out", default="data/raw/")
    ap.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-4o"))
    ap.add_argument("--base-url", default=os.getenv("LLM_BASE_URL"))
    args = ap.parse_args()

    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=args.base_url,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for pdf in sorted(Path(args.pdfs).glob("*.pdf")):
        try:
            p = processar(pdf, out_dir, client, args.model)
            print(f"[OK] {pdf.name} -> {p}")
        except Exception as e:
            print(f"[ERRO] {pdf.name}: {e}")


if __name__ == "__main__":
    main()