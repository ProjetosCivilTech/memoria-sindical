"""
Detecta IDs canônicos com nomes similares (candidatos a sinônimos).

Uso:
    python -m scripts.detectar_sinonimos
"""
import json
from collections import Counter
from pathlib import Path
from difflib import SequenceMatcher


def carregar_ids(jsonl_path: Path):
    c = Counter()
    for linha in jsonl_path.read_text(encoding="utf-8").splitlines():
        cl = json.loads(linha)
        c[cl["id_canonico"]] += 1
    return c


def similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def main():
    jsonl = Path("data/build/clausulas.jsonl")
    if not jsonl.exists():
        print(f"❌ Não encontrado: {jsonl}")
        print("   Rode antes: python -m scripts.consolidate --raw data/ --out data/build/")
        return

    contagem = carregar_ids(jsonl)

    # 1. Agrupa por prefixo (FIN, SOC, SIN, CON, TEC, PRO)
    por_prefixo = {}
    for cid in contagem:
        prefixo = cid.split("_")[0] if "_" in cid else "OUTROS"
        por_prefixo.setdefault(prefixo, []).append(cid)

    print(f"📊 Total IDs: {len(contagem)}\n")
    for p, ids in sorted(por_prefixo.items()):
        print(f"  {p:6}  {len(ids)} IDs")

    # 2. Detecta pares similares dentro do mesmo prefixo
    print()
    print("=" * 100)
    print("PARES SIMILARES (score >= 0.75) — candidatos a sinônimo")
    print("=" * 100)

    sugestoes = []
    for prefixo, ids in por_prefixo.items():
        for i, a in enumerate(sorted(ids)):
            for b in sorted(ids)[i + 1:]:
                score = similaridade(a, b)
                if score >= 0.75:
                    sugestoes.append((score, a, b, contagem[a], contagem[b]))

    sugestoes.sort(reverse=True)
    for score, a, b, n_a, n_b in sugestoes:
        # Sugere manter o de maior frequência
        vencedor = a if n_a >= n_b else b
        perdedor = b if n_a >= n_b else a
        print(f"{score:.2f}  {perdedor:55} ({contagem[perdedor]:>3}x)  →  {vencedor:55} ({contagem[vencedor]:>3}x)")

    print()
    print(f"Total de sugestões: {len(sugestoes)}")

    # 3. IDs que aparecem 1 vez (órfãos)
    print()
    print("=" * 100)
    print("IDs ÓRFÃOS (aparecem só 1 vez):")
    print("=" * 100)
    orfaos = sorted([cid for cid, n in contagem.items() if n == 1])
    for cid in orfaos:
        print(f"  {cid}")


if __name__ == "__main__":
    main()