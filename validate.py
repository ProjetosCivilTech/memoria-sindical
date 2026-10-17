"""
Uso:
    python scripts/validate.py --raw data/raw/
"""
import json
import argparse
from pathlib import Path
from schema import Documento


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/")
    args = ap.parse_args()

    erros = 0
    for p in sorted(Path(args.raw).glob("*.json")):
        try:
            Documento(**json.loads(p.read_text(encoding="utf-8")))
            print(f"[OK]  {p.name}")
        except Exception as e:
            erros += 1
            print(f"[BAD] {p.name}: {e}")
    raise SystemExit(1 if erros else 0)


if __name__ == "__main__":
    main()