"""
Compara os id_canonico de dois JSONs e sugere pares por similaridade.

Uso:
    python -m scripts.sugerir_pares data/"DC 2013-2014 FENTECT.json" data/"ACT 2013-2014 FINDECT.json"
"""
import json
import sys
import argparse
from pathlib import Path
from difflib import SequenceMatcher


def carregar_ids(arq: Path) -> dict[str, dict]:
    doc = json.loads(arq.read_text(encoding="utf-8"))
    return {c["id_canonico"]: c for c in doc.get("clausulas", [])}


def similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo_a", type=Path, help="JSON do lado A (ex.: FENTECT)")
    ap.add_argument("arquivo_b", type=Path, help="JSON do lado B (ex.: FINDECT)")
    ap.add_argument("--min-score", type=float, default=0.5,
                    help="Score mínimo para sugerir par (0-1)")
    args = ap.parse_args()

    a = carregar_ids(args.arquivo_a)
    b = carregar_ids(args.arquivo_b)

    print(f"A: {args.arquivo_a.name} ({len(a)} cláusulas)")
    print(f"B: {args.arquivo_b.name} ({len(b)} cláusulas)")
    print()

    # 1. Pares prováveis por similaridade
    print("=" * 100)
    print(f"PARES SUGERIDOS (score >= {args.min_score})")
    print("=" * 100)

    pares = []
    for id_a in sorted(a.keys()):
        for id_b in sorted(b.keys()):
            score = similaridade(id_a, id_b)
            if score >= args.min_score:
                pares.append((score, id_a, id_b))

    pares.sort(reverse=True)
    for score, id_a, id_b in pares:
        print(f"{score:.2f}  {id_a:45}  <->  {id_b:45}")

    # 2. IDs só em A
    ids_a_pareados = {id_a for _, id_a, _ in pares}
    ids_b_pareados = {id_b for _, _, id_b in pares}

    print()
    print("=" * 100)
    print("SÓ EM A (sem par sugerido)")
    print("=" * 100)
    for id_a in sorted(a.keys()):
        if id_a not in ids_a_pareados:
            print(f"  {id_a:60}  (num {a[id_a].get('numero_clausula_original')})")

    print()
    print("=" * 100)
    print("SÓ EM B (sem par sugerido)")
    print("=" * 100)
    for id_b in sorted(b.keys()):
        if id_b not in ids_b_pareados:
            print(f"  {id_b:60}  (num {b[id_b].get('numero_clausula_original')})")


if __name__ == "__main__":
    main()