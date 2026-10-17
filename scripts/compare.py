"""
Compara normas paralelas (FENTECT × FINDECT) por grupo.

Uso:
    python -m scripts.compare
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict


def indexar(doc):
    return {c["id_canonico"]: c for c in doc.get("clausulas", [])}


def comparar(doc_a, doc_b):
    a, b = indexar(doc_a), indexar(doc_b)
    todos = sorted(set(a) | set(b))

    divergencias, iguais = [], 0
    for cid in todos:
        ca, cb = a.get(cid), b.get(cid)
        if not ca:
            divergencias.append({"id": cid, "tipo": "só em B", "B": cb})
        elif not cb:
            divergencias.append({"id": cid, "tipo": "só em A", "A": ca})
        elif (ca["status"] != cb["status"]
              or ca.get("valor_atual") != cb.get("valor_atual")):
            divergencias.append({
                "id": cid,
                "tipo": "divergente",
                "A": {"status": ca["status"], "valor": ca.get("valor_atual"),
                      "unidade": ca.get("unidade")},
                "B": {"status": cb["status"], "valor": cb.get("valor_atual"),
                      "unidade": cb.get("unidade")},
            })
        else:
            iguais += 1

    return {
        "grupo": doc_a["metadados_documento"].get("grupo"),
        "A": {"papel": doc_a["metadados_documento"].get("papel"),
              "n_clausulas": len(doc_a.get("clausulas", []))},
        "B": {"papel": doc_b["metadados_documento"].get("papel"),
              "n_clausulas": len(doc_b.get("clausulas", []))},
        "comuns": len(set(a) & set(b)),
        "iguais": iguais,
        "divergencias": divergencias,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/")
    ap.add_argument("--out", default="data/build/comparacoes/")
    args = ap.parse_args()

    raw = Path(args.raw)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    por_grupo = defaultdict(list)
    for p in raw.glob("*.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        g = doc["metadados_documento"].get("grupo")
        if g:
            por_grupo[g].append(doc)

    for grupo, docs in por_grupo.items():
        if len(docs) < 2:
            continue
        docs.sort(key=lambda d: d["metadados_documento"].get("papel", ""))
        resultado = comparar(docs[0], docs[1])
        (out / f"{grupo}.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[OK] {grupo}: {resultado['comuns']} comuns, "
              f"{len(resultado['divergencias'])} divergências")


if __name__ == "__main__":
    main()