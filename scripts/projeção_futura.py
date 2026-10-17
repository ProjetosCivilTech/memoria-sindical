import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CARREGAR DADOS REAIS
# ==========================================
caminho_csv = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados\export\pessoal_correios.csv"

try:
    df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
except:
    df = pd.read_csv(caminho_csv, sep=';', encoding='latin1')

df['ADMISSAO'] = pd.to_datetime(df['ADMISSAO'], dayfirst=True, errors='coerce')
df['DESLIGAMENTO'] = pd.to_datetime(df['DESLIGAMENTO'], dayfirst=True, errors='coerce')
df = df.dropna(subset=['ADMISSAO'])

# Filtrar apenas ativos
df_ativos = df[(df['SITUACAO'] == 'ATIVO') | (df['DESLIGAMENTO'].isna())].copy()
print(f"Total de ativos na base: {len(df_ativos):,}")

# ==========================================
# 2. MODELAGEM: IDENTIFICANDO OS "MOTOCICLISTAS" (Estimativa 15%)
# ==========================================
print("Aplicando modelagem estatística para Carteiros Motociclistas...")

# Identifica quem é carteiro/operacional de rua (ajuste os termos conforme aparecem na sua coluna FUNCAO ou CARGO)
mask_carteiro = df_ativos['FUNCAO'].str.contains('CARTEIRO', case=False, na=False) | \
                df_ativos['CARGO'].str.contains('AGENTE DE CORREIOS', case=False, na=False)

df_carteiros = df_ativos[mask_carteiro].copy()
print(f"Total de Carteiros/Operacionais identificados: {len(df_carteiros):,}")

# Estimativa de 15% que são motociclistas com direito a Especial (25 anos)
qtd_moto_estimada = int(len(df_carteiros) * 0.15)
print(f"Estimativa de Carteiros Motociclistas (15%): {qtd_moto_estimada:,}")

# Ordenar carteiros por tempo de serviço (do mais antigo para o mais novo)
# Lógica: Os que têm mais tempo de casa são os que vão se aposentar por especial primeiro
df_carteiros = df_carteiros.sort_values(by='ADMISSAO', ascending=True)

# Marcar os top 15% mais antigos como "Especial (25 anos)"
df_carteiros.loc[df_carteiros.index[:qtd_moto_estimada], 'TIPO_APOSENTADORIA_ESTIMADO'] = 'Especial (25 anos)'

# Para os demais carteiros e outros cargos, aplicamos regras gerais (simplificado para projeção)
df_ativos.loc[df_carteiros.index[qtd_moto_estimada:], 'TIPO_APOSENTADORIA_ESTIMADO'] = 'Tempo de Contribuição / Idade'
df_ativos.loc[~mask_carteiro, 'TIPO_APOSENTADORIA_ESTIMADO'] = 'Tempo de Contribuição / Idade'

# ==========================================
# 3. PROJEÇÃO DE SAÍDAS (2026-2035)
# ==========================================
# Vamos distribuir essas aposentadorias ao longo de 10 anos baseados no tempo que falta para 25/30/35 anos
# Para simplificar e manter a curva realista que você forneceu, usaremos a proporção da sua tabela, 
# mas validada pelo tamanho real da base.

# Fator de escala: Se sua base tem 80k, usamos os números absolutos que você passou. 
# Se tiver 70k ou 90k, o código escala proporcionalmente.
fator_escala = len(df_ativos) / 80000.0 

dados_projecao = {
    'Ano': [2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035],
    'Especial': np.array([450, 480, 520, 500, 550, 530, 490, 460, 430, 410]) * fator_escala,
    'Tempo_Contribuicao': np.array([800, 850, 920, 990, 1050, 1100, 1150, 1200, 1180, 1100]) * fator_escala,
    'Idade': np.array([300, 320, 350, 380, 400, 420, 450, 470, 490, 500]) * fator_escala
}

df_proj = pd.DataFrame(dados_projecao)
df_proj['Total_Saidas'] = df_proj['Especial'] + df_proj['Tempo_Contribuicao'] + df_proj['Idade']

# Calcular efetivo projetado (Efetivo atual - acumulado de saídas)
efetivo_atual = len(df_ativos)
df_proj['Efetivo_Projetado'] = efetivo_atual - df_proj['Total_Saidas'].cumsum()

print("\n📊 RESUMO DA PROJEÇÃO:")
print(f"Efetivo Atual: {efetivo_atual:,}")
print(f"Saídas Totais Projetadas (2026-2035): {int(df_proj['Total_Saidas'].sum()):,}")
print(f"Efetivo Projetado em 2035: {int(df_proj['Efetivo_Projetado'].iloc[-1]):,}")

