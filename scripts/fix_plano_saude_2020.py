"""
Corrige o ID 'SOC_PLANO_SAUDE' no DC 2020-2021.json.

A cláusula "PLANO DE SAÚDE DOS EMPREGADOS DOS CORREIOS" (item X do
acórdão) é a transformação da cláusula 28 do ACT anterior
("Assistência Médica") — não uma cláusula nova. O TST a considerou
MANTIDA com nova redação (Correios Saúde → Postal Saúde).

Uso:
    python scripts/fix_plano_saude_2020.py
"""
import json
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "data" / "DC 2020-2021.json"

ID_ANTIGO = "SOC_PLANO_SAUDE"
ID_NOVO = "SOC_ASSISTENCIA_MEDICA"


def main():
    if not ARQUIVO.exists():
        print(f"[ERRO] Não encontrado: {ARQUIVO}")
        return

    doc = json.loads(ARQUIVO.read_text(encoding="utf-8"))

    # Encontra a cláusula
    encontradas = [
        (i, c) for i, c in enumerate(doc["clausulas"])
        if c.get("id_canonico") == ID_ANTIGO
    ]

    if not encontradas:
        print(f"[AVISO] Nenhuma cláusula com ID '{ID_ANTIGO}'")
        return

    print(f"Encontradas {len(encontradas)} cláusulas com '{ID_ANTIGO}':")
    print()

    for pos, c in encontradas:
        print(f"  Posição {pos}:")
        print(f"    numero: {c.get('numero_clausula_original')}")
        print(f"    titulo: {c.get('titulo_original')}")
        print(f"    texto:  {c.get('texto', '')[:150]}...")
        print()

        # Renomeia
        doc["clausulas"][pos]["id_canonico"] = ID_NOVO

        # Adiciona observação explicativa
        obs_atual = doc["clausulas"][pos].get("observacao", "")
        doc["clausulas"][pos]["observacao"] = (
            obs_atual + " " if obs_atual else ""
        ) + (
            "[Transformação do modelo Correios Saúde → Postal Saúde. "
            "O TST considerou esta cláusula como MANTIDA, com nova redação.]"
        )

    # Adiciona nota metodológica
    meta = doc.setdefault("notas_metodologicas", [])
    meta.append({
        "tipo": "FIX_TRANSFORMACAO",
        "descricao": (
            f"ID '{ID_ANTIGO}' renomeado para '{ID_NOVO}'. "
            "A cláusula é transformação da cláusula 28 do ACT anterior "
            "(Correios Saúde → Postal Saúde), mantida pelo TST."
        ),
    })

    # Salva
    ARQUIVO.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ Salvo: {ARQUIVO.name}")

    # Validação
    from collections import Counter
    ids = [c.get("id_canonico") for c in doc["clausulas"]]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    print(f"Duplicatas: {dup if dup else 'nenhuma'}")
    print(f"Total de cláusulas: {len(ids)}")
    print(f"IDs únicos: {len(set(ids))}")


if __name__ == "__main__":
    main()