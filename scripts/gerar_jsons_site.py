"""
CONVERSOR EXCEL → JSON (v2.1 - Corrigido para Inteiros)
"""
import pandas as pd
import numpy as np
import json
import os
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato"
CAMINHO_XLSX = os.path.join(BASE_DIR, "dados", "pessoal_tratado.xlsx")
PASTA_JSON_SITE = os.path.join(BASE_DIR, "site", "dados")

os.makedirs(PASTA_JSON_SITE, exist_ok=True)

# 1. CARREGAR
df_efetivo = pd.read_excel(CAMINHO_XLSX, sheet_name='Efetivo_Historico')
df_ondas = pd.read_excel(CAMINHO_XLSX, sheet_name='Ondas_Aposentadoria')
df_proj = pd.read_excel(CAMINHO_XLSX, sheet_name='Projecao_2026_2035')
df_raiox = pd.read_excel(CAMINHO_XLSX, sheet_name='RaioX_Aposentados')

# 2. JSON 1: EFETIVO (Forçando inteiros)
anos_totais = list(range(1989, 2036))
hist_dict = dict(zip(df_efetivo['Ano'], df_efetivo['Efetivo']))
proj_dict = dict(zip(df_proj['Ano'], df_proj['Efetivo_Projetado']))
val_2025 = int(hist_dict.get(2025, 90000))

efetivo_real = []
efetivo_projecao = []

for ano in anos_totais:
    # Linha real: inteiro até 2025, depois null
    val_real = hist_dict.get(ano)
    efetivo_real.append(int(val_real) if ano <= 2025 and val_real is not None else None)
    
    # Linha projeção: null até 2024, inteiro em 2025 (overlap), depois inteiro
    if ano < 2025:
        efetivo_projecao.append(None)
    elif ano == 2025:
        efetivo_projecao.append(val_2025)
    else:
        val_proj = proj_dict.get(ano)
        efetivo_projecao.append(int(val_proj) if val_proj is not None else None)

dados_efetivo = {
    "anos": anos_totais,
    "efetivo_real": efetivo_real,
    "efetivo_projecao": efetivo_projecao
}

# 3. JSON 2: PROJEÇÃO (Forçando inteiros)
anos_proj_grafico = [2025] + df_proj['Ano'].astype(int).tolist()
especial = [0] + df_proj['Especial_25_anos'].astype(int).tolist()
tempo_c = [0] + df_proj['Tempo_Contribuicao'].astype(int).tolist()
idade = [0] + df_proj['Aposentadoria_Idade'].astype(int).tolist()
pdv = [0] + df_proj['PDV_Voluntario'].astype(int).tolist()
efetivo_proj_grafico = [val_2025] + df_proj['Efetivo_Projetado'].astype(int).tolist()

dados_projecao = {
    "anos": anos_proj_grafico,
    "especial": especial,
    "tempoContrib": tempo_c,
    "idade": idade,
    "pdv": pdv,
    "efetivo": efetivo_proj_grafico
}

# 4. JSON 3: ONDAS
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

# 5. JSON 4: RAIO-X
labels_limpos = [
    'Já Elegível (35+ anos)', 'Já Elegível (Especial 25+)',
    'Risco Iminente (30-34 anos)', 'Risco Iminente (Cart. 20-24)', 'Longo Prazo (< 20 anos)'
]
dados_raiox = {
    "labels": labels_limpos,
    "geral": df_raiox['Quadro_Geral'].astype(int).tolist(),
    "carteiros": df_raiox['Apenas_Carteiros'].astype(int).tolist()
}

# 6. SALVAR
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
    print(f"✅ {nome_arquivo} (Inteiros corrigidos)")

print("\n🎉 JSONs gerados com sucesso e prontos para o site!")