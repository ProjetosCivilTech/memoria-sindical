"""
Unifica os 3 documentos de 2013-2014 (DC, FINDECT, Unificado).

Categoriza as diferenças DC vs FINDECT em:
  - MATERIAIS: mudam a regra (11 documentadas)
  - PARAFRASES: mesma regra, texto mais curto (9 conhecidas)
  - A INVESTIGAR: não mapeadas (esperado: 0)
  - COSMÉTICAS: similaridade alta, sem relevância

Gera:
  data/build/2013-2014_consolidado.json  — visão unificada por ID canônico
  data/build/2013-2014_divergencias.md   — relatório das divergências

Uso:
    python -m scripts.comparar_trio_2013
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher


DOCS = {
    "DC":        Path("data/DC 2013-2014.json"),
    "FINDECT":   Path("data/ACT 2013-2014 FINDECT.json"),
    "Unificado": Path("data/ACT 2013-2014 Unificado.json"),
}

LIMIAR_SIMILARIDADE = 0.90


# ================================================================
# CLASSIFICAÇÃO DE DIVERGÊNCIAS
# ================================================================

# Divergências MATERIAIS (mudam a regra de verdade)
DIVERGENCIAS_MATERIAIS = {
    "SIN_LIBERACAO_DIRIGENTES",             # 11 fixos vs escalonado por base
    "FIN_REAJUSTE_SALARIAL",                # DC: 8%+6,27% | FINDECT: só 8%
    "PRO_VIGENCIA",                         # DC: 4 anos | FINDECT: 1 ano
    "PRO_PROCESSO_PERMANENTE_NEGOCIACAO",   # cronograma fixo vs mesas amplas
    "SIN_ANISTIA",                          # comissão FENTECT vs Federação filiada
    "SIN_DELEGADO_SINDICAL",                # avaliação FENTECT vs Sindicato
    "SIN_FORNECIMENTO_MANUAL",              # + LAI + termo de confidencialidade
    "PRO_GARANTIAS_EMPREGADO_ESTUDANTE",    # FENTECT e sindicatos vs Sindicato
    "FIN_PLR",                              # FENTECT vs Sindicato ou Federação
    "SIN_QUADRO_AVISOS",                    # entidades FENTECT vs Sindicato
    "SOC_SAUDE_EMPREGADO",                  # apoio FENTECT vs entidades
}

# Paráfrases conhecidas (mesma regra, FINDECT com texto mais curto)
PARAFRASES_CONHECIDAS = {
    "PRO_ACESSO_DEPENDENCIAS",
    "FIN_ACUMULACAO_VANTAGENS",
    "TEC_DISTRIBUICAO_DOMICILIARIA",
    "SOC_ITENS_PROTECAO",
    "FIN_ADICIONAL_NOTURNO",
    "FIN_ANTECIPACAO_GRATIFICACAO_NATALINA",
    "FIN_REEMBOLSO_CRECHE_BABA",
    "SOC_ACOMPANHANTE",
    "FIN_ADIANTAMENTO_FERIAS",
}


# ================================================================
# CARREGAMENTO
# ================================================================

def carregar(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Não encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ================================================================
# NORMALIZAÇÃO DE TEXTO
# ================================================================

EQUIVALENCIAS = {
    r"\b§\s*": "paragrafo ",
    r"\bart\.\s*": "artigo ",
    r"\binc\.\s*": "inciso ",
    r"\bn[ºo°]\.?\s*": "numero ",
    r"\br\$\.?\s*": "r$ ",
    r"\bdr's\b": "drs",
    r"\bdr s\b": "drs",
    r"\bfentect\b": "federacao",
    r"\bfindect\b": "federacao",
    r"\bsindicato dos empregados dos correios\b": "sindicato",
    r"\bfederacao ao qual o sindicato estiver filiado\b": "federacao",
    r"\bfederacao ao qual o sindicato esteja filiado\b": "federacao",
    r"\bfederacao ou federacoes\b": "federacao",
    r"\bsindicato ou federacao\b": "sindicato",
    r"\bcorreios saude\b": "correios saude",
    r"\bcorreiosaude\b": "correios saude",
}


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    t = texto.lower()
    for padrao, sub in EQUIVALENCIAS.items():
        t = re.sub(padrao, sub, t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def similaridade(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


# ================================================================
# INDEXAÇÃO
# ================================================================

def indexar_por_id(docs: dict) -> dict:
    por_id = defaultdict(lambda: {"fontes": {}, "meta": {}})
    for nome, doc in docs.items():
        for c in doc.get("clausulas", []):
            cid = c.get("id_canonico")
            if not cid:
                continue
            por_id[cid]["fontes"][nome] = c
            if not por_id[cid]["meta"]:
                por_id[cid]["meta"] = {
                    "titulo_original": c.get("titulo_original"),
                    "pagina_referencia": c.get("pagina_referencia"),
                }
    return por_id


# ================================================================
# COMPARAÇÃO
# ================================================================

def comparar_dc_vs_findect(por_id: dict) -> tuple[list, list, list, int]:
    """Compara DC vs FINDECT.
    Retorna (materiais, parafrases, investigar, cosmeticas).
    """
    materiais, parafrases, investigar = [], [], []
    cosmeticas = 0

    for cid, dados in por_id.items():
        fontes = dados["fontes"]
        if "DC" not in fontes or "FINDECT" not in fontes:
            continue

        t_dc = normalizar(fontes["DC"].get("texto", ""))
        t_fd = normalizar(fontes["FINDECT"].get("texto", ""))
        score = similaridade(t_dc, t_fd)

        if score >= LIMIAR_SIMILARIDADE:
            cosmeticas += 1
            continue

        registro = {
            "id": cid,
            "titulo": dados["meta"].get("titulo_original"),
            "score": round(score, 3),
            "texto_DC": fontes["DC"].get("texto"),
            "texto_FINDECT": fontes["FINDECT"].get("texto"),
        }

        if cid in DIVERGENCIAS_MATERIAIS:
            materiais.append(registro)
        elif cid in PARAFRASES_CONHECIDAS:
            parafrases.append(registro)
        else:
            investigar.append(registro)

    for lista in (materiais, parafrases, investigar):
        lista.sort(key=lambda d: d["score"])

    return materiais, parafrases, investigar, cosmeticas


# ================================================================
# CONSOLIDADO
# ================================================================

def gerar_consolidado(por_id: dict, materiais: list, parafrases: list) -> dict:
    ids_materiais = {d["id"] for d in materiais}
    ids_parafrases = {d["id"] for d in parafrases}
    ids_divergentes = ids_materiais | ids_parafrases

    consolidado = {
        "grupo": "2013-2014",
        "documentos_fonte": {nome: str(path) for nome, path in DOCS.items()},
        "total_ids": len(por_id),
        "total_clausulas": sum(len(v["fontes"]) for v in por_id.values()),
        "total_divergencias": len(ids_divergentes),
        "total_materiais": len(ids_materiais),
        "total_parafrases": len(ids_parafrases),
        "clausulas": [],
    }

    for cid in sorted(por_id.keys()):
        dados = por_id[cid]
        fontes = dados["fontes"]

        texto_ref = (
            fontes.get("DC", {}).get("texto")
            or fontes.get("FINDECT", {}).get("texto")
            or fontes.get("Unificado", {}).get("texto")
        )

        consolidado["clausulas"].append({
            "id_canonico": cid,
            "titulo_original": dados["meta"].get("titulo_original"),
            "presente_em": sorted(fontes.keys()),
            "texto_consolidado": texto_ref,
            "divergencia": cid in ids_divergentes,
            "divergencia_material": cid in ids_materiais,
            "parafrase": cid in ids_parafrases,
            "numero_original": {
                n: fontes[n].get("numero_clausula_original")
                for n in fontes
            },
        })

    return consolidado


# ================================================================
# RELATÓRIO MARKDOWN
# ================================================================

def _bloco(d: dict) -> list[str]:
    return [
        f"## `{d['id']}` — {d['titulo']}",
        f"**Score:** {d['score']}\n",
        "**DC (FENTECT/TST):**",
        f"> {d['texto_DC']}\n",
        "**FINDECT:**",
        f"> {d['texto_FINDECT']}\n",
        "---\n",
    ]


def gerar_markdown(materiais: list, parafrases: list, investigar: list, cosmeticas: int) -> str:
    linhas = ["# Divergências DC 2013-2014 vs ACT FINDECT\n"]
    linhas.append(f"- **Materiais** (mudam a regra): {len(materiais)}")
    linhas.append(f"- **Paráfrases** (mesma regra, texto mais curto): {len(parafrases)}")
    linhas.append(f"- **A investigar** (não mapeadas): {len(investigar)}")
    linhas.append(f"- **Cosméticas** (score >= {LIMIAR_SIMILARIDADE}): {cosmeticas}\n")
    linhas.append("---\n")

    if materiais:
        linhas.append("# 🔴 Divergências materiais\n")
        for d in materiais:
            linhas.extend(_bloco(d))

    if parafrases:
        linhas.append("# 🟡 Paráfrases conhecidas\n")
        linhas.append("Mesma regra, texto do FINDECT mais resumido.\n")
        for d in parafrases:
            linhas.extend(_bloco(d))

    if investigar:
        linhas.append("# ⚠️ A investigar\n")
        linhas.append("Divergências **não mapeadas** anteriormente.\n")
        for d in investigar:
            linhas.extend(_bloco(d))

    return "\n".join(linhas)


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 90)
    print("UNIFICAÇÃO 2013-2014: DC + FINDECT + Unificado")
    print("=" * 90)

    docs = {nome: carregar(path) for nome, path in DOCS.items()}
    por_id = indexar_por_id(docs)

    total_3 = sum(1 for v in por_id.values() if len(v["fontes"]) == 3)
    total_2 = sum(1 for v in por_id.values() if len(v["fontes"]) == 2)
    total_1 = sum(1 for v in por_id.values() if len(v["fontes"]) == 1)

    print(f"\n📊 Total de IDs canônicos únicos: {len(por_id)}")
    print(f"   Presentes em todos os 3: {total_3}")
    print(f"   Presentes em 2:          {total_2}")
    print(f"   Presentes em 1 só:       {total_1}")

    materiais, parafrases, investigar, cosmeticas = comparar_dc_vs_findect(por_id)

    print(f"\n🔴 Divergências MATERIAIS:      {len(materiais)}")
    print(f"🟡 Paráfrases conhecidas:        {len(parafrases)}")
    print(f"🔍 A INVESTIGAR:                 {len(investigar)}")
    print(f"✨ Cosmeticas (>= {LIMIAR_SIMILARIDADE}):        {cosmeticas}")

    # Salvar
    out_dir = Path("data/build")
    out_dir.mkdir(parents=True, exist_ok=True)

    consolidado = gerar_consolidado(por_id, materiais, parafrases)
    out_json = out_dir / "2013-2014_consolidado.json"
    out_json.write_text(
        json.dumps(consolidado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✅ Salvo: {out_json}")

    if materiais or parafrases or investigar:
        out_md = out_dir / "2013-2014_divergencias.md"
        out_md.write_text(
            gerar_markdown(materiais, parafrases, investigar, cosmeticas),
            encoding="utf-8",
        )
        print(f"✅ Salvo: {out_md}")

    # Resumo por fonte
    print("\n" + "=" * 90)
    print("CLÁUSULAS POR FONTE")
    print("=" * 90)
    for nome, doc in docs.items():
        print(f"  {nome:12}  {len(doc.get('clausulas', [])):3} cláusulas")

    # Divergências materiais
    if materiais:
        print("\n" + "=" * 90)
        print("🔴 DIVERGÊNCIAS MATERIAIS")
        print("=" * 90)
        for d in materiais:
            print(f"  {d['score']:.2f}  {d['id']:55}  {d['titulo']}")

    # Paráfrases
    if parafrases:
        print("\n" + "=" * 90)
        print("🟡 PARÁFRASES CONHECIDAS")
        print("=" * 90)
        for d in parafrases:
            print(f"  {d['score']:.2f}  {d['id']:55}  {d['titulo']}")

    # Investigar
    if investigar:
        print("\n" + "=" * 90)
        print("⚠️  A INVESTIGAR (não mapeadas antes)")
        print("=" * 90)
        for d in investigar:
            print(f"  {d['score']:.2f}  {d['id']:55}  {d['titulo']}")
    else:
        print("\n✅ Nenhuma divergência não mapeada.")

    print()


if __name__ == "__main__":
    main()