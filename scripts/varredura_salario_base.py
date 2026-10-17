"""
Varre os 36 JSONs em busca de menções a salário-base, piso, tabela salarial
e valores específicos por referência (NM-01, NS-01, etc.).

Uso:
    python scripts/varredura_salario_base.py
"""
import json
import re
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"

PALAVRAS_CHAVE = [
    "salário-base",
    "salario-base",
    "salário base",
    "piso salarial",
    "tabela salarial",
    "referência salarial",
    "referencia salarial",
    "NM-01",
    "NS-01",
    "vencimento básico",
    "vencimento basico",
]

REGEX_RS = re.compile(r"R\$\s*([\d.]+,\d{2})")


def analisar_documento(arq: Path):
    try:
        doc = json.loads(arq.read_text(encoding="utf-8"))
    except Exception as e:
        return {"erro": str(e)}

    achados = {
        "arquivo": arq.name,
        "ano": None,
        "tipo": None,
        "clausulas_com_salario_base": [],
        "valores_rs": [],
    }

    meta = doc.get("metadados_documento", {})
    achados["ano"] = meta.get("ano_inicio")
    achados["tipo"] = meta.get("tipo")

    for c in doc.get("clausulas", []):
        texto = (c.get("texto") or "") + " " + (c.get("titulo_original") or "")
        cid = c.get("id_canonico") or "?"

        for palavra in PALAVRAS_CHAVE:
            if palavra.lower() in texto.lower():
                achados["clausulas_com_salario_base"].append({
                    "id": cid,
                    "titulo": c.get("titulo_original"),
                    "trecho": texto[:200],
                })
                break

        valores = REGEX_RS.findall(texto)
        for v in valores:
            achados["valores_rs"].append({
                "id": cid,
                "valor": "R$ " + v,
            })

    return achados


def main():
    print("=" * 90)
    print("VARREDURA -- SALARIO-BASE, PISO E TABELA SALARIAL NOS 36 JSONs")
    print("=" * 90)
    print()

    arquivos = sorted(DATA_DIR.glob("*.json"))
    total_com_salario = 0
    total_com_valores = 0

    for arq in arquivos:
        resultado = analisar_documento(arq)
        if "erro" in resultado:
            print(f"[ERRO] {arq.name}: {resultado['erro']}")
            continue

        n_clausulas = len(resultado["clausulas_com_salario_base"])
        n_valores = len(resultado["valores_rs"])

        if n_clausulas > 0 or n_valores > 0:
            total_com_salario += 1 if n_clausulas > 0 else 0
            total_com_valores += 1 if n_valores > 0 else 0

            print(f"\n[ARQ] {resultado['arquivo']}  ({resultado['tipo']} {resultado['ano']})")
            print(f"      Clausulas com termos-chave: {n_clausulas}")
            print(f"      Valores em R$ encontrados:  {n_valores}")

            for c in resultado["clausulas_com_salario_base"][:3]:
                trecho = c['trecho'].replace('\n', ' ')[:120]
                print(f"      -> [{c['id']}] {trecho}...")

            for v in resultado["valores_rs"][:5]:
                print(f"      -> [{v['id']}] {v['valor']}")

    print()
    print("=" * 90)
    print(f"RESUMO: {total_com_salario} arquivos com termos-chave, "
          f"{total_com_valores} arquivos com valores em R$")
    print("=" * 90)


if __name__ == "__main__":
    main()