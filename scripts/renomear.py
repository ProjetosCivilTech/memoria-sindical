"""
Renomeia e organiza os JSONs de data/ seguindo o padrão:
    TIPO AAAA-AAAA [ENTIDADE].json

Uso:
    python -m scripts.renomear              # executa de verdade
    python -m scripts.renomear --dry-run    # só mostra o que faria
    python -m scripts.renomear --pasta data/raw
"""
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime


# ----------------------------------------------------------------
# Mapeamento: nome atual -> nome novo
# ----------------------------------------------------------------
RENOMEAR = {
    # Nomes fora do padrão
    "ACT-2017-2018.json":                  "ACT 2017-2018.json",
    "ACT 2024-2025.json":                  "ACT 2024-2025 FENTECT.json",
    "ACT 2024-2025 (FINDECT).json":        "ACT 2024-2025 FINDECT.json",
    "ACT 2000-2001.json":                  "DC 2000-2001.json",

    # Dissídios com nome por extenso
    "Dissídio Coletivo 2019-2021.json":    "DC 2020-2021.json",
    "Dissídio Coletivo 2013.json":         "DC 2013-2014 FENTECT.json",

    # ACT com dois anos no mesmo arquivo
    "ACT 1990 e ACT 1990 Suplementar.json": "ACT 1990.json",
}

# Arquivos que precisam ser divididos em dois (não renomeia, avisa)
PRECISA_DIVIDIR = {
    "ACT 1991 (parcial) e ACT 1992.json": {
        "motivo": "Contém dois documentos: DC 1991 (parcial) e ACT 1992",
        "sugestao": ["DC 1991.json", "ACT 1992.json"],
    },
}

# Padrão dos nomes já corretos
PADRAO_OK = [
    "ACT 1988-1989.json",
    "ACT 1993.json",
    "ACT 1994-1995.json",
    "ACT 1995-1996.json",
    "ACT 1997-1998.json",
    "ACT 1998-1999.json",
    "ACT 1999-2000.json",
    "ACT 2001-2002.json",
    "ACT 2002-2003.json",
    "ACT 2003-2004.json",
    "ACT 2004-2005.json",
    "ACT 2005-2006.json",
    "ACT 2007-2008.json",
    "ACT 2008-2009.json",
    "ACT 2009-2011.json",
    "ACT 2013-2014 FINDECT.json",
    "ACT 2014-2015.json",
    "ACT 2015-2016.json",
    "ACT 2016-2017.json",
    "ACT 2017-2018.json",
    "ACT 2018-2019.json",
    "ACT 2022-2023.json",
    "ACT 2023-2024.json",
    "ACT 2024-2025 FENTECT.json",
    "ACT 2024-2025 FINDECT.json",
    "DC 2011.json",
    "DC 2012-2013.json",
    "DC 2013-2014 FENTECT.json",
    "DC 2020-2021.json",
    "DC 2021-2022.json",
    "DC 2025-2026.json",
    "Cartilha 2020-2021.json",
]


def fazer_backup(pasta: Path, dry_run: bool):
    """Copia todos os JSONs para uma pasta de backup com timestamp."""
    if dry_run:
        return None
    backup = pasta / f"_backup_renomeacao_{datetime.now():%Y%m%d_%H%M%S}"
    backup.mkdir(parents=True, exist_ok=True)
    for p in pasta.glob("*.json"):
        shutil.copy2(p, backup / p.name)
    return backup


def listar_arquivos(pasta: Path):
    return sorted([p for p in pasta.glob("*.json") if not p.name.startswith("_")])


def renomear(pasta: Path, dry_run: bool):
    arquivos = listar_arquivos(pasta)
    print(f"📂 Pasta: {pasta}")
    print(f"📄 Encontrados: {len(arquivos)} JSONs\n")

    acoes = {"renomear": [], "manter": [], "dividir": [], "orfao": []}

    # 1. Identificar ações
    for arq in arquivos:
        nome = arq.name
        if nome in RENOMEAR:
            acoes["renomear"].append((nome, RENOMEAR[nome]))
        elif nome in PRECISA_DIVIDIR:
            acoes["dividir"].append((nome, PRECISA_DIVIDIR[nome]))
        elif nome in PADRAO_OK:
            acoes["manter"].append(nome)
        else:
            acoes["orfao"].append(nome)

    # 2. Verificar colisões
    destino_existentes = {p.name for p in arquivos}
    for antigo, novo in acoes["renomear"]:
        if novo in destino_existentes and novo != antigo:
            print(f"⚠️  COLISÃO: '{novo}' já existe. Renomeação de '{antigo}' seria bloqueada.")

    # 3. Relatório
    print("=" * 70)
    print(f"✅ Já estão no padrão: {len(acoes['manter'])}")
    print(f"🔄 Precisam ser renomeados: {len(acoes['renomear'])}")
    print(f"✂️  Precisam ser divididos: {len(acoes['dividir'])}")
    print(f"❓ Sem mapeamento: {len(acoes['orfao'])}")
    print("=" * 70)

    if acoes["manter"]:
        print("\n✅ Já no padrão:")
        for n in acoes["manter"]:
            print(f"   {n}")

    if acoes["renomear"]:
        print("\n🔄 A renomear:")
        for antigo, novo in acoes["renomear"]:
            print(f"   {antigo}")
            print(f"      ➜ {novo}")

    if acoes["dividir"]:
        print("\n✂️  Precisam ser divididos (NÃO serão tocados):")
        for nome, info in acoes["dividir"]:
            print(f"   {nome}")
            print(f"      Motivo: {info['motivo']}")
            print(f"      Sugestão: {info['sugestao']}")

    if acoes["orfao"]:
        print("\n❓ Sem mapeamento (NÃO serão tocados):")
        for n in acoes["orfao"]:
            print(f"   {n}")

    if dry_run:
        print("\n🔍 Modo dry-run: nenhuma alteração feita.")
        return

    # 4. Executar
    print("\n" + "=" * 70)
    print("🔧 Executando renomeações...")
    print("=" * 70)

    backup = fazer_backup(pasta, dry_run=False)
    if backup:
        print(f"💾 Backup em: {backup}\n")

    cont_ok = 0
    cont_erro = 0
    for antigo, novo in acoes["renomear"]:
        origem = pasta / antigo
        destino = pasta / novo
        if not origem.exists():
            print(f"❌ Não encontrado: {antigo}")
            cont_erro += 1
            continue
        if destino.exists() and destino != origem:
            print(f"⚠️  Colisão, pulando: {antigo} ➜ {novo}")
            cont_erro += 1
            continue
        origem.rename(destino)
        print(f"✅ {antigo} ➜ {novo}")
        cont_ok += 1

    print("\n" + "=" * 70)
    print(f"✅ Renomeados: {cont_ok}")
    print(f"❌ Erros: {cont_erro}")
    print("=" * 70)

    # 5. Estado final
    print("\n📂 Estado final:")
    for arq in listar_arquivos(pasta):
        print(f"   {arq.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default="data/", help="Pasta com os JSONs")
    ap.add_argument("--dry-run", action="store_true", help="Só mostra, não altera")
    args = ap.parse_args()

    pasta = Path(args.pasta)
    if not pasta.exists():
        print(f"❌ Pasta não encontrada: {pasta}")
        return

    renomear(pasta, args.dry_run)


if __name__ == "__main__":
    main()