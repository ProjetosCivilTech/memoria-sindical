"""Investiga onde aparecem IDs específicos e seus títulos."""
import json
from pathlib import Path

ALVOS = {
    "FIN_GQP", "FIN_GIP", "FIN_GACT", "FIN_AADC",
    "FIN_TABELA_SALARIAL", "FIN_PROTECAO_SALARIAL",
}

pasta = Path("data")
for arq in sorted(pasta.glob("*.json")):
    try:
        doc = json.loads(arq.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[erro] {arq.name}: {e}")
        continue

    for c in doc.get("clausulas", []):
        cid = c.get("id_canonico")
        if cid in ALVOS:
            titulo = (c.get("titulo_original") or "")[:70]
            texto = (c.get("texto") or "")[:120]
            print(f"{arq.name:35} | {cid:25} | {titulo}")
            print(f"   → {texto}")
            print()