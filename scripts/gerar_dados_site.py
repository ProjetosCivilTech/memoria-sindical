import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURAÇÃO DE CAMINHOS
# ==========================================
caminho_csv = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados\export\pessoal_correios.csv"
pasta_dados = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados"

# Garantir que a pasta existe
os.makedirs(pasta_dados, exist_ok=True)

print("🔄 Carregando e processando dados...")
try:
    df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
except:
    df = pd.read_csv(caminho_csv, sep=';', encoding='latin1')

df['ADMISSAO'] = pd.to_datetime(df['ADMISSAO'], dayfirst=True, errors='coerce')
df['DESLIGAMENTO'] = pd.to_datetime(df['DESLIGAMENTO'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['ADMISSAO'])

# ==========================================
# 2. DADOS 1: EFETIVO HISTÓRICO (1989-2025)
# ==========================================
data_ref = pd.to_datetime('1989-01-01')
estoque_inicial = len(df[(df['ADMISSAO'] < data_ref) & ((df['DESLIGAMENTO'].isna()) | (df['DESLIGAMENTO'] >= data_ref))])

entradas = df[df['ADMISSAO'] >= data_ref][['ADMISSAO']].copy()
entradas.columns = ['Data']; entradas['Variação'] = 1

saidas = df[['DESLIGAMENTO']].dropna().copy()
saidas = saidas[saidas['DESLIGAMENTO'] >= data_ref]
saidas.columns = ['Data']; saidas['Variação'] = -1

fluxo = pd.concat([entradas, saidas]).set_index('Data').resample('M').sum()
indice = pd.date_range(start='1989-01-31', end='2025-12-31', freq='M')
fluxo = fluxo.reindex(indice, fill_value=0)

efetivo_mensal = fluxo['Variação'].cumsum() + estoque_inicial
efetivo_anual = efetivo_mensal.resample('Y').mean().reset_index()
efetivo_anual.columns = ['Ano', 'Efetivo']
efetivo_anual['Ano'] = efetivo_anual['Ano'].dt.year

# ==========================================
# 3. DADOS 2: PROJEÇÃO (2026-2035)
# ==========================================
df_ativos = df[(df['SITUACAO'] == 'ATIVO') | (df['DESLIGAMENTO'].isna())].copy()
efetivo_2025 = int(efetivo_anual[efetivo_anual['Ano']==2025]['Efetivo'].values[0])
fator_escala = efetivo_2025 / 80000.0

anos_proj = [2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035]
especial = (np.array([450, 480, 520, 500, 550, 530, 490, 460, 430, 410]) * fator_escala).astype(int).tolist()
tempo_c = (np.array([800, 850, 920, 990, 1050, 1100, 1150, 1200, 1180, 1100]) * fator_escala).astype(int).tolist()
idade = (np.array([300, 320, 350, 380, 400, 420, 450, 470, 490, 500]) * fator_escala).astype(int).tolist()

saidas_totais = np.array(especial) + np.array(tempo_c) + np.array(idade)
efetivo_proj = (efetivo_2025 - np.cumsum(saidas_totais)).astype(int).tolist()

# Unir histórico e projeção para o gráfico 1
anos_totais = efetivo_anual['Ano'].tolist() + anos_proj
efetivo_totais = efetivo_anual['Efetivo'].astype(int).tolist() + efetivo_proj
is_projecao = [False]*len(efetivo_anual) + [True]*len(anos_proj)

dados_efetivo = {
    "anos": anos_totais,
    "efetivo": efetivo_totais,
    "isProjecao": is_projecao
}

dados_projecao = {
    "anos": [2025] + anos_proj,
    "especial": [0] + especial,
    "tempoContrib": [0] + tempo_c,
    "idade": [0] + idade,
    "efetivo": [efetivo_2025] + efetivo_proj
}

# ==========================================
# 4. DADOS 3: ONDAS DE APOSENTADORIA (1989-2026)
# ==========================================
df_deslig = df.dropna(subset=['DESLIGAMENTO']).copy()
df_deslig['tempo_saida'] = (df_deslig['DESLIGAMENTO'] - df_deslig['ADMISSAO']).dt.days / 365.25
df_apos = df_deslig[df_deslig['tempo_saida'] >= 25].copy()

def era_legal(ano):
    if ano <= 1994: return 'classica'
    if ano <= 2019: return 'transicao'
    return 'posReforma'

df_apos['Era'] = df_apos['DESLIGAMENTO'].dt.year.apply(era_legal)
df_apos['Ano'] = df_apos['DESLIGAMENTO'].dt.year

ondas = df_apos.groupby(['Ano', 'Era']).size().unstack(fill_value=0).reset_index()
for col in ['classica', 'transicao', 'posReforma']:
    if col not in ondas.columns: ondas[col] = 0

# Preencher anos faltantes (1989-2026)
todos_anos = pd.DataFrame({'Ano': range(1989, 2027)})
ondas = todos_anos.merge(ondas, on='Ano', how='left').fillna(0)

dados_ondas = {
    "anos": ondas['Ano'].astype(int).tolist(),
    "classica": ondas['classica'].astype(int).tolist(),
    "transicao": ondas['transicao'].astype(int).tolist(),
    "posReforma": ondas['posReforma'].astype(int).tolist()
}

# ==========================================
# 5. DADOS 4: RAIO-X ATUAL (ESTÁTICO)
# ==========================================
hoje = pd.Timestamp('today')
df_ativos['tempo_anos'] = (hoje - df_ativos['ADMISSAO']).dt.days / 365.25
mask_carteiro = df_ativos['FUNCAO'].str.contains('CARTEIRO', case=False, na=False) | \
                df_ativos['CARGO'].str.contains('AGENTE DE CORREIOS', case=False, na=False)

def classificar(tempo, is_carteiro):
    if tempo >= 35: return 'Já Elegível (35+ anos)'
    if is_carteiro and tempo >= 25: return 'Já Elegível (Especial 25+)'
    if tempo >= 30: return 'Risco Iminente (30-34 anos)'
    if is_carteiro and tempo >= 20: return 'Risco Iminente (Cart. 20-24)'
    return 'Longo Prazo (< 20 anos)'

df_ativos['Status'] = df_ativos.apply(lambda r: classificar(r['tempo_anos'], mask_carteiro.loc[r.name]), axis=1)

ordem = ['Já Elegível (35+ anos)', 'Já Elegível (Especial 25+)', 'Risco Iminente (30-34 anos)', 'Risco Iminente (Cart. 20-24)', 'Longo Prazo (< 20 anos)']

contagem_geral = df_ativos['Status'].value_counts().reindex(ordem, fill_value=0).astype(int).tolist()

df_cart = df_ativos[mask_carteiro]
contagem_cart = df_cart['Status'].value_counts().reindex(ordem, fill_value=0).astype(int).tolist()

dados_raiox = {
    "labels": ordem,
    "geral": contagem_geral,
    "carteiros": contagem_cart
}

# ==========================================
# 6. EXPORTAR JSONs
# ==========================================
arquivos = {
    "efetivo_historico_projecao.json": dados_efetivo,
    "projecao_2026_2035.json": dados_projecao,
    "ondas_aposentadoria.json": dados_ondas,
    "raiox_aposentados.json": dados_raiox
}

for nome, dados in arquivos.items():
    caminho_saida = os.path.join(pasta_dados, nome)
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"✅ Salvo: {nome}")

print("\n🎉 Dados prontos para o site! Agora atualize o index.html para buscar esses JSONs.")