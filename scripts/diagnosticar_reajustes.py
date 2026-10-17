"""
Mostra o que está sendo extraído de FIN_REAJUSTE_SALARIAL em cada arquivo.
Serve pra identificar valores errados antes de gerar o financeiro.json.

Uso:
    python scripts/diagnosticar_reajustes.py
"""
import json
import re
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"


def extrair_ano_do_nome(nome):
    m = re.search(r"(\d{4})", nome)
    return int(m.group(1)) if m else None


def main():
    print("=" * 100)
    print("DIAGNÓSTICO — EXTRAÇÃO DE FIN_REAJUSTE_SALARIAL")
    print("=" * 100)
    print()

    for arq in sorted(DATA_DIR.glob("*.json")):
        ano = extrair_ano_do_nome(arq.name)
        if not ano:
            continue

        try:
            doc = json.loads(arq.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERRO] {arq.name}: {e}")
            continue

        # Encontra cláusulas FIN_REAJUSTE_SALARIAL
        encontrados = []
        for c in doc.get("clausulas", []):
            if c.get("id_canonico") != "FIN_REAJUSTE_SALARIAL":
                continue

            encontrados.append({
                "valor_atual": c.get("valor_atual"),
                "unidade": c.get("unidade"),
                "detalhes": c.get("detalhes"),
                "texto": (c.get("texto") or "")[:200],
                "titulo": c.get("titulo_original"),
            })

        if not encontrados:
            print(f"{arq.name:35} | --- sem FIN_REAJUSTE_SALARIAL ---")
            continue

        for i, e in enumerate(encontrados):
            print(f"{arq.name:35} | valor={e['valor_atual']!r:10} | unidade={e['unidade']!r}")
            if e['detalhes']:
                print(f"{'':35} |   detalhes={e['detalhes']}")
            if e['texto']:
                print(f"{'':35} |   texto: {e['texto'][:120]}")
            print()


if __name__ == "__main__":
    main()