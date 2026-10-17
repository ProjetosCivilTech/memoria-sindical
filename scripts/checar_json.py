from pathlib import Path
import json
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "data/DC 2013-2014.json")
t = p.read_text(encoding="utf-8")

try:
    json.loads(t)
    print("OK - JSON válido")
except json.JSONDecodeError as e:
    print(f"Erro: {e}")
    print(f"Posição: {e.pos}  (linha {e.lineno}, coluna {e.colno})")
    print()
    print("--- Linhas ao redor (a linha com <<< é onde o parser parou) ---")
    linhas = t.splitlines()
    ini = max(0, e.lineno - 6)
    fim = min(len(linhas), e.lineno + 3)
    for i in range(ini, fim):
        n = i + 1
        marca = "  <<<" if n == e.lineno else ""
        print(f"{n:4}| {linhas[i]}{marca}")