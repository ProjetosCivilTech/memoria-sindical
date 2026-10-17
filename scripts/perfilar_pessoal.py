# -*- coding: utf-8 -*-
"""
perfilar_pessoal.py — Carrega, limpa e perfila o CSV de pessoal dos Correios.

Saída:
    dados/export/_pessoal_limpo.parquet   (para análises rápidas)
    dados/export/_perfil.txt              (relatório de perfil)

Uso no Spyder:
    %cd F:\\AUTOMAÇÕES\\projeto_memoria_sindicato
    %run scripts/perfilar_pessoal.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np

RAIZ = Path(r"F:\AUTOMAÇÕES\projeto_memoria_sindicato")
CSV  = RAIZ / "dados" / "export" / "pessoal_correios.csv"
SAIDA_DIR = RAIZ / "dados" / "export"
SAIDA_PARQUET = SAIDA_DIR / "_pessoal_limpo.parquet"
SAIDA_PERFIL  = SAIDA_DIR / "_perfil.txt"

# ---------------------------------------------------------------------------
# 1. CARREGAR — testa encodings até funcionar
# ---------------------------------------------------------------------------

def carregar_csv(caminho: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(
                caminho,
                sep=";",               # Correios costuma usar ; em CSV grande
                encoding=enc,
                dtype=str,             # carrega tudo como texto primeiro
                low_memory=False,
                on_bad_lines="warn",
            )
            print(f"[OK] Carregado com encoding={enc!r}")
            print(f"     {len(df):,} linhas | {len(df.columns)} colunas")
            return df
        except UnicodeDecodeError:
            continue
    raise SystemExit("[ERRO] Nenhum encoding funcionou. Abra o CSV num editor "
                     "e confirme o separador (vírgula, ponto-e-vírgula, tab).")


# ---------------------------------------------------------------------------
# 2. LIMPAR NOMES DE COLUNA
# ---------------------------------------------------------------------------

def limpar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    mapa = {
        "LOCAL DE EXERCICIO":  "local_exercicio",
        "UF":                  "uf",
        "CPF":                 "cpf_hash",       # já vem anonimizado
        "CARGO":               "cargo",
        "FUNCAO":              "funcao",
        "ESPECIALIDADE":       "especialidade",
        "SE":                  "se",
        "LOTACAO":             "lotacao",
        "REFERENCIA":          "referencia",
        "SITUACAO":            "situacao",
        "JORNADA/CARGA HORÃ\u0081RIA": "jornada",
        "JORNADA/CARGA HORÁRIA":       "jornada",
        "ADMISSAO":            "admissao",
        "DESLIGAMENTO":        "desligamento",
    }
    df = df.rename(columns={c: c.strip() for c in df.columns})
    # remove BOM / espaços residuais
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
    # aplica mapa (o que bater)
    df = df.rename(columns={k: v for k, v in mapa.items() if k in df.columns})
    # fallback: se sobrou algum nome estranho, normaliza
    df.columns = [c.lower()
                    .replace(" ", "_")
                    .replace("ç", "c")
                    .replace("ã", "a")
                    .replace("á", "a")
                    .replace("é", "e")
                    .replace("í", "i")
                    .replace("ó", "o")
                    .replace("ú", "u")
                    .replace("\u0081", "")
                  for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# 3. PARSE DE DATAS
# ---------------------------------------------------------------------------

def parse_data(serie: pd.Series) -> pd.Series:
    """Aceita dd/mm/aaaa e vazio como NaT."""
    return pd.to_datetime(serie, format="%d/%m/%Y", errors="coerce")


def tratar_datas(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("admissao", "desligamento"):
        if col in df.columns:
            df[col] = parse_data(df[col])
    # datas impossíveis
    if "admissao" in df.columns:
        hoje = pd.Timestamp.today()
        futuras = (df["admissao"] > hoje).sum()
        if futuras:
            print(f"[AVISO] {futuras} admissões no futuro")
    if {"admissao", "desligamento"} <= set(df.columns):
        invertidas = (df["desligamento"] < df["admissao"]).sum()
        if invertidas:
            print(f"[AVISO] {invertidas} desligamentos antes da admissão")
    return df


# ---------------------------------------------------------------------------
# 4. PERFIL
# ---------------------------------------------------------------------------

def perfil(df: pd.DataFrame) -> str:
    L = []
    L.append("=" * 78)
    L.append("PERFIL — pessoal_correios.csv")
    L.append("=" * 78)
    L.append(f"Linhas:  {len(df):,}")
    L.append(f"Colunas: {len(df.columns)} -> {list(df.columns)}")
    L.append("")

    # Nulos
    L.append("--- NULOS por coluna (%) ---")
    for c in df.columns:
        pct = df[c].isna().mean() * 100
        L.append(f"  {c:<18} {pct:>6.2f}%")
    L.append("")

    # Datas
    if "admissao" in df.columns:
        ad = df["admissao"].dropna()
        L.append(f"--- ADMISSAO ---")
        L.append(f"  min:  {ad.min().date()}")
        L.append(f"  max:  {ad.max().date()}")
        L.append(f"  válidas: {len(ad):,} ({len(ad)/len(df)*100:.2f}%)")
    if "desligamento" in df.columns:
        dg = df["desligamento"].dropna()
        L.append(f"--- DESLIGAMENTO ---")
        L.append(f"  min:  {dg.min().date()}")
        L.append(f"  max:  {dg.max().date()}")
        L.append(f"  válidas: {len(dg):,} ({len(dg)/len(df)*100:.2f}%)")
    L.append("")

    # Categóricas — top 15
    for c in ("situacao", "uf", "cargo", "funcao", "especialidade",
              "referencia", "jornada"):
        if c in df.columns:
            L.append(f"--- {c.upper()} (top 15) ---")
            vc = df[c].value_counts(dropna=False).head(15)
            for k, v in vc.items():
                L.append(f"  {str(k)[:60]:<60} {v:>8,}")
            L.append(f"  ... total distintos: {df[c].nunique(dropna=True):,}")
            L.append("")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if not CSV.exists():
        print(f"[ERRO] Não encontrado: {CSV}")
        sys.exit(1)

    print(f"[1/4] Lendo {CSV.name} ...")
    df = carregar_csv(CSV)

    print(f"[2/4] Limpando nomes de coluna ...")
    df = limpar_colunas(df)
    print(f"      Colunas finais: {list(df.columns)}")

    print(f"[3/4] Parseando datas ...")
    df = tratar_datas(df)

    print(f"[4/4] Gerando perfil ...")
    txt = perfil(df)
    SAIDA_PERFIL.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\n[OK] Perfil salvo: {SAIDA_PERFIL}")

    # Salva parquet para análises rápidas
    try:
        df.to_parquet(SAIDA_PARQUET, index=False)
        tam = SAIDA_PARQUET.stat().st_size / (1024 * 1024)
        print(f"[OK] Parquet salvo: {SAIDA_PARQUET} ({tam:.1f} MB)")
    except Exception as e:
        print(f"[AVISO] Não deu para salvar parquet: {e}")
        print("        Instale: pip install pyarrow")


if __name__ == "__main__":
    main()