import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

# ==========================================
# 1. DEFINIÇÃO DE CAMINHOS
# ==========================================
# Usando 'r' antes das strings para evitar problemas com as barras do Windows
caminho_csv = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\dados\export\pessoal_correios.csv"
pasta_scripts = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\scripts"
caminho_saida_html = os.path.join(pasta_scripts, "evolucao_efetivo_correios.html")

# ==========================================
# 2. CARREGAMENTO E VALIDAÇÃO DE DADOS
# ==========================================
print("Carregando dados...")

# Tenta carregar com utf-8 (padrão atual), se falhar, tenta latin1 (padrão antigo)
try:
    df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
except UnicodeDecodeError:
    df = pd.read_csv(caminho_csv, sep=';', encoding='latin1')

print(f"Base carregada com sucesso! Shape: {df.shape}")
print("Colunas identificadas:", df.columns.tolist())

# ==========================================
# 3. LIMPEZA E PROCESSAMENTO DE DATAS
# ==========================================
print("Processando datas...")

# Converter datas (formato DD/MM/YYYY)
df['ADMISSAO'] = pd.to_datetime(df['ADMISSAO'], dayfirst=True, errors='coerce')
df['DESLIGAMENTO'] = pd.to_datetime(df['DESLIGAMENTO'], dayfirst=True, errors='coerce')

# Remover linhas onde a admissão é inválida/nula
df = df.dropna(subset=['ADMISSAO'])

# ==========================================
# ==========================================
# 4. CÁLCULO DO ESTOQUE INICIAL (JAN/1989)
# ==========================================
print("Calculando estoque inicial de funcionários em jan/1989...")

data_referencia = pd.to_datetime('1989-01-01')

# Estava ativo em jan/1989 se: admitido antes E (sem desligamento OU desligado depois)
estoque_inicial = df[
    (df['ADMISSAO'] < data_referencia) & 
    ((df['DESLIGAMENTO'].isna()) | (df['DESLIGAMENTO'] >= data_referencia))
]

qtd_estoque_inicial = len(estoque_inicial)
print(f"✅ Funcionários ativos em jan/1989 (estoque inicial): {qtd_estoque_inicial:,}")

# ==========================================
# 5. CÁLCULO DO FLUXO (CORRIGIDO)
# ==========================================
print("Calculando fluxo de admissões e desligamentos...")

# ENTRADAS: apenas admissões a partir de 1989
entradas = df[df['ADMISSAO'] >= data_referencia][['ADMISSAO']].copy()
entradas.columns = ['Data']
entradas['Variação'] = 1

# SAÍDAS: TODOS os desligamentos a partir de 1989 (independente da admissão)
# ⭐ AQUI ESTAVA O BUG - agora pega toda a base
saidas = df[['DESLIGAMENTO']].dropna().copy()
saidas = saidas[saidas['DESLIGAMENTO'] >= data_referencia]  # filtra apenas desligamentos pós-1989
saidas.columns = ['Data']
saidas['Variação'] = -1

# Consolidar e agrupar por mês
fluxo_total = pd.concat([entradas, saidas]).set_index('Data')
fluxo_mensal = fluxo_total.resample('M').sum()

# ==========================================
# 6. SÉRIE TEMPORAL COM ESTOQUE INICIAL
# ==========================================
print("Gerando série temporal...")

data_inicio = pd.to_datetime('1989-01-31')
data_fim = pd.to_datetime('2026-12-31')
indice_tempo = pd.date_range(start=data_inicio, end=data_fim, freq='M')

fluxo_mensal = fluxo_mensal.reindex(indice_tempo, fill_value=0)

# Efetivo = estoque inicial + acumulado de (entradas - saídas)
efetivo_acumulado = fluxo_mensal['Variação'].cumsum() + qtd_estoque_inicial

df_efetivo = efetivo_acumulado.reset_index()
df_efetivo.columns = ['Mês', 'Efetivo']

# ==========================================
# VALIDAÇÃO FINAL
# ==========================================
ativos_hoje_base = len(df[df['SITUACAO'] == 'ATIVO'])
print(f"\n📊 Validação:")
print(f"   Estoque inicial (jan/1989): {qtd_estoque_inicial:,}")
print(f"   Ativos na base hoje (SITUACAO='ATIVO'): {ativos_hoje_base:,}")
print(f"   Efetivo calculado no último mês: {int(df_efetivo['Efetivo'].iloc[-1]):,}")
print(f"   Diferença entre cálculo e base: {int(df_efetivo['Efetivo'].iloc[-1]) - ativos_hoje_base:,}")
# 6. GRÁFICO INTERATIVO (PLOTLY)
# ==========================================
print("Gerando gráfico interativo...")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_efetivo['Mês'], 
    y=df_efetivo['Efetivo'],
    mode='lines',
    name='Efetivo Total',
    line=dict(color='#003366', width=3), # Azul escuro (cor institucional)
    fill='tozeroy',
    fillcolor='rgba(0, 51, 102, 0.1)'
))

# Layout
fig.update_layout(
    title='<b>Evolução do Quadro de Pessoal dos Correios (1989 - 2026)</b>',
    title_font_size=20,
    xaxis_title='Período',
    yaxis_title='Número de Empregados (Efetivo)',
    hovermode='x unified',
    template='plotly_white',
    height=650,
    margin=dict(l=40, r=40, t=60, b=40),
    xaxis=dict(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1 Ano", step="year", stepmode="backward"),
                dict(count=5, label="5 Anos", step="year", stepmode="backward"),
                dict(count=10, label="10 Anos", step="year", stepmode="backward"),
                dict(step="all", label="Tudo")
            ]),
            bgcolor="#E5ECF6",
            activecolor="#003366",
            font=dict(color="white")
        ),
        rangeslider=dict(visible=True),
        type="date"
    )
)

# Linha vertical no dia de hoje
hoje = pd.to_datetime(datetime.now())
fig.add_vline(x=hoje, line_dash="dash", line_color="red", line_width=2,
              annotation_text=" Data Atual ", annotation_position="top right",
              annotation_font_color="red")

# ==========================================
# 7. EXPORTAÇÃO E EXIBIÇÃO
# ==========================================

# Salvar como HTML interativo na pasta de scripts
fig.write_html(caminho_saida_html)
print(f"\n✅ Sucesso! Gráfico interativo salvo em:\n{caminho_saida_html}")

# Exibir no console/navegador do Spyder
# No Spyder, forçar a abertura no navegador padrão é a melhor forma de ver o Plotly
fig.show(renderer="browser") 

print("\n📊 Resumo dos Dados:")
print(f"Total de registros na base: {len(df)}")
print(f"Admissões registradas: {len(entradas)}")
print(f"Desligamentos registrados: {len(saidas)}")
print(f"Efetivo no último mês da base: {df_efetivo['Efetivo'].iloc[-1]}")