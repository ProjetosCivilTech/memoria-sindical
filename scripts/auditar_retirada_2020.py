"""
Auditoria da retirada de cláusulas entre 2019-2021 e 2020-2021.

Compara o DC 2019-2021 (79 cláusulas) com o DC 2020-2021 (29 cláusulas)
para confirmar o número real de cláusulas retiradas pelo TST no
julgamento do dissídio DC 1001203-57.2020.5.00.0000.

Uso:
    python scripts/auditar_retirada_2020.py
"""
import json
from pathlib import Path
from datetime import datetime


RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
SAIDA = DATA_DIR / "export" / "auditoria_2020.txt"


# ================================================================
# DOCUMENTOS A COMPARAR
# Ordem de prioridade — o primeiro existente é usado
# ================================================================

DOCUMENTO_ANTES = [
    "DC 2019-2021.json",
]

DOCUMENTO_DEPOIS = [
    "DC 2020-2021.json",
]


# ================================================================
# CARREGAMENTO
# ================================================================

def encontrar_documento(candidatos: list) -> str | None:
    """Retorna o primeiro nome de arquivo que existe em data/."""
    for nome in candidatos:
        if (DATA_DIR / nome).exists():
            return nome
    return None


def carregar_documento(nome_arquivo: str) -> dict | None:
    """Carrega um JSON e retorna o dict completo."""
    caminho = DATA_DIR / nome_arquivo
    if not caminho.exists():
        return None

    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERRO] {nome_arquivo}: {e}")
        return None


def indexar_por_id(doc: dict) -> dict:
    """Retorna {id_canonico: clausula}."""
    return {
        c.get("id_canonico"): c
        for c in doc.get("clausulas", [])
        if c.get("id_canonico")
    }


# ================================================================
# COMPARAÇÃO
# ================================================================

def comparar(antes: dict, depois: dict) -> dict:
    """Compara dois conjuntos de cláusulas e retorna análise."""
    ids_antes = set(antes.keys())
    ids_depois = set(depois.keys())

    retiradas = sorted(ids_antes - ids_depois)
    novas = sorted(ids_depois - ids_antes)
    mantidas = sorted(ids_antes & ids_depois)

    return {
        "total_antes": len(ids_antes),
        "total_depois": len(ids_depois),
        "retiradas": retiradas,
        "mantidas": mantidas,
        "novas": novas,
    }


# ================================================================
# RELATÓRIO
# ================================================================

def imprimir_relatorio(analise: dict, nome_antes: str, nome_depois: str):
    print()
    print("=" * 100)
    print("AUDITORIA — RETIRADA DE CLÁUSULAS 2020")
    print("=" * 100)
    print(f"  ANTES:  {nome_antes}")
    print(f"  DEPOIS: {nome_depois}")
    print()
    print(f"  Cláusulas antes:    {analise['total_antes']}")
    print(f"  Cláusulas depois:   {analise['total_depois']}")
    print(f"  Retiradas:          {len(analise['retiradas'])}")
    print(f"  Mantidas:           {len(analise['mantidas'])}")
    print(f"  Novas:              {len(analise['novas'])}")

    if analise["retiradas"]:
        print()
        print("=" * 100)
        print(f"CLÁUSULAS RETIRADAS ({len(analise['retiradas'])}):")
        print("=" * 100)
        for cid in analise["retiradas"]:
            titulo = analise["titulos_antes"].get(cid, "?")
            print(f"  X  {cid:55} {titulo[:60]}")

    if analise["novas"]:
        print()
        print("=" * 100)
        print(f"CLÁUSULAS NOVAS ({len(analise['novas'])}):")
        print("=" * 100)
        for cid in analise["novas"]:
            titulo = analise["titulos_depois"].get(cid, "?")
            print(f"  +  {cid:55} {titulo[:60]}")


