/* ============================================================
   Batalha pelo Salário — Gráficos Dinâmicos
   Memória Sindical | Raio-X da Luta
   Versão: eixo duplo + contexto macro + paleta Viridis
   ============================================================ */

'use strict';

/* ------------------------------------------------------------
   PALETA VIRIDIS
   Perceptualmente uniforme, amigável para daltônicos.
   Fonte: matplotlib (Nathaniel Smith & Stéfan van der Walt, 2015)
   ------------------------------------------------------------ */

const VIRIDIS = [
  '#440154', // 0.0  roxo escuro  (menor)
  '#482878', // 0.11
  '#3E4989', // 0.22
  '#31688E', // 0.33
  '#26828E', // 0.44
  '#1F9E89', // 0.55  teal
  '#35B779', // 0.66  verde
  '#6DCD59', // 0.77
  '#B4DE2C', // 0.88  verde-amarelo
  '#FDE725', // 1.0  amarelo    (maior)
];

function interpolarCor(c1, c2, t) {
  const r1 = parseInt(c1.slice(1, 3), 16);
  const g1 = parseInt(c1.slice(3, 5), 16);
  const b1 = parseInt(c1.slice(5, 7), 16);
  const r2 = parseInt(c2.slice(1, 3), 16);
  const g2 = parseInt(c2.slice(3, 5), 16);
  const b2 = parseInt(c2.slice(5, 7), 16);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

/** t ∈ [0,1] → cor Viridis */
function viridis(t) {
  t = Math.max(0, Math.min(1, t));
  const idx = t * (VIRIDIS.length - 1);
  const i = Math.floor(idx);
  const j = Math.min(i + 1, VIRIDIS.length - 1);
  return interpolarCor(VIRIDIS[i], VIRIDIS[j], idx - i);
}

/** Escala aplicada a um array de valores (min → roxo, max → amarelo) */
function viridisEscala(valores) {
  const validos = valores.filter(v => typeof v === 'number' && !isNaN(v));
  if (!validos.length) return valores.map(() => VIRIDIS[5]);
  const min = Math.min(...validos);
  const max = Math.max(...validos);
  const range = max - min || 1;
  return valores.map(v => viridis((v - min) / range));
}

/** Escala divergente: centro = tom neutro, extremos = roxo/amarelo */
function viridisDivergente(valores, centro = 0) {
  const maxAbs = Math.max(...valores.map(v => Math.abs(v - centro))) || 1;
  return valores.map(v => viridis(((v - centro) / maxAbs + 1) / 2));
}

/* Cores fixas da paleta para uso direto */
const V = {
  roxo:       VIRIDIS[0],   // #440154
  azul:       VIRIDIS[3],   // #31688E
  teal:       VIRIDIS[5],   // #1F9E89
  verde:      VIRIDIS[6],   // #35B779
  verdeAm:    VIRIDIS[8],   // #B4DE2C
  amarelo:    VIRIDIS[9],   // #FDE725
};

/* ------------------------------------------------------------
   CORES E FONTES (compatibilidade)
   ------------------------------------------------------------ */

const CORES = {
  vermelho:      V.azul,          // reaproveitado como cor de destaque principal
  vermelhoEsc:   V.roxo,
  vermelhoClaro: 'rgba(49, 104, 142, 0.12)',
  vermelhoArea:  'rgba(49, 104, 142, 0.20)',
  cinza:         '#888888',
  cinzaClaro:    'rgba(136, 136, 136, 0.10)',
  ganho:         V.verde,         // verde Viridis
  perda:         V.roxo,          // roxo Viridis
  conquista:     V.amarelo,       // amarelo Viridis (conquista)
  preto:         '#1A1A1A',
  branco:        '#FFFFFF',
};

const CORES_GOVERNO = {
  progressista: V.verde,
  conservador:  V.azul,
  centro:       '#888888',
  '—':          '#CCCCCC',
};

const FONTE_TITULO = "'Montserrat', sans-serif";
const FONTE_TEXTO  = "'Inter', sans-serif";

const TOOLTIP_PADRAO = {
  backgroundColor: CORES.preto,
  titleFont: { family: FONTE_TITULO, size: 13, weight: '700' },
  bodyFont:  { family: FONTE_TEXTO,  size: 12 },
  padding: 12,
  cornerRadius: 6,
  displayColors: false,
};

/* ------------------------------------------------------------
   MARCOS HISTÓRICOS DE CONQUISTA
   ------------------------------------------------------------ */

const EVENTOS_CONQUISTA = {
  1993: {
    titulo: 'AADC 30% + Adicional Noturno',
    descricao: 'Adicional de Atividade de Distribuição e Coleta (30%) e adicional noturno de 60%.',
    impacto: '+30% AADC | +60% noturno',
  },
  1997: {
    titulo: 'Quebra de Caixa',
    descricao: 'Criação da Gratificação de Quebra de Caixa para atendentes comerciais.',
    impacto: 'Novo benefício',
  },
  1999: {
    titulo: 'Criação do Vale Cesta',
    descricao: 'Instituído no ACT 1999/2000, substituindo a cesta básica em alimentos.',
    impacto: 'R$ 40/mês',
  },
  2008: {
    titulo: 'AADC Consolidado em 30%',
    descricao: 'Consolidação do AADC após 3 greves sucessivas. Benefício separado do salário-base.',
    impacto: '+30% AADC',
  },
  2014: {
    titulo: 'Periculosidade Motociclistas',
    descricao: 'Adicional de periculosidade de 30% + acumulação com o AADC.',
    impacto: '+30% acumulável',
  },
  2024: {
    titulo: 'Reconquista de Direitos',
    descricao: 'Reajuste acima da inflação e recomposição de cláusulas retiradas.',
    impacto: 'Recomposição',
  },
};

const ANOS_CHAVE = [1993, 1995, 1997, 1999, 2002, 2008, 2013, 2014, 2020, 2022, 2024];
const MARGEM_GANHO = 0.1;

/* ------------------------------------------------------------
   VARIÁVEIS GLOBAIS
   ------------------------------------------------------------ */

let chartSalarioReal = null;
let chartReajustesGoverno = null;
let dadosGlobais = null;
let dadosMacroGlobal = null;

function prefereMenosMovimento() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/* ------------------------------------------------------------
   PLUGIN: TROFÉUS DE CONQUISTA
   ------------------------------------------------------------ */

const conquistasPlugin = {
  id: 'conquistasPlugin',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea, scales: { x } } = chart;
    if (!x || !chartArea) return;

    const anosVisiveis = chart.data.labels || [];

    ctx.save();
    ctx.textAlign = 'center';

    anosVisiveis.forEach((ano, idx) => {
      if (!EVENTOS_CONQUISTA[ano]) return;

      const xPos = x.getPixelForValue(idx);
      if (xPos < chartArea.left || xPos > chartArea.right) return;

      const yTrophy = chartArea.bottom - 32;

      ctx.beginPath();
      ctx.arc(xPos, yTrophy, 11, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(253, 231, 37, 0.30)';
      ctx.fill();
      ctx.strokeStyle = V.amarelo;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.font = '12px sans-serif';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = CORES.preto;
      ctx.fillText('🏆', xPos, yTrophy);

      ctx.font = `bold 10px ${FONTE_TEXTO}`;
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#8B6B00';   // amarelo escurecido p/ contraste
      ctx.fillText(String(ano), xPos, chartArea.bottom - 16);
    });

    ctx.restore();
  },
};

