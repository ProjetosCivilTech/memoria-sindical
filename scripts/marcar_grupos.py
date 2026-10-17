"""
Adiciona os campos 'grupo' e 'papel' em JSONs que representam normas paralelas.

Os pares abaixo foram identificados manualmente:
  - 2013-2014: FENTECT (Acórdão TST 6942/2013) × FINDECT (ACT direto)
  - 2024-2025: FENTECT × FINDECT

Uso:
    python -m scripts.marcar_grupos --pasta data/ --dry-run
    python -m scripts.marcar_grupos --pasta data/
"""
import json
import argparse
from pathlib import Path


# Mapa: nome do arquivo → (grupo, papel)
# Atualizar este dict quando novos pares forem identificados.
MARCADORES = {
    # 2013-2014
    "ACT 2013-2014 FENTECT.json":   ("2013-2014", "FENTECT"),
    "ACT 2013-2014 FINDECT.json":   ("2013-2014", "FINDECT"),

    # 2024-2025
    "ACT 2024-2025 FENTECT.json":   ("2024-2025", "FENTECT"),
    "ACT 2024-2025 FINDECT.json":   ("2024-2025", "FINDECT"),
}


def marcar(arq: Path, grupo: str, papel: str, dry_run: bool) -> str:
    """
    Adiciona grupo/papel ao documento.
    Retorna um dos status: 'ja_marcado', 'marcaria', 'marcado', 'erro'.
    """
    try:
        doc = json.loads(arq.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return f"erro: JSON inválido ({e.msg})"

    md = doc.setdefault("metadados_documento", {})

    ja_marcado = (
        md.get("grupo") == grupo
        and md.get("papel") == papel
    )
    if ja_marcado:
        return "ja_marcado"

    md["grupo"] = grupo
    md["papel"] = papel

    if dry_run:
        return "marcaria"

    arq.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return "marcado"


def main():
    ap = argparse.ArgumentParser(
        description="Marca campos 'grupo' e 'papel' em JSONs de normas paralelas."
    )
    ap.add_argument("--pasta", default="data/", help="Pasta com os JSONs")
    ap.add_argument("--dry-run", action="store_true", help="Só mostra, não altera")
    args = ap.parse_args()

    pasta = Path(args.pasta)
    if not pasta.exists():
        print(f"❌ Pasta não encontrada: {pasta}")
        return

    print(f"📂 {pasta}\n")

    total = len(MARCADORES)
    cont = {"ja_marcado": 0, "marcaria": 0, "marcado": 0, "nao_encontrado": 0, "erro": 0}

    for nome, (grupo, papel) in MARCADORES.items():
        arq = pasta / nome

        if not arq.exists():
            print(f"❌ Não encontrado: {nome}")
            cont["nao_encontrado"] += 1
            continue

        status = marcar(arq, grupo, papel, args.dry_run)

        if status == "ja_marcado":
            print(f"✅ {nome}: já tinha grupo={grupo}, papel={papel}")
            cont["ja_marcado"] += 1
        elif status == "marcaria":
            print(f"🔧 {nome}: marcaria grupo={grupo}, papel={papel}")
            cont["marcaria"] += 1
        elif status == "marcado":
            print(f"✅ {nome}: marcado grupo={grupo}, papel={papel}")
            cont["marcado"] += 1
        else:
            print(f"❌ {nome}: {status}")
            cont["erro"] += 1

    # Resumo
    print()
    print(f"📊 Total de marcadores: {total}")
    print(f"   ✅ Já marcados:        {cont['ja_marcado']}")
    print(f"   🔧 A marcar (dry-run): {cont['marcaria']}")
    print(f"   ✅ Marcados:           {cont['marcado']}")
    print(f"   ❌ Não encontrados:    {cont['nao_encontrado']}")
    print(f"   ❌ Erros:              {cont['erro']}")


if __name__ == "__main__":
    main()