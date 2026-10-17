"""
Corrige ID duplicado em DC 2019-2021.json.

Problema: 'SOC_PRORROGACAO_LICENCA_MATERNIDADE' aparece 2x
Solução: renomeia a cláusula de "LICENÇA MATERNIDADE" (original)
         para SOC_LICENCA_MATERNIDADE, mantendo
         SOC_PRORROGACAO_LICENCA_MATERNIDADE para a "prorrogação"

Uso:
    python scripts/fix_duplicata_2019.py
"""
import json
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "data" / "DC 2019-2021.json"

ID_DUPLICADO = "SOC_PRORROGACAO_LICENCA_MATERNIDADE"
ID_NOVO = "SOC_LICENCA_MATERNIDADE"


def main():
    if not ARQUIVO.exists():
        print(f"[ERRO] Arquivo não encontrado: {ARQUIVO}")
        return

    doc = json.loads(ARQUIVO.read_text(encoding="utf-8"))

    # Encontra todas as cláusulas com o ID duplicado
    duplicadas = [
        (i, c) for i, c in enumerate(doc["clausulas"])
        if c.get("id_canonico") == ID_DUPLICADO
    ]

    print(f"Encontradas {len(duplicadas)} cláusulas com ID '{ID_DUPLICADO}':")
    print()
    for pos, c in duplicadas:
        print(f"  Posição {pos}:")
        print(f"    numero: {c.get('numero_clausula_original')}")
        print(f"    titulo: {c.get('titulo_original')}")
        print(f"    texto:  {c.get('texto', '')[:120]}...")
        print()

    if len(duplicadas) != 2:
        print(f"[AVISO] Esperado 2 duplicatas, encontradas {len(duplicadas)}")
        return

    # Regra: a cláusula cujo título NÃO contém "prorrogação"
    # ou "prorrogacao" é a "licença maternidade" original
    candidata_original = None
    candidata_extensao = None

    for pos, c in duplicadas:
        titulo_lower = (c.get("titulo_original") or "").lower()
        if "prorroga" in titulo_lower:
            candidata_extensao = (pos, c)
        else:
            candidata_original = (pos, c)

    if not candidata_original:
        # Fallback: usa a primeira
        candidata_original = duplicadas[0]
        candidata_extensao = duplicadas[1]

    pos_original, _ = candidata_original

    # Renomeia
    print(f"Renomeando posição {pos_original} de:")
    print(f"  '{ID_DUPLICADO}' → '{ID_NOVO}'")
    print(f"  Título: {doc['clausulas'][pos_original].get('titulo_original')}")
    print()

    doc["clausulas"][pos_original]["id_canonico"] = ID_NOVO

    # Adiciona metadado de correção
    meta = doc.setdefault("notas_metodologicas", [])
    meta.append({
        "tipo": "FIX_DUPLICATA",
        "descricao": (
            f"ID '{ID_DUPLICADO}' estava duplicado. "
            f"Cláusula 'LICENÇA MATERNIDADE' (pos {pos_original}) "
            f"renomeada para '{ID_NOVO}'."
        ),
    })

    # Salva
    ARQUIVO.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ Salvo: {ARQUIVO.name}")

    # Valida
    from collections import Counter
    ids = [c.get("id_canonico") for c in doc["clausulas"]]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    print(f"Duplicatas restantes: {dup if dup else 'nenhuma'}")
    print(f"Total de cláusulas: {len(ids)}")
    print(f"IDs únicos: {len(set(ids))}")


if __name__ == "__main__":
    main()