Chart.register(conquistasPlugin);

/* ------------------------------------------------------------
   UTILITÁRIOS
   ------------------------------------------------------------ */

async function carregarDados(caminho) {
  const resp = await fetch(caminho);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ao carregar ${caminho}`);
  return resp.json();
}

function mostrarErro(msg) {
  document.body.insertAdjacentHTML('afterbegin', `
    <div style="background:${V.azul};color:#fff;padding:1rem;
                text-align:center;font-family:${FONTE_TEXTO};">
      <strong>Erro:</strong> ${msg}
      <br><small>Abra o console (F12) para mais detalhes.</small>
    </div>
  `);
}

function formatarInflacao(valor) {
  if (valor >= 1e12) return '×' + (valor / 1e12).toFixed(1) + ' tri';
  if (valor >= 1e9)  return '×' + (valor / 1e9).toFixed(1) + ' bi';
  if (valor >= 1e6)  return '×' + (valor / 1e6).toFixed(1) + ' mi';
  if (valor >= 1e3)  return '×' + (valor / 1e3).toFixed(1) + ' mil';
  return '×' + Math.round(valor).toLocaleString('pt-BR');
}

function formatarRS(valor) {
  return 'R$ ' + valor.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/* ------------------------------------------------------------
   LÓGICA DE CORES E TAMANHOS
   ------------------------------------------------------------ */

function corDoPonto(s) {
  if (EVENTOS_CONQUISTA[s.ano]) return V.amarelo;
  if (typeof s.reajuste_pct === 'number' &&
      typeof s.ipca_ano === 'number' &&
      s.reajuste_pct > s.ipca_ano + MARGEM_GANHO) {
    return V.verde;
  }
  return V.azul;
}

function raioDoPonto(s) {
  if (EVENTOS_CONQUISTA[s.ano]) return 8;
  if (ANOS_CHAVE.includes(s.ano)) return 6;
  return 3;
}

/* ------------------------------------------------------------
   PAUSA FORA DA VIEWPORT
   ------------------------------------------------------------ */

const graficosPausados = new WeakSet();

function pausarForaDaViewport(canvas, chart) {
  if (!canvas || !chart || graficosPausados.has(canvas)) return;
  graficosPausados.add(canvas);

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting && chart) {
        chart.options.animation = false;
      }
    });
  }, { threshold: 0.05 });

  observer.observe(canvas);
}

/* ------------------------------------------------------------
   KPIs
   ------------------------------------------------------------ */

function renderKPIs(dados) {
  const serie = dados.serie_temporal || [];
  if (!serie.length) return;

  const ultimo = serie[serie.length - 1];
  const primeiro = serie[0];
  const anoBase = dados.metadados?.ano_base || primeiro.ano;

  const poder = ultimo.salario_real || 100;
  const variacao = poder - 100;

  document.getElementById('kpi-salario-real').textContent = poder.toFixed(0);

  const elSal = document.getElementById('kpi-salario-var');
  elSal.textContent = (variacao >= 0 ? '+' : '') +
                      variacao.toFixed(0) + '% desde ' + anoBase;
  elSal.className = 'variacao ' + (variacao >= 0 ? 'positiva' : 'negativa');

  const inflacaoX = ultimo.inflacao_acumulada / primeiro.inflacao_acumulada;
  document.getElementById('kpi-inflacao').textContent = formatarInflacao(inflacaoX);

  const totalGreves = dados.metadados?.total_greves_historicas || 0;
  document.getElementById('kpi-greves').textContent = totalGreves;

  let maior = { ano: null, pct: 0 };
  for (const s of serie) {
    if (typeof s.reajuste_pct === 'number' && s.reajuste_pct > maior.pct) {
      maior = { ano: s.ano, pct: s.reajuste_pct };
    }
  }
  document.getElementById('kpi-maior-ganho').textContent =
    maior.ano ? '+' + maior.pct + '%' : '—';
  document.getElementById('kpi-maior-ganho-ano').textContent =
    maior.ano ? 'em ' + maior.ano : '';
}

/* ------------------------------------------------------------
   PAINEL DE DETALHES
   ------------------------------------------------------------ */

function mostrarPainelDetalhe(s) {
  const el = document.getElementById('painel-detalhe');
  if (!el || !s) return;

  const vaVc = s.va_vc_total ? `
    <div class="painel-linha">
      <span class="painel-rotulo">Vale Refeição/Alimentação + Cesta</span>
      <span class="painel-valor">${formatarRS(s.va_vc_total)}/mês</span>
    </div>` : '';

  const reaj = s.reajuste_pct !== null && s.reajuste_pct !== undefined ? `
    <div class="painel-linha">
      <span class="painel-rotulo">Reajuste</span>
      <span class="painel-valor">${s.reajuste_pct > 0 ? '+' : ''}${s.reajuste_pct}%</span>
    </div>` : '';

  const inflacao = s.ipca_ano ? `
    <div class="painel-linha">
      <span class="painel-rotulo">IPCA do ano</span>
      <span class="painel-valor">${s.ipca_ano}%</span>
    </div>` : '';

  el.innerHTML = `
    <div class="painel-titulo">${s.ano} — ${s.governo || '—'}</div>
    <div class="painel-linha">
      <span class="painel-rotulo">Poder de compra</span>
      <span class="painel-valor">${(s.salario_real || 100).toFixed(1)}</span>
    </div>
    ${reaj}
    ${inflacao}
    ${vaVc}
    ${s.observacao ? `<div class="painel-obs">${s.observacao}</div>` : ''}
  `;
  el.classList.add('ativo');
}

/* ------------------------------------------------------------
   GRÁFICO 0 — REAJUSTES POR GOVERNO
   ------------------------------------------------------------ */

function renderizarReajustesGoverno(dados) {
  dadosGlobais = dados;

  const serie = (dados.serie_temporal || [])
    .filter(s => typeof s.reajuste_pct === 'number')
    .map(s => ({ ...s, ano: parseInt(s.ano, 10) }))
    .sort((a, b) => a.ano - b.ano);

  if (!serie.length) return;

  const canvas = document.getElementById('grafico-reajustes-governo');
  if (!canvas) return;

  if (chartReajustesGoverno) {
    chartReajustesGoverno.destroy();
    chartReajustesGoverno = null;
  }

  const isMobile = window.innerWidth < 768;
  const semAnimacao = prefereMenosMovimento();
  const ctx = canvas.getContext('2d');

  // Cor de cada ponto: escala Viridis pelo valor do reajuste
  const coresPontos = viridisEscala(serie.map(s => s.reajuste_pct));

  chartReajustesGoverno = new Chart(ctx, {
    type: 'line',
    data: {
      labels: serie.map(s => s.ano),
      datasets: [{
        label: 'Reajuste nominal (%)',
        data: serie.map(s => s.reajuste_pct),
        borderColor: V.teal,
        backgroundColor: 'rgba(31, 158, 137, 0.15)',
        borderWidth: 3,
        pointBackgroundColor: serie.map((s, i) =>
          EVENTOS_CONQUISTA[s.ano] ? V.amarelo : coresPontos[i]
        ),
        pointBorderColor: serie.map(s =>
          EVENTOS_CONQUISTA[s.ano] ? V.amarelo :
          (s.estimado ? CORES.cinza : CORES.branco)
        ),
        pointBorderWidth: serie.map(s => EVENTOS_CONQUISTA[s.ano] ? 3 : 2),
        pointRadius: serie.map(s =>
          EVENTOS_CONQUISTA[s.ano] ? (isMobile ? 6 : 8) :
          (s.reajuste_pct >= 8 ? (isMobile ? 4 : 6) : 3)
        ),
        pointHoverRadius: 10,
        tension: 0.3,
        fill: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: semAnimacao ? false : {
        duration: 600,
        easing: 'easeOutQuart',
        delay: (context) => {
          if (context.type === 'data' && context.mode === 'default') {
            return context.dataIndex * 60;
          }
          return 0;
        },
      },
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 10, bottom: 5 } },
      onClick: (evt, elements) => {
        if (elements.length > 0) {
          mostrarPainelDetalhe(serie[elements[0].index]);
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: { family: FONTE_TEXTO, size: isMobile ? 11 : 13 },
            padding: isMobile ? 8 : 16,
            usePointStyle: true,
          }
        },
        subtitle: {
          display: true,
          text: '🎨 Intensidade = valor do reajuste (roxo ↓ | amarelo ↑) · 🏆 conquista sindical',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11, style: 'italic' },
          color: CORES.cinza,
          padding: { top: 8 },
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          callbacks: {
            title: (items) => {
              const s = serie[items[0].dataIndex];
              return `${s.ano} — ${s.governo || '—'}`;
            },
            label: (ctx) => `Reajuste: +${ctx.raw}%`,
            afterLabel: (ctx) => {
              const s = serie[ctx.dataIndex];
              const linhas = [];

              if (EVENTOS_CONQUISTA[s.ano]) {
                linhas.push('━━━━━━━━━━━━━━━━━━━━━━');
                linhas.push(`🏆 ${EVENTOS_CONQUISTA[s.ano].titulo}`);
                linhas.push(EVENTOS_CONQUISTA[s.ano].impacto);
              }
              if (s.ipca_ano) linhas.push(`IPCA do ano: ${s.ipca_ano}%`);
              if (s.observacao) linhas.push(s.observacao);
              if (s.estimado) linhas.push('⚠️ Dado estimado');
              return linhas;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: !isMobile,
            text: 'Reajuste nominal (%)',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            maxTicksLimit: isMobile ? 5 : 8,
            callback: (v) => v + '%'
          }
        },
        x: {
          title: {
            display: !isMobile,
            text: 'Ano',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { display: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            autoSkip: false,
            maxTicksLimit: isMobile ? 8 : 32,
            maxRotation: isMobile ? 90 : 60,
            minRotation: isMobile ? 90 : 60,
          }
        }
      }
    }
  });

  pausarForaDaViewport(canvas, chartReajustesGoverno);
}

/* ------------------------------------------------------------
   GRÁFICO 1 — PODER DE COMPRA + VALE REFEIÇÃO/ALIMENTAÇÃO + CESTA
   ------------------------------------------------------------ */

function renderizarSalarioReal(dados) {
  dadosGlobais = dados;

  const serie = (dados.serie_temporal || [])
    .slice()
    .map(s => ({ ...s, ano: parseInt(s.ano, 10) }))
    .sort((a, b) => a.ano - b.ano);

  if (!serie.length) return;

  const anoBase = dados.metadados?.ano_base || serie[0].ano;
  const canvas = document.getElementById('grafico-salario-real');
  if (!canvas) return;

  if (chartSalarioReal) {
    chartSalarioReal.destroy();
    chartSalarioReal = null;
  }

  const isMobile = window.innerWidth < 768;
  const semAnimacao = prefereMenosMovimento();
  const ctx = canvas.getContext('2d');

  // Gradiente Viridis para a área de "poder de compra"
  const gradient = ctx.createLinearGradient(0, 0, 0, 500);
  gradient.addColorStop(0, 'rgba(253, 231, 37, 0.20)');  // amarelo
  gradient.addColorStop(1, 'rgba(68, 1, 84, 0.20)');     // roxo

  // Cores dos pontos: escala Viridis do poder de compra
  const coresPoder = viridisEscala(serie.map(s => s.salario_real));

  chartSalarioReal = new Chart(ctx, {
    type: 'line',
    data: {
      labels: serie.map(s => s.ano),
      datasets: [
        {
          label: `Poder de Compra (base 100 = ${anoBase})`,
          data: serie.map(s => s.salario_real),
          borderColor: V.roxo,
          backgroundColor: gradient,
          borderWidth: 3,
          pointBackgroundColor: serie.map((s, i) =>
            EVENTOS_CONQUISTA[s.ano] ? V.amarelo : coresPoder[i]
          ),
          pointBorderColor: serie.map(s => s.estimado ? V.roxo : CORES.branco),
          pointBorderWidth: serie.map(s => s.estimado ? 3 : 2),
          pointRadius: serie.map(s => isMobile ? raioDoPonto(s) * 0.7 : raioDoPonto(s)),
          pointHoverRadius: 10,
          tension: 0.3,
          fill: { target: { value: 100 } },
          yAxisID: 'y',
        },
        {
          label: 'Vale Refeição/Alimentação + Cesta (R$/mês)',
          data: serie.map(s => s.va_vc_total),
          borderColor: V.amarelo,
          backgroundColor: 'rgba(253, 231, 37, 0.10)',
          borderWidth: 3,
          pointBackgroundColor: V.amarelo,
          pointBorderColor: serie.map(s => s.va_vc_estimado ? V.roxo : CORES.branco),
          pointBorderWidth: serie.map(s => s.va_vc_estimado ? 3 : 2),
          pointRadius: isMobile ? 3 : 4,
          pointHoverRadius: 9,
          tension: 0.3,
          fill: false,
          yAxisID: 'y1',
        },
        {
          label: `Referência ${anoBase} (100)`,
          data: serie.map(() => 100),
          borderColor: CORES.cinza,
          borderWidth: 2,
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
          yAxisID: 'y',
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: semAnimacao ? false : {
        duration: 800,
        easing: 'easeOutQuart',
        delay: (context) => {
          if (context.type === 'data' && context.mode === 'default') {
            return context.dataIndex * 40;
          }
          return 0;
        },
      },
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 10, bottom: 5 } },
      onClick: (evt, elements) => {
        if (elements.length > 0) {
          mostrarPainelDetalhe(serie[elements[0].index]);
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: { family: FONTE_TEXTO, size: isMobile ? 11 : 13 },
            padding: isMobile ? 8 : 16,
            usePointStyle: true,
          }
        },
        subtitle: {
          display: !isMobile,
          text: `🟣 Poder de Compra (base 100 = ${anoBase}) | 🟡 Vale Refeição/Alimentação + Cesta (R$/mês, 22 vales)`,
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: 11, style: 'italic' },
          color: CORES.cinza,
          padding: { top: 8 },
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          displayColors: true,
          callbacks: {
            title: (items) => `Ano ${items[0].label}`,
            label: (ctx) => {
              const s = serie[ctx.dataIndex];

              if (ctx.datasetIndex === 0) {
                const dif = s.salario_real - 100;
                const status = dif >= 0 ? '▲ Ganho' : '▼ Perda';
                return [
                  ` Poder de compra: ${s.salario_real.toFixed(1)}`,
                  ` ${status}: ${dif > 0 ? '+' : ''}${dif.toFixed(1)}%`,
                ];
              }

              if (ctx.datasetIndex === 1 && s.va_vc_total) {
                const linhas = [
                  ` Vale Refeição/Alimentação + Cesta: ${formatarRS(s.va_vc_total)}/mês`,
                  ` Vale Alimentação unitário: ${formatarRS(s.va_vr_unit)} × 22 = ${formatarRS(s.va_vr_mes)}`,
                  ` Vale Cesta: ${formatarRS(s.vc_reais)}`,
                ];
                if (s.ano === 1999) {
                  linhas.push('━━━━━━━━━━━━━━━━━━━━━━');
                  linhas.push('✨ Vale Cesta instituído neste ano (ACT 1999/2000)');
                  linhas.push('   Substituiu a cesta básica em alimentos');
                }
                if (s.va_vc_estimado) {
                  linhas.push(' ⚠️ Valor estimado (interpolação IPCA)');
                }
                return linhas;
              }

              return [];
            },
            afterLabel: (ctx) => {
              if (ctx.datasetIndex !== 0) return [];
              const s = serie[ctx.dataIndex];
              const linhas = [];

              if (EVENTOS_CONQUISTA[s.ano]) {
                linhas.push('━━━━━━━━━━━━━━━━━━━━━━');
                linhas.push(`🏆 ${EVENTOS_CONQUISTA[s.ano].titulo}`);
                linhas.push(EVENTOS_CONQUISTA[s.ano].impacto);
              }
              if (s.reajuste_pct) linhas.push(`Reajuste: +${s.reajuste_pct}%`);
              if (s.ipca_ano)     linhas.push(`IPCA: ${s.ipca_ano}%`);
              if (s.governo)      linhas.push(`Governo: ${s.governo}`);
              if (s.estimado)     linhas.push('⚠️ Reajuste estimado');
              return linhas;
            }
          }
        }
      },
      scales: {
        y: {
          type: 'linear',
          position: 'left',
          min: 0,
          max: 120,
          title: {
            display: !isMobile,
            text: `Poder de Compra (base 100 = ${anoBase})`,
            font: { family: FONTE_TEXTO, size: 12 },
            color: V.roxo,
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            color: V.roxo,
            maxTicksLimit: isMobile ? 5 : 8,
          }
        },
        y1: {
          type: 'linear',
          position: 'right',
          min: 0,
          max: 2000,
          title: {
            display: !isMobile,
            text: 'Vale Refeição/Alimentação + Cesta (R$/mês)',
            font: { family: FONTE_TEXTO, size: 12 },
            color: '#8B6B00',    // amarelo escurecido (amarelo puro no branco é ilegível)
          },
          grid: { drawOnChartArea: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            color: '#8B6B00',
            maxTicksLimit: isMobile ? 5 : 8,
            callback: (v) => 'R$ ' + v.toLocaleString('pt-BR'),
          }
        },
        x: {
          title: {
            display: !isMobile,
            text: 'Ano',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { display: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            autoSkip: true,
            maxTicksLimit: isMobile ? 8 : 32,
            maxRotation: isMobile ? 90 : 60,
            minRotation: isMobile ? 90 : 60,
          },
          reverse: false,
        }
      }
    }
  });

  pausarForaDaViewport(canvas, chartSalarioReal);
}

/* ------------------------------------------------------------
   GRÁFICO 2 — REAJUSTES (Viridis por intensidade)
   ------------------------------------------------------------ */

function renderizarReajustes(dados) {
  const serie = (dados.serie_temporal || []).filter(s =>
    typeof s.reajuste_pct === 'number' && s.reajuste_pct > 0
  );
  if (!serie.length) return;

  const inflacaoAnual = serie.map((s, i) => {
    if (i === 0) return 0;
    const inflAnt = serie[i - 1].inflacao_acumulada;
    const inflAtual = s.inflacao_acumulada;
    return ((inflAtual - inflAnt) / inflAnt) * 100;
  });

  const canvas = document.getElementById('grafico-reajustes');
  if (!canvas) return;
  const isMobile = window.innerWidth < 768;
  const ctx = canvas.getContext('2d');

  // Viridis por valor do reajuste
  const coresBarras = viridisEscala(serie.map(s => s.reajuste_pct));

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: serie.map(s => s.ano),
      datasets: [{
        label: 'Reajuste conquistado (%)',
        data: serie.map(s => s.reajuste_pct),
        backgroundColor: coresBarras,
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: prefereMenosMovimento() ? false : { duration: 600 },
      plugins: {
        legend: { display: false },
        subtitle: {
          display: true,
          text: 'Viridis: roxo = reajuste baixo | amarelo = reajuste alto',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11, style: 'italic' },
          color: CORES.cinza,
          padding: { top: 8 },
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          callbacks: {
            title: (items) => `Ano ${items[0].label}`,
            label: (ctx) => `Reajuste: ${ctx.raw}%`,
            afterLabel: (ctx) => {
              const i = ctx.dataIndex;
              const s = serie[i];
              const infl = inflacaoAnual[i];
              const ganho = s.reajuste_pct - infl;
              const status = ganho >= MARGEM_GANHO ? '▲ ganho real' : '▼ perda real';
              return [
                `IPCA do ano: ${infl.toFixed(1)}%`,
                `${status}: ${ganho > 0 ? '+' : ''}${ganho.toFixed(1)} p.p.`,
                `Tipo: ${s.tipo || '—'}`,
                `Governo: ${s.governo || '—'}`,
              ];
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: !isMobile,
            text: 'Reajuste (%)',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            maxTicksLimit: isMobile ? 5 : 8,
          }
        },
        x: {
          grid: { display: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            maxTicksLimit: isMobile ? 8 : 20,
            maxRotation: isMobile ? 90 : 45,
            minRotation: isMobile ? 90 : 45,
          }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   GRÁFICO 3 — GOVERNOS (Viridis divergente)
   ------------------------------------------------------------ */

function renderizarGovernos(dados) {
  const g = dados.por_governo || [];
  if (!g.length) return;

  const canvas = document.getElementById('grafico-governos');
  if (!canvas) return;
  const isMobile = window.innerWidth < 768;
  const ctx = canvas.getContext('2d');

  // Viridis divergente: centro = 0 (neutro), extremos = roxo/amarelo
  const cores = viridisDivergente(g.map(x => x.ganho_medio_anual), 0);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: g.map(x => x.periodo),
      datasets: [{
        label: 'Média de ganho/perda real ao ano (%)',
        data: g.map(x => x.ganho_medio_anual),
        backgroundColor: cores,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: prefereMenosMovimento() ? false : { duration: 600 },
      plugins: {
        legend: { display: false },
        subtitle: {
          display: true,
          text: 'Viridis: roxo = perda · amarelo = ganho',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11, style: 'italic' },
          color: CORES.cinza,
          padding: { top: 8 },
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          callbacks: {
            title: (items) => items[0].label,
            label: (ctx) => {
              const v = ctx.raw;
              return `${v > 0 ? '+' : ''}${v.toFixed(1)}% ao ano`;
            },
            afterLabel: (ctx) => {
              const o = g[ctx.dataIndex].orientacao;
              return o === 'progressista' ? '▲ Progressista'
                   : o === 'conservador'  ? '▼ Conservador'
                   : '⚪ Transição';
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: !isMobile,
            text: 'Média de ganho/perda real ao ano (%)',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
            callback: (v) => (v > 0 ? '+' : '') + v + '%'
          },
          min: -10,
          max: 10,
        },
        y: {
          grid: { display: false },
          ticks: { font: { family: FONTE_TEXTO, size: isMobile ? 11 : 12 } }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   GRÁFICO 4 — ACT vs DC (2 cores Viridis)
   ------------------------------------------------------------ */

function renderizarActVsDc(dados) {
  const d = dados.act_vs_dc || [];
  if (!d.length) return;

  const total = d.reduce((acc, x) => acc + x.total_clausulas, 0);
  const canvas = document.getElementById('grafico-act-dc');
  if (!canvas) return;
  const isMobile = window.innerWidth < 768;
  const ctx = canvas.getContext('2d');

  // Dois extremos da paleta
  const cores = [V.azul, V.amarelo];

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: d.map(x => {
        const pct = ((x.total_clausulas / total) * 100).toFixed(1);
        return `${x.tipo} — ${x.total_clausulas.toLocaleString('pt-BR')} (${pct}%)`;
      }),
      datasets: [{
        data: d.map(x => x.total_clausulas),
        backgroundColor: cores,
        borderColor: CORES.branco,
        borderWidth: 3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '55%',
      animation: prefereMenosMovimento() ? false : { duration: 600 },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { family: FONTE_TEXTO, size: isMobile ? 10 : 12 },
            padding: isMobile ? 8 : 16,
            usePointStyle: true,
          }
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          displayColors: true,
          callbacks: {
            label: (ctx) => {
              const v = ctx.raw;
              const pct = ((v / total) * 100).toFixed(1);
              return `${v.toLocaleString('pt-BR')} cláusulas (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   MACRO — INPC por mandato (Viridis por intensidade)
   ------------------------------------------------------------ */

function renderizarInpcMandato(dadosMacro) {
  const canvas = document.getElementById('grafico-inpc-mandato');
  if (!canvas) return;

  const isMobile = window.innerWidth < 768;
  const ms = dadosMacro.mandatos || [];

  // Viridis por valor do INPC
  const cores = viridisEscala(ms.map(m => m.inpc_acumulado));

  new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: ms.map(m => m.nome),
      datasets: [{
        label: 'INPC acumulado (%)',
        data: ms.map(m => m.inpc_acumulado),
        backgroundColor: cores,
        borderColor: ms.map(m => m.parcial ? V.roxo : 'transparent'),
        borderWidth: ms.map(m => m.parcial ? 2 : 0),
        borderRadius: 4, borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: prefereMenosMovimento() ? false : { duration: 600 },
      plugins: {
        legend: { display: false },
        subtitle: {
          display: true,
          text: 'Viridis: roxo = INPC baixo | amarelo = INPC alto · borda tracejada = dado parcial',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: 10, style: 'italic' },
          color: CORES.cinza, padding: { top: 6 }
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          callbacks: {
            title: (i) => ms[i[0].dataIndex].nome,
            label: (c) => {
              const m = ms[c.dataIndex];
              const l = [` INPC: ${m.inpc_acumulado}%`];
              l.push(m.parcial ? ` ⚠ Parcial (${m.meses_contados}m)` : ` ${m.meses_contados} meses`);
              return l;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: !isMobile, text: 'INPC acumulado (%)',
                   font: { family: FONTE_TEXTO, size: 12 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
                   maxTicksLimit: isMobile ? 5 : 8,
                   callback: (v) => v + '%' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
                   maxRotation: 45, minRotation: isMobile ? 45 : 0 }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   MACRO — Reajuste vs INPC (2 cores Viridis)
   ------------------------------------------------------------ */

function renderizarReajusteVsInpc(dadosMacro) {
  const canvas = document.getElementById('grafico-reajuste-inpc');
  if (!canvas) return;

  const isMobile = window.innerWidth < 768;
  const ms = dadosMacro.mandatos || [];

  new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: ms.map(m => m.nome),
      datasets: [
        {
          label: 'INPC acumulado (%)',
          data: ms.map(m => m.inpc_acumulado),
          backgroundColor: V.roxo,       // frio = referência
          borderRadius: 3, borderSkipped: false,
        },
        {
          label: 'Reajuste Correios (%)',
          data: ms.map(m => m.reajuste_acumulado),
          backgroundColor: V.amarelo,    // quente = resposta
          borderRadius: 3, borderSkipped: false,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: prefereMenosMovimento() ? false : { duration: 600 },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: { family: FONTE_TEXTO, size: isMobile ? 11 : 12 },
            padding: 12, usePointStyle: true, boxWidth: 8,
          }
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          displayColors: true,
          callbacks: {
            title: (i) => ms[i[0].dataIndex].nome,
            label: (c) => ` ${c.dataset.label}: ${c.raw}%`,
            afterBody: (c) => {
              const m = ms[c[0].dataIndex];
              const d = m.reajuste_acumulado - m.inpc_acumulado;
              const st = d >= 0 ? '▲ Ganho real' : '▼ Perda real';
              return `\n${st}: ${d > 0 ? '+' : ''}${d.toFixed(2)} p.p.`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: !isMobile, text: 'Acumulado no mandato (%)',
                   font: { family: FONTE_TEXTO, size: 12 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
                   maxTicksLimit: isMobile ? 5 : 8,
                   callback: (v) => v + '%' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
                   maxRotation: 45, minRotation: isMobile ? 45 : 0 }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   MACRO — Ganho real (Viridis divergente)
   ------------------------------------------------------------ */

function renderizarGanhoReal(dadosMacro) {
  const canvas = document.getElementById('grafico-ganho-real');
  if (!canvas) return;

  const isMobile = window.innerWidth < 768;
  const ms = dadosMacro.mandatos || [];

  // Divergente: centro = 0 (perda/ganho neutro)
  const cores = viridisDivergente(ms.map(m => m.ganho_real_pct), 0);

  new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: ms.map(m => m.nome),
      datasets: [{
        label: 'Ganho real (%)',
        data: ms.map(m => m.ganho_real_pct),
        backgroundColor: cores,
        borderRadius: 4, borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: prefereMenosMovimento() ? false : { duration: 600 },
      plugins: {
        legend: { display: false },
        subtitle: {
          display: true,
          text: 'Viridis: roxo = perda real · amarelo = ganho real',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: 10, style: 'italic' },
          color: CORES.cinza, padding: { top: 6 }
        },
        tooltip: {
          ...TOOLTIP_PADRAO,
          callbacks: {
            title: (i) => ms[i[0].dataIndex].nome,
            label: (c) => {
              const m = ms[c.dataIndex];
              return [
                ` Ganho real: ${m.ganho_real_pct > 0 ? '+' : ''}${m.ganho_real_pct}%`,
                ` INPC: ${m.inpc_acumulado}%  |  Reajuste: ${m.reajuste_acumulado}%`
              ];
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: !isMobile, text: 'Ganho/perda real acumulado (%)',
                   font: { family: FONTE_TEXTO, size: 12 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { font: { family: FONTE_TEXTO, size: isMobile ? 10 : 11 },
                   callback: (v) => (v > 0 ? '+' : '') + v + '%' }
        },
        y: {
          grid: { display: false },
          ticks: { font: { family: FONTE_TEXTO, size: isMobile ? 11 : 12 } }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   TABELA DE MANDATOS
   ------------------------------------------------------------ */

function renderizarTabelaMandatos(dadosMacro) {
  const el = document.getElementById('tabela-mandatos');
  if (!el) return;

  const mandatos = dadosMacro.mandatos || [];
  const coresGanho = viridisDivergente(mandatos.map(m => m.ganho_real_pct), 0);

  const linhas = mandatos.map((m, i) => {
    const cor = coresGanho[i];
    const tag = m.parcial ? ' ⚠' : '';
    const sinal = m.ganho_real_pct >= 0 ? '+' : '';
    return `
      <tr>
        <td><strong>${m.nome}</strong>${tag}</td>
        <td>${m.periodo[0]}-${m.periodo[1]}</td>
        <td style="text-align:right">${m.inpc_acumulado}%</td>
        <td style="text-align:right">${m.reajuste_acumulado}%</td>
        <td style="text-align:right">
          <span style="display:inline-block;padding:2px 8px;border-radius:4px;
                       background:${cor};color:#fff;font-weight:700;font-size:0.85rem;">
            ${sinal}${m.ganho_real_pct}%
          </span>
        </td>
      </tr>`;
  }).join('');

  el.innerHTML = `
    <table class="tabela-mandatos-grid">
      <thead>
        <tr>
          <th>Mandato</th>
          <th>Período</th>
          <th style="text-align:right">INPC</th>
          <th style="text-align:right">Reajuste</th>
          <th style="text-align:right">Ganho real</th>
        </tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
    <p class="tabela-nota">
      ⚠ = mandato com dado parcial (Lula 3 até set/2026).<br>
      Cores Viridis: roxo = perda · amarelo = ganho. Fonte: IBGE/SIDRA (Tabela 1736) e ACTs/DCs.
    </p>`;
}

/* ------------------------------------------------------------
   TIMELINE
   ------------------------------------------------------------ */

function renderizarTimeline(dados) {
  const container = document.getElementById('timeline-financeira-lista');
  if (!container) return;

  const eventos = dados.eventos_timeline || [];
  if (!eventos.length) {
    container.innerHTML =
      '<p style="text-align:center;color:#888;">Sem eventos cadastrados.</p>';
    return;
  }

  const icones = { ganho: '🟢', perda: '🔴', neutro: '⚪' };
  const corPorTipo = {
    ganho:  V.amarelo,
    perda:  V.roxo,
    neutro: CORES.cinza,
  };

  container.innerHTML = eventos.map(ev => {
    const tipo = ev.tipo || 'neutro';
    const corImpacto = corPorTipo[tipo] || CORES.cinza;
    const icone = icones[tipo] || '•';

    return `
      <div class="timeline-evento">
        <div class="marcador"
             style="background:${corImpacto};
                    box-shadow:0 0 0 3px ${corImpacto};">
        </div>
        <div class="conteudo" style="border-color:${corImpacto};">
          <div class="ano">
            ${icone} ${ev.ano} — ${ev.impacto || ''}
          </div>
          <div class="titulo">${ev.titulo || ''}</div>
          <div class="descricao">${ev.descricao || ''}</div>
          <div class="fonte">Fonte: ${ev.fonte || '—'}</div>
        </div>
      </div>
    `;
  }).join('');
}

/* ------------------------------------------------------------
   INICIALIZAÇÃO
   ------------------------------------------------------------ */

(async function init() {
  try {
    const dados = await carregarDados('data/financeiro.json');
    dadosGlobais = dados;

    renderKPIs(dados);
    renderizarTimeline(dados);

    lazyChart('grafico-reajustes-governo', () => renderizarReajustesGoverno(dados));
    lazyChart('grafico-salario-real',      () => renderizarSalarioReal(dados));
    lazyChart('grafico-reajustes',         () => renderizarReajustes(dados));
    lazyChart('grafico-governos',          () => renderizarGovernos(dados));
    lazyChart('grafico-act-dc',            () => renderizarActVsDc(dados));

    try {
      const macro = await carregarDados('data/inpc_mandato.json');
      dadosMacroGlobal = macro;
      lazyChart('grafico-inpc-mandato',  () => renderizarInpcMandato(macro));
      lazyChart('grafico-reajuste-inpc', () => renderizarReajusteVsInpc(macro));
      lazyChart('grafico-ganho-real',    () => renderizarGanhoReal(macro));
      renderizarTabelaMandatos(macro);
      console.log('[Raio-X/Financeiro] Contexto macro carregado.');
    } catch (e) {
      console.warn('[Raio-X/Financeiro] inpc_mandato.json indisponível:', e.message);
    }

    console.log('[Raio-X/Financeiro] Página inicializada (lazy load, Viridis).');
    console.log(`[Raio-X/Financeiro] Base: ${dados.metadados?.ano_base}`);
    console.log(`[Raio-X/Financeiro] Período: ${dados.metadados?.periodo_analisado}`);
    console.log(`[Raio-X/Financeiro] Greves: ${dados.metadados?.total_greves_historicas}`);
  } catch (err) {
    console.error('[Raio-X/Financeiro]', err);
    mostrarErro('Não foi possível carregar data/financeiro.json');
  }
})();