def salvar_relatorio(analise: dict, nome_antes: str, nome_depois: str):
    """Salva o relatório em texto."""
    SAIDA.parent.mkdir(parents=True, exist_ok=True)

    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("AUDITORIA — RETIRADA DE CLÁUSULAS 2020\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"ANTES:  {nome_antes}\n")
        f.write(f"DEPOIS: {nome_depois}\n\n")

        f.write(f"Cláusulas antes:  {analise['total_antes']}\n")
        f.write(f"Cláusulas depois: {analise['total_depois']}\n")
        f.write(f"Retiradas:        {len(analise['retiradas'])}\n")
        f.write(f"Mantidas:         {len(analise['mantidas'])}\n")
        f.write(f"Novas:            {len(analise['novas'])}\n\n")

        f.write("=" * 100 + "\n")
        f.write("CLÁUSULAS RETIRADAS\n")
        f.write("=" * 100 + "\n\n")
        for cid in analise["retiradas"]:
            titulo = analise["titulos_antes"].get(cid, "?")
            f.write(f"  {cid:55} {titulo}\n")

        f.write("\n")
        f.write("=" * 100 + "\n")
        f.write("CLÁUSULAS MANTIDAS\n")
        f.write("=" * 100 + "\n\n")
        for cid in analise["mantidas"]:
            titulo = analise["titulos_depois"].get(cid, "?")
            f.write(f"  {cid:55} {titulo}\n")

        if analise["novas"]:
            f.write("\n")
            f.write("=" * 100 + "\n")
            f.write("CLÁUSULAS NOVAS\n")
            f.write("=" * 100 + "\n\n")
            for cid in analise["novas"]:
                titulo = analise["titulos_depois"].get(cid, "?")
                f.write(f"  {cid:55} {titulo}\n")

    print(f"\n📄 Relatório salvo em: {SAIDA}")


# ================================================================
# MAIN
# ================================================================

def main():
    print()
    print("🔍 AUDITORIA DE RETIRADA DE CLÁUSULAS — DC 2019-2021 vs DC 2020-2021")
    print()

    # Encontra os documentos
    nome_antes = encontrar_documento(DOCUMENTO_ANTES)
    nome_depois = encontrar_documento(DOCUMENTO_DEPOIS)

    if not nome_antes:
        print("[ERRO] Nenhum documento ANTES encontrado.")
        print(f"       Tentados: {DOCUMENTO_ANTES}")
        print()
        print("Arquivos disponíveis em data/:")
        for arq in sorted(DATA_DIR.glob("*.json")):
            print(f"  - {arq.name}")
        return

    if not nome_depois:
        print("[ERRO] Nenhum documento DEPOIS encontrado.")
        print(f"       Tentados: {DOCUMENTO_DEPOIS}")
        return

    # Carrega
    doc_antes = carregar_documento(nome_antes)
    doc_depois = carregar_documento(nome_depois)

    if not doc_antes or not doc_depois:
        print("[ERRO] Falha ao carregar documentos.")
        return

    # Indexa
    ids_antes = indexar_por_id(doc_antes)
    ids_depois = indexar_por_id(doc_depois)

    print(f"📄 Documento ANTES:  {nome_antes} ({len(ids_antes)} cláusulas)")
    print(f"📄 Documento DEPOIS: {nome_depois} ({len(ids_depois)} cláusulas)")

    # Compara
    analise = comparar(ids_antes, ids_depois)

    # Adiciona títulos
    analise["titulos_antes"] = {
        cid: doc_antes["clausulas"][i].get("titulo_original", "?")
        for i, c in enumerate(doc_antes["clausulas"])
        if c.get("id_canonico")
        for cid in [c["id_canonico"]]
    }
    analise["titulos_depois"] = {
        cid: doc_depois["clausulas"][i].get("titulo_original", "?")
        for i, c in enumerate(doc_depois["clausulas"])
        if c.get("id_canonico")
        for cid in [c["id_canonico"]]
    }

    # Imprime
    imprimir_relatorio(analise, nome_antes, nome_depois)

    # Salva
    salvar_relatorio(analise, nome_antes, nome_depois)

    # Validação contra o acórdão
    print()
    print("=" * 100)
    print("VALIDAÇÃO CONTRA O ACÓRDÃO (TST-DC 1001203-57.2020.5.00.0000)")
    print("=" * 100)
    print(f"  Esperado: 79 → 29 = 50 retiradas")
    print(f"  Obtido:   {analise['total_antes']} → {analise['total_depois']} = "
          f"{len(analise['retiradas'])} retiradas")

    ok_antes = analise["total_antes"] == 79
    ok_depois = analise["total_depois"] == 29
    ok_retiradas = len(analise["retiradas"]) == 50

    if ok_antes and ok_depois and ok_retiradas:
        print(f"  Status:   ✅ CORRETO")
    else:
        print(f"  Status:   ⚠️  DIVERGÊNCIA")
        if not ok_antes:     print(f"            - Total antes deveria ser 79")
        if not ok_depois:    print(f"            - Total depois deveria ser 29")
        if not ok_retiradas: print(f"            - Retiradas deveriam ser 50")


if __name__ == "__main__":
    main()