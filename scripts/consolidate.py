"""
Uso:
    python scripts/consolidate.py --raw data/raw/ --out data/build/
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict

import pandas as pd


def carregar(raw_dir: Path):
    docs = []
    for p in sorted(raw_dir.glob("*.json")):
        docs.append(json.loads(p.read_text(encoding="utf-8")))
    docs.sort(key=lambda d: (
        d["metadados_documento"]["ano_inicio"],
        d["metadados_documento"].get("ano_fim") or 0,
    ))
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/")
    ap.add_argument("--out", default="data/build/")
    args = ap.parse_args()

    raw_dir = Path(args.raw)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "por_clausula").mkdir(exist_ok=True)

    docs = carregar(raw_dir)

    # ---- 1. Hierárquico ----
    consolidado = {
        "total_documentos": len(docs),
        "total_clausulas": sum(len(d.get("clausulas", [])) for d in docs),
        "documentos": docs,
    }
    (out_dir / "all.json").write_text(
        json.dumps(consolidado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ---- 2. JSONL por cláusula ----
    with (out_dir / "clausulas.jsonl").open("w", encoding="utf-8") as f:
        for d in docs:
            meta = d["metadados_documento"]
            base = {
                "ano_inicio": meta["ano_inicio"],
                "ano_fim": meta.get("ano_fim"),
                "tipo": meta["tipo"],
                "processo": meta.get("processo"),
            }
            for c in d.get("clausulas", []):
                f.write(json.dumps({**base, **c}, ensure_ascii=False) + "\n")

    # ---- 3. CSV achatado ----
    linhas = []
    for d in docs:
        meta = d["metadados_documento"]
        for c in d.get("clausulas", []):
            linhas.append({
                "ano_inicio": meta["ano_inicio"],
                "ano_fim": meta.get("ano_fim"),
                "tipo": meta["tipo"],
                "processo": meta.get("processo"),
                "tribunal": meta.get("tribunal"),
                "relator": meta.get("relator"),
                "id_canonico": c.get("id_canonico"),
                "numero_clausula_original": c.get("numero_clausula_original"),
                "titulo_original": c.get("titulo_original"),
                "status": c.get("status"),
                "valor_atual": c.get("valor_atual"),
                "unidade": c.get("unidade"),
                "detalhes_json": json.dumps(c.get("detalhes"), ensure_ascii=False),
                "memoria_negociacao": c.get("memoria_negociacao"),
                "observacao": c.get("observacao"),
                "pagina_referencia": c.get("pagina_referencia"),
            })
    df = pd.DataFrame(linhas).drop_duplicates(
        subset=["ano_inicio", "ano_fim", "id_canonico", "titulo_original"]
    )
    df.to_csv(out_dir / "clausulas.csv", index=False, encoding="utf-8-sig")

    # ---- 4. Índice ----
    idx = [
        {
            "periodo": f"{d['metadados_documento']['ano_inicio']}-"
                       f"{d['metadados_documento'].get('ano_fim') or '?'}",
            "tipo": d["metadados_documento"]["tipo"],
            "arquivo": f"data/raw/{d['metadados_documento']['arquivo_origem'].replace('.pdf', '.json')}",
            "n_clausulas": len(d.get("clausulas", [])),
        }
        for d in docs
    ]
    (out_dir / "index.json").write_text(
        json.dumps(idx, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ---- 5. Por cláusula (histórico) ----
    por_clausula = defaultdict(list)
    for d in docs:
        meta = d["metadados_documento"]
        for c in d.get("clausulas", []):
            por_clausula[c["id_canonico"]].append({
                "ano_inicio": meta["ano_inicio"],
                "ano_fim": meta.get("ano_fim"),
                "tipo": meta["tipo"],
                **c,
            })
    for cid, ocorrencias in por_clausula.items():
        ocorrencias.sort(key=lambda x: (x["ano_inicio"], x.get("ano_fim") or 0))
        (out_dir / "por_clausula" / f"{cid}.json").write_text(
            json.dumps(ocorrencias, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"Documentos: {len(docs)}")
    print(f"Cláusulas: {consolidado['total_clausulas']}")
    print(f"IDs canônicos: {len(por_clausula)}")


if __name__ == "__main__":
    main()