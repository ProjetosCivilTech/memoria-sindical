"""
Normaliza IDs canônicos nos JSONs de data/.

Aplica um mapa de merge (IDs duplicados/sinônimos → ID canônico único)
e regrava os arquivos. Faz backup antes.

Uso:
    python -m scripts.normalizar_ids --raw data/ --dry-run
    python -m scripts.normalizar_ids --raw data/
"""
import json
import argparse
import shutil
from pathlib import Path
from collections import Counter


# ================================================================
# MERGE — IDs duplicados/sinônimos → ID canônico único
# ================================================================

MERGE = {
    # Sinônimos por plural/singular
    "SIN_LIBERACAO_CONSELHOS":             "SIN_LIBERACAO_CONSELHO",

    # Conselho Postalistas (redundâncias)
    "SIN_LIBERACAO_CONSELHO_POSTALIS":     "SIN_LIBERACAO_CONSELHO",
    "SIN_LIBERACAO_CONSELHEIRO_POSTALIS":  "SIN_LIBERACAO_CONSELHO",
    "PRO_POSTALIS":                        "SIN_LIBERACAO_CONSELHO",

    # PCCS (typo e variações)
    "PRO_REVISAO_PCS":                     "PRO_REVISAO_PCCS",
    "PRO_PCCS":                            "PRO_REVISAO_PCCS",

    # Nomes incompletos
    "CON_ITENS_PROTECAO":                  "CON_ITENS_USO_PROTECAO",
    "CON_PROTECAO_BAIXA_UMIDADE":          "CON_ITENS_PROTECAO_BAIXA_UMIDADE",
    "SOC_FORNECIMENTO_CAT_LISA":           "SOC_FORNECIMENTO_CAT",
    "SIN_RELACAO_NOMINAL_EMPREGADOS":      "SIN_RELACAO_EMPREGADOS",
    "PRO_PRORROGACAO_REVISAO_DENUNCIA":    "PRO_PRORROGACAO_REVISAO",
    "SIN_PARCERIA_ASSOCIACOES":            "SIN_PARCERIA_ASSOCIACOES_RECREATIVAS",
    "PRO_PROCESSO_PERMANENTE_NEGOCIACAO":  "PRO_PROCESSO_PERMANENTE",
    "SOC_ACOMPANHANTE":                    "SOC_LICENCA_ACOMPANHANTE",
    "PRO_DIREITO_AMPLA_DEFESA":            "PRO_AMPLA_DEFESA",
    # Prefixo inconsistente (TEC_ vs CON_)
    "TEC_DISTRIBUICAO_DOMICILIARIA":       "CON_DISTRIBUICAO_DOMICILIARIA",
    # Variações de nome do mesmo tema
    "SOC_EMPREGADO_HIV":                   "SOC_EMPREGADO_VIVENDO_HIV",
    "SIN_PROMOCAO_EQUIDADE_GENERO":        "SIN_EQUIDADE_GENERO",
    "SIN_DIVERSIDADE_INCLUSAO":            "SIN_DIVERSIDADE",
    "PRO_ACOMPANHAMENTO_TST":              "PRO_ACOMPANHAMENTO_CUMPRIMENTO",
    "SOC_REGIME_CALAMIDADE":               "SOC_ESTADO_CALAMIDADE",

    # Órfãos mapeáveis
    "FIN_ABONO":                           "FIN_ABONO_SALARIAL",
    "FIN_ABONO_INDENIZATORIO":             "FIN_ABONO_SALARIAL",
    "FIN_AUMENTO_LINEAR":                  "FIN_REAJUSTE_SALARIAL",
    "FIN_COMPENSACAO_DIAS_PARADOS":        "FIN_COMPENSACAO_GREVE",
    "PRO_PAGAMENTO_DIAS_PARADOS":          "FIN_COMPENSACAO_GREVE",
    "FIN_DESCONTO_ASSISTENCIAL":           "SIN_DESCONTO_ASSISTENCIAL",
    "FIN_FOLGA_FIM_SEMANA":                "FIN_TRABALHO_FINS_SEMANA",
    "FIN_PRODUTIVIDADE_ANUAL":             "FIN_GRATIFICACAO_PRODUTIVIDADE",
    "PRO_ANISTIA":                         "SIN_ANISTIA",
    "PRO_PROMOCAO_MERECIMENTO":            "PRO_PROMOCAO_TEMPO_SERVICO",
    "PRO_PREENCHIMENTO_CARGOS":            "PRO_CONCURSO_PUBLICO",
    "PRO_REGULAMENTACAO_POSTAL":           "PRO_DEFESA_MONOPOLIO",
    "PRO_REVISAO_PUNICOES":                "SIN_REVOGACAO_SUSPENSOES",
}


# ================================================================
# NORMALIZAÇÃO
# ================================================================

def normalizar_documento(doc: dict) -> tuple[dict, Counter]:
    """Aplica o mapa MERGE. Retorna (doc_normalizado, relatorio)."""
    relatorio = Counter()
    for c in doc.get("clausulas", []):
        id_original = c.get("id_canonico")
        if id_original in MERGE:
            c["id_canonico"] = MERGE[id_original]
            relatorio[id_original] += 1
    return doc, relatorio


def processar(arq: Path, dry_run: bool) -> tuple[int, Counter]:
    doc = json.loads(arq.read_text(encoding="utf-8"))
    doc_norm, relatorio = normalizar_documento(doc)

    if not relatorio:
        return 0, Counter()

    if dry_run:
        return sum(relatorio.values()), relatorio

    backup = arq.with_suffix(arq.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(arq, backup)

    arq.write_text(
        json.dumps(doc_norm, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return sum(relatorio.values()), relatorio


# ================================================================
# MAIN
# ================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pasta = Path(args.raw)
    arquivos = sorted(pasta.glob("*.json"))

    print(f"Pasta: {pasta}")
    print(f"Arquivos: {len(arquivos)}")
    print(f"Regras no mapa: {len(MERGE)}\n")

    total_alteracoes = 0
    total_arquivos = 0
    relatorio_geral = Counter()

    for arq in arquivos:
        n, rel = processar(arq, args.dry_run)
        if n > 0:
            total_arquivos += 1
            total_alteracoes += n
            relatorio_geral.update(rel)
            prefixo = "[dry-run]" if args.dry_run else "[ok]"
            print(f"{prefixo} {arq.name}: {n} cláusulas normalizadas")

    print()
    print("=" * 80)
    print("RESUMO POR REGRA")
    print("=" * 80)
    for id_orig, n in relatorio_geral.most_common():
        destino = MERGE[id_orig]
        print(f"  {n:3}x  {id_orig:50}  ->  {destino}")

    print()
    print(f"Arquivos afetados: {total_arquivos}")
    print(f"Total de cláusulas com ID normalizado: {total_alteracoes}")


if __name__ == "__main__":
    main()