"""
Audita a pasta de PDFs contra o dicionário config.DOCUMENTOS.

Uso:
    python -m scripts.check_pdfs
"""
import argparse
from pathlib import Path
from scripts.config import DOCUMENTOS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="dados/")
    args = ap.parse_args()

    disco = {p.name for p in Path(args.base).glob("*.pdf")}
    esperado = {a for cfg in DOCUMENTOS.values() for a in cfg["arquivos"]}

    faltam = disco - esperado
    sobram = esperado - disco

    print(f"PDFs no disco:      {len(disco)}")
    print(f"PDFs no dicionário: {len(esperado)}")
    print()

    if faltam:
        print("⚠ No disco mas NÃO no dicionário:")
        for f in sorted(faltam):
            print(f"   - {f}")
        print()
    if sobram:
        print("⚠ No dicionário mas NÃO no disco:")
        for f in sorted(sobram):
            print(f"   - {f}")
        print()
    if not faltam and not sobram:
        print("✅ Tudo alinhado.")


if __name__ == "__main__":
    main()