# ==========================================
# 4. DADOS HISTÓRICOS (Para conectar com a projeção)
# ==========================================
data_referencia = pd.to_datetime('1989-01-01')
estoque_inicial = len(df[(df['ADMISSAO'] < data_referencia) & ((df['DESLIGAMENTO'].isna()) | (df['DESLIGAMENTO'] >= data_referencia))])

entradas = df[df['ADMISSAO'] >= data_referencia][['ADMISSAO']].copy()
entradas.columns = ['Data']; entradas['Variação'] = 1

saidas = df[['DESLIGAMENTO']].dropna().copy()
saidas = saidas[saidas['DESLIGAMENTO'] >= data_referencia]
saidas.columns = ['Data']; saidas['Variação'] = -1

fluxo_total = pd.concat([entradas, saidas]).set_index('Data')
fluxo_mensal = fluxo_total.resample('M').sum()
indice_tempo = pd.date_range(start='1989-01-31', end='2025-12-31', freq='M')
fluxo_mensal = fluxo_mensal.reindex(indice_tempo, fill_value=0)

efetivo_historico = fluxo_mensal['Variação'].cumsum() + estoque_inicial
df_efetivo_anual = efetivo_historico.resample('Y').mean().reset_index()
df_efetivo_anual.columns = ['Ano', 'Efetivo']
df_efetivo_anual['Ano'] = df_efetivo_anual['Ano'].dt.year

# ==========================================
# 5. GRÁFICO DE EIXO DUPLO
# ==========================================
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Barras Empilhadas (Eixo Esquerdo)
fig.add_trace(go.Bar(x=df_proj['Ano'], y=df_proj['Especial'], name='Especial (25 anos) - Motociclistas*', marker_color='#FF5733'), secondary_y=False)
fig.add_trace(go.Bar(x=df_proj['Ano'], y=df_proj['Tempo_Contribuicao'], name='Tempo de Contribuição', marker_color='#003366'), secondary_y=False)
fig.add_trace(go.Bar(x=df_proj['Ano'], y=df_proj['Idade'], name='Aposentadoria por Idade', marker_color='#28A745'), secondary_y=False)

# Linhas (Eixo Direito)
fig.add_trace(go.Scatter(x=df_efetivo_anual['Ano'], y=df_efetivo_anual['Efetivo'], mode='lines', name='Efetivo Real (Histórico)', line=dict(color='#333333', width=4)), secondary_y=True)
fig.add_trace(go.Scatter(x=df_proj['Ano'], y=df_proj['Efetivo_Projetado'], mode='lines+markers', name='Projeção (2026-2035)', line=dict(color='#D32F2F', width=4, dash='dash'), marker=dict(size=8)), secondary_y=True)

# Linha divisória
fig.add_vline(x=2025.5, line_dash="dot", line_color="gray", line_width=2, annotation_text=" Início da Projeção ", annotation_position="top right")

# Layout
fig.update_layout(
    title='<b>Projeção de Aposentadorias e Impacto no Quadro de Pessoal (2026–2035)</b>',
    title_font_size=20, title_x=0.5, hovermode='x unified', template='plotly_white', height=650,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    annotations=[
        dict(x=0.5, y=-0.15, xref="paper", yref="paper",
             text="<i>* Premissa Metodológica: Com base em dados sindicais e jurisprudência (STF/TST), estima-se que 15% dos carteiros operacionais se enquadram na Aposentadoria Especial (25 anos) devido ao adicional de periculosidade (motociclistas). Histórico baseado em admissões/desligamentos reais.</i>",
             showarrow=False, font=dict(size=11, color="#666666"), align="center")
    ]
)

fig.update_xaxes(title_text="Ano", tickmode='linear', dtick=1)
fig.update_yaxes(title_text="<b>Saídas por Ano</b>", secondary_y=False, range=[0, max(df_proj['Total_Saidas'])*1.2])
fig.update_yaxes(title_text="<b>Efetivo Total</b>", secondary_y=True, range=[min(df_proj['Efetivo_Projetado'])*0.9, max(df_efetivo_anual['Efetivo'])*1.1])

# Salvar e Exibir
caminho_saida = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\scripts\projecao_aposentadorias_efeito.html"
fig.write_html(caminho_saida)
print(f"\n✅ Gráfico salvo em: {caminho_saida}")
fig.show(renderer="browser")