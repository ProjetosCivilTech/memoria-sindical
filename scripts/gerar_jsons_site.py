"""
================================================================
CONVERSOR EXCEL → JSON (Memória Sindical v2.0)
================================================================
Lê o arquivo 'pessoal_tratado.xlsx' e gera os 4 arquivos JSON 
otimizados para o frontend, incluindo dados de PDV voluntário.
================================================================
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. CONFIGURAÇÃO DE CAMINHOS
# ============================================================
BASE_DIR = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato"
CAMINHO_XLSX = os.path.join(BASE_DIR, "dados", "pessoal_tratado.xlsx")
PASTA_JSON_SITE = os.path.join(BASE_DIR, "site", "dados")

print("=" * 70)
print("🔄 CONVERTENDO EXCEL → JSON (v2.0 com PDV)")
print("=" * 70)

os.makedirs(PASTA_JSON_SITE, exist_ok=True)

# ============================================================
# 2. CARREGAR ABAS DO EXCEL
# ============================================================
print("\n📥 Lendo arquivo Excel...")
df_efetivo = pd.read_excel(CAMINHO_XLSX, sheet_name='Efetivo_Historico')
df_ondas = pd.read_excel(CAMINHO_XLSX, sheet_name='Ondas_Aposentadoria')
df_proj = pd.read_excel(CAMINHO_XLSX, sheet_name='Projecao_2026_2035')
df_raiox = pd.read_excel(CAMINHO_XLSX, sheet_name='RaioX_Aposentados')

# ============================================================
# 3. JSON 1: EFETIVO HISTÓRICO + PROJEÇÃO (COM OVERLAP 2025)
# ============================================================
print("\n📊 Processando: efetivo_historico_projecao.json")

anos_totais = list(range(1989, 2036))
hist_dict = dict(zip(df_efetivo['Ano'], df_efetivo['Efetivo']))
proj_dict = dict(zip(df_proj['Ano'], df_proj['Efetivo_Projetado']))
val_2025 = hist_dict.get(2025, 90000)

efetivo_real = []
efetivo_projecao = []

for ano in anos_totais:
    if ano <= 2025:
        efetivo_real.append(hist_dict.get(ano, None))
    else:
        efetivo_real.append(None)
    
    if ano < 2025:
        efetivo_projecao.append(None)
    elif ano == 2025:
        efetivo_projecao.append(val_2025)
    else:
        efetivo_projecao.append(proj_dict.get(ano, None))

dados_efetivo = {
    "anos": anos_totais,
    "efetivo_real": efetivo_real,
    "efetivo_projecao": efetivo_projecao
}

# ============================================================
# 4. JSON 2: PROJEÇÃO DETALHADA (2025-2035) COM PDV
# ============================================================
print("📊 Processando: projecao_2026_2035.json")

anos_proj_grafico = [2025] + df_proj['Ano'].tolist()
especial = [0] + df_proj['Especial_25_anos'].tolist()
tempo_c = [0] + df_proj['Tempo_Contribuicao'].tolist()
idade = [0] + df_proj['Aposentadoria_Idade'].tolist()
pdv = [0] + df_proj['PDV_Voluntario'].tolist()
efetivo_proj_grafico = [val_2025] + df_proj['Efetivo_Projetado'].tolist()

dados_projecao = {
    "anos": anos_proj_grafico,
    "especial": especial,
    "tempoContrib": tempo_c,
    "idade": idade,
    "pdv": pdv,
    "efetivo": efetivo_proj_grafico
}

# ============================================================
# 5. JSON 3: ONDAS DE APOSENTADORIA
# ============================================================
print(" Processando: ondas_aposentadoria.json")

df_ondas_renamed = df_ondas.rename(columns={
    'Era Classica (ate 1994)': 'classica',
    'Transicao Pre-Reforma (1995-2019)': 'transicao',
    'Pos-Reforma (2020+)': 'posReforma'
})

dados_ondas = {
    "anos": df_ondas_renamed['Ano'].astype(int).tolist(),
    "classica": df_ondas_renamed['classica'].astype(int).tolist(),
    "transicao": df_ondas_renamed['transicao'].astype(int).tolist(),
    "posReforma": df_ondas_renamed['posReforma'].astype(int).tolist()
}

# ============================================================
# 6. JSON 4: RAIO-X DE APOSENTADOS
# ============================================================
print("📊 Processando: raiox_aposentados.json")

labels_limpos = [
    'Já Elegível (35+ anos)',
    'Já Elegível (Especial 25+)',
    'Risco Iminente (30-34 anos)',
    'Risco Iminente (Cart. 20-24)',
    'Longo Prazo (< 20 anos)'
]

dados_raiox = {
    "labels": labels_limpos,
    "geral": df_raiox['Quadro_Geral'].astype(int).tolist(),
    "carteiros": df_raiox['Apenas_Carteiros'].astype(int).tolist()
}

# ============================================================
# 7. EXPORTAR JSONs
# ============================================================
print("\n💾 Salvando arquivos JSON...")

arquivos = {
    "efetivo_historico_projecao.json": dados_efetivo,
    "projecao_2026_2035.json": dados_projecao,
    "ondas_aposentadoria.json": dados_ondas,
    "raiox_aposentados.json": dados_raiox
}

for nome_arquivo, dados in arquivos.items():
    caminho_saida = os.path.join(PASTA_JSON_SITE, nome_arquivo)
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {nome_arquivo}")

print("\n" + "=" * 70)
print("🎉 SUCESSO! JSONs gerados com dados de PDV incorporados.")
print("=" * 70)