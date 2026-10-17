import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CARREGAR BASE COMPLETA
# ==========================================
caminho_csv = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados\export\pessoal_correios.csv"

try:
    df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
except:
    df = pd.read_csv(caminho_csv, sep=';', encoding='latin1')

df['ADMISSAO'] = pd.to_datetime(df['ADMISSAO'], dayfirst=True, errors='coerce')
df['DESLIGAMENTO'] = pd.to_datetime(df['DESLIGAMENTO'], dayfirst=True, errors='coerce')

# ==========================================
# 2. FILTRAR APENAS "APOSENTADORIAS" HISTÓRICAS
# ==========================================
# Para ser considerado aposentadoria com alta probabilidade, a pessoa precisa ter 
# pelo menos 25 anos de casa no momento do desligamento.
df_com_desligamento = df.dropna(subset=['DESLIGAMENTO']).copy()

# Calcular tempo de serviço no momento da saída
df_com_desligamento['tempo_na_saida_anos'] = (df_com_desligamento['DESLIGAMENTO'] - df_com_desligamento['ADMISSAO']).dt.days / 365.25

# Filtrar apenas quem saiu com 25 anos ou mais de casa (Proxy robusto de aposentadoria)
df_aposentados_historicos = df_com_desligamento[df_com_desligamento['tempo_na_saida_anos'] >= 25].copy()

print(f"Total de desligamentos na base: {len(df_com_desligamento):,}")
print(f"Desligamentos com 25+ anos de casa (Prováveis Aposentadorias): {len(df_aposentados_historicos):,}")

# ==========================================
# 3. CLASSIFICAR POR ERA LEGAL
# ==========================================
def classificar_era_legal(data_desligamento):
    ano = data_desligamento.year
    if ano <= 1994:
        return 'Era Clássica (Até 1994)'
    elif 1995 <= ano <= 2019:
        return 'Transição Pré-Reforma (1995-2019)'
    else:
        return 'Pós-Reforma da Previdência (2020+)'

df_aposentados_historicos['Era_Legal'] = df_aposentados_historicos['DESLIGAMENTO'].apply(classificar_era_legal)

# Extrair o ano do desligamento para agrupamento
df_aposentados_historicos['Ano_Saida'] = df_aposentados_historicos['DESLIGAMENTO'].dt.year

# Agrupar por Ano e Era Legal
historico_anual = df_aposentados_historicos.groupby(['Ano_Saida', 'Era_Legal']).size().unstack(fill_value=0).reset_index()

# Garantir que todas as colunas de era existam, mesmo que com zero
for era in ['Era Clássica (Até 1994)', 'Transição Pré-Reforma (1995-2019)', 'Pós-Reforma da Previdência (2020+)']:
    if era not in historico_anual.columns:
        historico_anual[era] = 0

# Ordenar por ano
historico_anual = historico_anual.sort_values('Ano_Saida')

# ==========================================
# 4. GRÁFICO DE ÁREA EMPILHADA (STACKED AREA)
# ==========================================
fig = go.Figure()

# Adicionar traços para cada era legal
cores_eras = {
    'Era Clássica (Até 1994)': '#81C784',       # Verde claro
    'Transição Pré-Reforma (1995-2019)': '#FFB74D', # Laranja
    'Pós-Reforma da Previdência (2020+)': '#E57373'   # Vermelho suave
}

for era in ['Era Clássica (Até 1994)', 'Transição Pré-Reforma (1995-2019)', 'Pós-Reforma da Previdência (2020+)']:
    fig.add_trace(go.Scatter(
        x=historico_anual['Ano_Saida'],
        y=historico_anual[era],
        mode='lines',
        stackgroup='one', # Isso cria o efeito de área empilhada
        name=era,
        line=dict(width=0.5, color='white'),
        fillcolor=cores_eras[era],
        hovertemplate='<b>%{fullData.name}</b><br>Ano: %{x}<br>Aposentadorias: %{y:,.0f}<extra></extra>'
    ))

# Adicionar linhas verticais de marco legal
fig.add_vline(x=1994.5, line_dash="dash", line_color="#2E7D32", line_width=2,
              annotation_text=" Lei 9.032/95 ", annotation_position="top right")
fig.add_vline(x=2019.5, line_dash="dash", line_color="#C62828", line_width=2,
              annotation_text=" EC 103/2019 (Reforma) ", annotation_position="top right")

# Layout
fig.update_layout(
    title='<b>Histórico de Aposentadorias nos Correios por Era Legal (1989 - 2026)</b>',
    title_font_size=20,
    title_x=0.5,
    hovermode='x unified',
    template='plotly_white',
    height=600,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    xaxis=dict(title="Ano do Desligamento", dtick=2),
    yaxis=dict(title="Número de Aposentadorias (com 25+ anos de casa)"),
    annotations=[
        dict(x=0.5, y=-0.15, xref="paper", yref="paper",
             text="<i>Metodologia: Consideradas como 'Aposentadorias' apenas as saídas com tempo de serviço igual ou superior a 25 anos. As linhas verticais marcam mudanças legislativas estruturais que impactaram diretamente o fluxo de saídas.</i>",
             showarrow=False, font=dict(size=11, color="#666666"), align="center")
    ]
)

# Salvar e Exibir
caminho_saida = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\scripts\historico_ondas_aposentadoria.html"
fig.write_html(caminho_saida)
print(f"\n✅ Gráfico Histórico de Aposentadorias salvo em: {caminho_saida}")
fig.show(renderer="browser")

# ==========================================
# 5. RESUMO ESTATÍSTICO PARA O RELATÓRIO
# ==========================================
print("\n" + "="*70)
print("📊 RESUMO DAS ONDAS DE APOSENTADORIA (25+ anos de casa)")
print("="*70)
total_geral = historico_anual[['Era Clássica (Até 1994)', 'Transição Pré-Reforma (1995-2019)', 'Pós-Reforma da Previdência (2020+)']].sum().sum()
for era in ['Era Clássica (Até 1994)', 'Transição Pré-Reforma (1995-2019)', 'Pós-Reforma da Previdência (2020+)']:
    total_era = historico_anual[era].sum()
    pct = (total_era / total_geral) * 100 if total_geral > 0 else 0
    print(f"{era:<45}: {int(total_era):>6,}  ({pct:>5.1f}%)")
print(f"{'TOTAL GERAL DE APOSENTADORIAS HISTÓRICAS':<45}: {int(total_geral):>6,}")