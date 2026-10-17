"""
================================================================
PROCESSADOR DE DADOS DE PESSOAL - CORREIOS (v2.0 com PDV Real)
================================================================
Incorpora dados reais de PDV (Plano de Demissão Voluntária)
na projeção 2026-2035, criando um cenário híbrido e realista.

Dados de PDV incorporados:
- PDV 2026 (1º semestre): 3.100 adesões (30% da meta de 10k)
- PDV-E 2026 (Ago/Set): 7.000 adesões esperadas
- PDV contínuo 2027-2035: ~3.000/ano (ritmo realista)

Requisitos: pip install pandas openpyxl
================================================================
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. CONFIGURAÇÃO DE CAMINHOS
# ============================================================
BASE_DIR = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato"
CAMINHO_CSV = os.path.join(BASE_DIR, "dados", "export", "pessoal_correios.csv")
CAMINHO_SAIDA = os.path.join(BASE_DIR, "dados", "pessoal_tratado.xlsx")

print("=" * 70)
print("🔄 PROCESSAMENTO DE DADOS DE PESSOAL (v2.0 com PDV Real)")
print("=" * 70)

# ============================================================
# 2. CARREGAR BASE BRUTA
# ============================================================
print("\n Carregando base bruta...")
try:
    df = pd.read_csv(CAMINHO_CSV, sep=';', encoding='utf-8')
except UnicodeDecodeError:
    df = pd.read_csv(CAMINHO_CSV, sep=';', encoding='latin1')

df['ADMISSAO'] = pd.to_datetime(df['ADMISSAO'], dayfirst=True, errors='coerce')
df['DESLIGAMENTO'] = pd.to_datetime(df['DESLIGAMENTO'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['ADMISSAO'])
print(f"✅ Base carregada: {len(df):,} registros")

# ============================================================
# 3. ABA 1: EFETIVO HISTÓRICO (1989-2025)
# ============================================================
print("\n📊 Processando ABA 1: Efetivo Histórico...")
data_ref = pd.to_datetime('1989-01-01')

estoque_inicial = len(df[
    (df['ADMISSAO'] < data_ref) & 
    ((df['DESLIGAMENTO'].isna()) | (df['DESLIGAMENTO'] >= data_ref))
])

entradas = df[df['ADMISSAO'] >= data_ref][['ADMISSAO']].copy()
entradas.columns = ['Data']
entradas['Variacao'] = 1

saidas = df[['DESLIGAMENTO']].dropna().copy()
saidas = saidas[saidas['DESLIGAMENTO'] >= data_ref]
saidas.columns = ['Data']
saidas['Variacao'] = -1

fluxo = pd.concat([entradas, saidas]).set_index('Data').resample('M').sum()
indice = pd.date_range(start='1989-01-31', end='2025-12-31', freq='M')
fluxo = fluxo.reindex(indice, fill_value=0)

efetivo_mensal = fluxo['Variacao'].cumsum() + estoque_inicial
df_efetivo_anual = efetivo_mensal.resample('Y').mean().reset_index()
df_efetivo_anual.columns = ['Ano', 'Efetivo']
df_efetivo_anual['Ano'] = df_efetivo_anual['Ano'].dt.year

val_2025 = int(df_efetivo_anual[df_efetivo_anual['Ano']==2025]['Efetivo'].values[0])
print(f"✅ Efetivo em 2025: {val_2025:,}")

# ============================================================
# 4. ABA 2: ONDAS DE APOSENTADORIA POR ERA LEGAL (1989-2026)
# ============================================================
print("\n📊 Processando ABA 2: Ondas de Aposentadoria...")
df_deslig = df.dropna(subset=['DESLIGAMENTO']).copy()
df_deslig['tempo_saida'] = (df_deslig['DESLIGAMENTO'] - df_deslig['ADMISSAO']).dt.days / 365.25
df_apos = df_deslig[df_deslig['tempo_saida'] >= 25].copy()

def era_legal(ano):
    if ano <= 1994: return 'Era Classica (ate 1994)'
    if ano <= 2019: return 'Transicao Pre-Reforma (1995-2019)'
    return 'Pos-Reforma (2020+)'

df_apos['Era'] = df_apos['DESLIGAMENTO'].dt.year.apply(era_legal)
df_apos['Ano'] = df_apos['DESLIGAMENTO'].dt.year

ondas = df_apos.groupby(['Ano', 'Era']).size().unstack(fill_value=0).reset_index()
for col in ['Era Classica (ate 1994)', 'Transicao Pre-Reforma (1995-2019)', 'Pos-Reforma (2020+)']:
    if col not in ondas.columns: ondas[col] = 0

todos_anos = pd.DataFrame({'Ano': range(1989, 2027)})
df_ondas = todos_anos.merge(ondas, on='Ano', how='left').fillna(0)
df_ondas['Ano'] = df_ondas['Ano'].astype(int)
print(f"✅ Total de aposentadorias históricas (25+ anos): {int(df_ondas.iloc[:, 1:].sum().sum()):,}")

# ============================================================
# 5. ABA 3: PROJEÇÃO 2026-2035 COM PDV REAL
# ============================================================
print("\n Processando ABA 3: Projeção 2026-2035 (com PDV Real)...")

fator_escala = val_2025 / 80000.0

# Dados base de aposentadorias naturais (escalados)
anos_proj = list(range(2026, 2036))
especial = [int(x * fator_escala) for x in [450, 480, 520, 500, 550, 530, 490, 460, 430, 410]]
tempo_c = [int(x * fator_escala) for x in [800, 850, 920, 990, 1050, 1100, 1150, 1200, 1180, 1100]]
idade = [int(x * fator_escala) for x in [300, 320, 350, 380, 400, 420, 450, 470, 490, 500]]

# 🎯 DADOS REAIS DE PDV (incorporados na projeção)
# Fonte: Desempenho Real das Adesões e Ajustes de Rota
pdv_2026 = 10100  # 3.100 (PDV1) + 7.000 (PDV-E)
pdv_anual_2027_2035 = 3000  # Ritmo realista contínuo

# Distribuir PDV ao longo dos anos (cenário realista)
pdv_por_ano = [
    pdv_2026,           # 2026: pico de adesões
    pdv_anual_2027_2035,  # 2027
    pdv_anual_2027_2035,  # 2028
    pdv_anual_2027_2035,  # 2029
    pdv_anual_2027_2035,  # 2030
    pdv_anual_2027_2035,  # 2031
    pdv_anual_2027_2035,  # 2032
    pdv_anual_2027_2035,  # 2033
    pdv_anual_2027_2035,  # 2034
    pdv_anual_2027_2035   # 2035
]

# Calcular efetivo projetado ano a ano
saidas_totais = []
efetivo_proj = []
efetivo_atual = val_2025

for i in range(len(anos_proj)):
    saidas_ano = especial[i] + tempo_c[i] + idade[i] + pdv_por_ano[i]
    saidas_totais.append(saidas_ano)
    efetivo_atual -= saidas_ano
    efetivo_proj.append(efetivo_atual)

df_proj = pd.DataFrame({
    'Ano': anos_proj,
    'Especial_25_anos': especial,
    'Tempo_Contribuicao': tempo_c,
    'Aposentadoria_Idade': idade,
    'PDV_Voluntario': pdv_por_ano,
    'Total_Saidas': saidas_totais,
    'Efetivo_Projetado': efetivo_proj
})

print(f"✅ Projeção com PDV:")
print(f"   Efetivo 2025: {val_2025:,}")
print(f"   PDV 2026: {pdv_2026:,} (3.100 + 7.000)")
print(f"   PDV anual 2027-2035: {pdv_anual_2027_2035:,}/ano")
print(f"   Efetivo projetado 2035: {efetivo_proj[-1]:,}")
print(f"   Queda total: {val_2025 - efetivo_proj[-1]:,} ({((val_2025 - efetivo_proj[-1])/val_2025*100):.1f}%)")

# ============================================================
# 6. ABA 4: RAIO-X DE APOSENTADOS ATIVOS
# ============================================================
print("\n Processando ABA 4: Raio-X de Aposentados Ativos...")
hoje = pd.Timestamp('today')
df_ativos = df[(df['SITUACAO'] == 'ATIVO') | (df['DESLIGAMENTO'].isna())].copy()
df_ativos['tempo_anos'] = (hoje - df_ativos['ADMISSAO']).dt.days / 365.25

mask_carteiro = df_ativos['FUNCAO'].str.contains('CARTEIRO', case=False, na=False) | \
                df_ativos['CARGO'].str.contains('AGENTE DE CORREIOS', case=False, na=False)

def classificar(row):
    tempo = row['tempo_anos']
    is_carteiro = row['is_carteiro']
    if tempo >= 35: return 'Ja Elegivel (35+ anos)'
    if is_carteiro and tempo >= 25: return 'Ja Elegivel (Especial 25+)'
    if tempo >= 30: return 'Risco Iminente (30-34 anos)'
    if is_carteiro and tempo >= 20: return 'Risco Iminente (Cart. 20-24)'
    return 'Longo Prazo (< 20 anos)'

df_ativos['is_carteiro'] = mask_carteiro
df_ativos['Status'] = df_ativos.apply(classificar, axis=1)

ordem = [
    'Ja Elegivel (35+ anos)',
    'Ja Elegivel (Especial 25+)',
    'Risco Iminente (30-34 anos)',
    'Risco Iminente (Cart. 20-24)',
    'Longo Prazo (< 20 anos)'
]

contagem_geral = df_ativos['Status'].value_counts().reindex(ordem, fill_value=0).astype(int)
df_cart = df_ativos[mask_carteiro]
contagem_cart = df_cart['Status'].value_counts().reindex(ordem, fill_value=0).astype(int)

df_raiox = pd.DataFrame({
    'Categoria': ordem,
    'Quadro_Geral': contagem_geral.values,
    'Apenas_Carteiros': contagem_cart.values
})
print(f"✅ Total de ativos analisados: {len(df_ativos):,}")

# ============================================================
# 7. EXPORTAR PARA EXCEL CONSOLIDADO
# ============================================================
print("\n💾 Exportando para Excel...")
os.makedirs(os.path.dirname(CAMINHO_SAIDA), exist_ok=True)

with pd.ExcelWriter(CAMINHO_SAIDA, engine='openpyxl') as writer:
    df_efetivo_anual.to_excel(writer, sheet_name='Efetivo_Historico', index=False)
    df_ondas.to_excel(writer, sheet_name='Ondas_Aposentadoria', index=False)
    df_proj.to_excel(writer, sheet_name='Projecao_2026_2035', index=False)
    df_raiox.to_excel(writer, sheet_name='RaioX_Aposentados', index=False)

print("\n" + "=" * 70)
print("✅ SUCESSO! Arquivo salvo em:")
print(f"   {CAMINHO_SAIDA}")
print("=" * 70)
print("\n📑 Abas geradas:")
print("   1. Efetivo_Historico (1989-2025)")
print("   2. Ondas_Aposentadoria (1989-2026)")
print("   3. Projecao_2026_2035 (com PDV Real)")
print("   4. RaioX_Aposentados")
print("\n🎉 Processamento concluído!")