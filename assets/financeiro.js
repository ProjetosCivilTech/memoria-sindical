/* ============================================================
   Batalha pelo Salário — Gráficos Dinâmicos
   Memória Sindical | Raio-X da Luta
   Versão: eixo duplo (Poder de Compra + VA/VC) + loop + lazy
   ============================================================ */

'use strict';

/* ------------------------------------------------------------
   CORES E FONTES
   ------------------------------------------------------------ */

const CORES = {
  vermelho:      '#C8102E',
  vermelhoEsc:   '#8B0000',
  vermelhoClaro: 'rgba(200, 16, 46, 0.12)',
  vermelhoArea:  'rgba(200, 16, 46, 0.20)',
  cinza:         '#888888',
  cinzaClaro:    'rgba(136, 136, 136, 0.10)',
  ganho:         '#1E7A3C',
  perda:         '#8B0000',
  conquista:     '#E6A817',
  preto:         '#1A1A1A',
  branco:        '#FFFFFF',
};

const CORES_GOVERNO = {
  progressista: '#1E7A3C',
  conservador:  '#C8102E',
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
    titulo: 'Criação do Vale Cesta (VC)',
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
const PAUSA_LOOP_MS = 4000;

/* ------------------------------------------------------------
   VARIÁVEIS GLOBAIS
   ------------------------------------------------------------ */

let chartSalarioReal = null;
let chartReajustesGoverno = null;
let loopTimeoutSalario = null;
let loopTimeoutGoverno = null;
let dadosGlobais = null;

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
      ctx.fillStyle = 'rgba(230, 168, 23, 0.20)';
      ctx.fill();
      ctx.strokeStyle = CORES.conquista;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.font = '12px sans-serif';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = CORES.preto;
      ctx.fillText('🏆', xPos, yTrophy);

      ctx.font = `bold 10px ${FONTE_TEXTO}`;
      ctx.textBaseline = 'top';
      ctx.fillStyle = CORES.conquista;
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
    <div style="background:${CORES.vermelho};color:#fff;padding:1rem;
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
  if (EVENTOS_CONQUISTA[s.ano]) return CORES.conquista;
  if (typeof s.reajuste_pct === 'number' &&
      typeof s.ipca_ano === 'number' &&
      s.reajuste_pct > s.ipca_ano + MARGEM_GANHO) {
    return CORES.ganho;
  }
  return CORES.perda;
}

function raioDoPonto(s) {
  if (EVENTOS_CONQUISTA[s.ano]) return 8;
  if (ANOS_CHAVE.includes(s.ano)) return 6;
  return 3;
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
   GRÁFICO 0 — REAJUSTES POR GOVERNO (linha)
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

  const ctx = canvas.getContext('2d');

  const corPonto = (s) => {
    if (EVENTOS_CONQUISTA[s.ano]) return CORES.conquista;
    return CORES_GOVERNO[s.orientacao] || CORES_GOVERNO['—'];
  };

  chartReajustesGoverno = new Chart(ctx, {
    type: 'line',
    data: {
      labels: serie.map(s => s.ano),
      datasets: [{
        label: 'Reajuste nominal (%)',
        data: serie.map(s => s.reajuste_pct),
        borderColor: CORES.vermelho,
        backgroundColor: 'rgba(200, 16, 46, 0.12)',
        borderWidth: 3,
        pointBackgroundColor: serie.map(corPonto),
        pointBorderColor: serie.map(s =>
          EVENTOS_CONQUISTA[s.ano] ? CORES.conquista :
          (s.estimado ? CORES.cinza : CORES.branco)
        ),
        pointBorderWidth: serie.map(s =>
          EVENTOS_CONQUISTA[s.ano] ? 3 : (s.estimado ? 2 : 2)
        ),
        pointRadius: serie.map(s =>
          EVENTOS_CONQUISTA[s.ano] ? 8 :
          (s.reajuste_pct >= 8 ? 6 : 3)
        ),
        pointHoverRadius: 10,
        tension: 0.3,
        fill: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 400,
        easing: 'easeOutQuart',
        delay: (context) => {
          if (context.type === 'data' && context.mode === 'default') {
            return context.dataIndex * 90;
          }
          return 0;
        },
        onComplete: () => {
          if (loopTimeoutGoverno) clearTimeout(loopTimeoutGoverno);
          loopTimeoutGoverno = setTimeout(reiniciarReajustesGoverno, PAUSA_LOOP_MS);
        },
      },
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 10, bottom: 5 } },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: { family: FONTE_TEXTO, size: 13 },
            padding: 16,
            usePointStyle: true,
          }
        },
        subtitle: {
          display: true,
          text: '🟢 Progressista | 🔴 Conservador | ⚪ Transição | 🟡 Conquista sindical',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: 11, style: 'italic' },
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
            display: true,
            text: 'Reajuste nominal (%)',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            callback: (v) => v + '%'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Ano',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { display: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            autoSkip: false,
            maxRotation: 60,
            minRotation: 60,
          }
        }
      }
    }
  });

  canvas.addEventListener('mouseenter', () => {
    if (loopTimeoutGoverno) {
      clearTimeout(loopTimeoutGoverno);
      loopTimeoutGoverno = null;
    }
  });
  canvas.addEventListener('mouseleave', () => {
    if (chartReajustesGoverno && !loopTimeoutGoverno) {
      loopTimeoutGoverno = setTimeout(reiniciarReajustesGoverno, 2000);
    }
  });
  canvas.addEventListener('dblclick', () => {
    if (loopTimeoutGoverno) clearTimeout(loopTimeoutGoverno);
    loopTimeoutGoverno = null;
    reiniciarReajustesGoverno();
  });
}

function reiniciarReajustesGoverno() {
  if (!chartReajustesGoverno || !dadosGlobais) return;
  if (loopTimeoutGoverno) {
    clearTimeout(loopTimeoutGoverno);
    loopTimeoutGoverno = null;
  }
  chartReajustesGoverno.destroy();
  chartReajustesGoverno = null;
  renderizarReajustesGoverno(dadosGlobais);
}

/* ------------------------------------------------------------
   GRÁFICO 1 — PODER DE COMPRA + VA/VC (EIXO DUPLO)
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

  const ctx = canvas.getContext('2d');

  const gradient = ctx.createLinearGradient(0, 0, 0, 400);
  gradient.addColorStop(0, 'rgba(30, 122, 60, 0.15)');
  gradient.addColorStop(1, 'rgba(200, 16, 46, 0.15)');

  chartSalarioReal = new Chart(ctx, {
    type: 'line',
    data: {
      labels: serie.map(s => s.ano),
      datasets: [
        {
          label: `Poder de Compra (base 100 = ${anoBase})`,
          data: serie.map(s => s.salario_real),
          borderColor: CORES.vermelho,
          backgroundColor: gradient,
          borderWidth: 3,
          pointBackgroundColor: serie.map(corDoPonto),
          pointBorderColor: serie.map(s => s.estimado ? CORES.conquista : CORES.branco),
          pointBorderWidth: serie.map(s => s.estimado ? 3 : 2),
          pointRadius: serie.map(raioDoPonto),
          pointHoverRadius: 10,
          tension: 0.3,
          fill: { target: { value: 100 } },
          yAxisID: 'y',
        },
        {
          label: 'VA + VC (R$/mês)',
          data: serie.map(s => s.va_vc_total),
          borderColor: CORES.ganho,
          backgroundColor: 'rgba(30, 122, 60, 0.10)',
          borderWidth: 3,
          pointBackgroundColor: CORES.ganho,
          pointBorderColor: serie.map(s => s.va_vc_estimado ? CORES.conquista : CORES.branco),
          pointBorderWidth: serie.map(s => s.va_vc_estimado ? 3 : 2),
          pointRadius: 4,
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
      animation: {
        duration: 400,
        easing: 'easeOutQuart',
        delay: (context) => {
          if (context.type === 'data' && context.mode === 'default') {
            return context.dataIndex * 90;
          }
          return 0;
        },
        onComplete: () => {
          if (loopTimeoutSalario) clearTimeout(loopTimeoutSalario);
          loopTimeoutSalario = setTimeout(reiniciarAnimacaoSalario, PAUSA_LOOP_MS);
        },
      },
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 10, bottom: 5 } },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: { family: FONTE_TEXTO, size: 13 },
            padding: 16,
            usePointStyle: true,
          }
        },
        subtitle: {
          display: true,
          text: `🔴 Poder de Compra (salário-base, base 100 = ${anoBase}) | 🟢 VA + VC em R$/mês (23 vales + cesta) — VC instituído no ACT 1999/2000`,
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
                const status = dif >= 0 ? '✅ Ganho' : '❌ Perda';
                return [
                  ` Poder de compra: ${s.salario_real.toFixed(1)}`,
                  ` ${status}: ${dif > 0 ? '+' : ''}${dif.toFixed(1)}%`,
                ];
              }

              if (ctx.datasetIndex === 1 && s.va_vc_total) {
                const linhas = [
                  ` VA + VC total: ${formatarRS(s.va_vc_total)}/mês`,
                  ` VR unitário: ${formatarRS(s.va_vr_unit)} × 23 = ${formatarRS(s.va_vr_mes)}`,
                  ` Vale Cesta: ${formatarRS(s.vc_reais)}`,
                ];
                if (s.ano === 1999) {
                  linhas.push('━━━━━━━━━━━━━━━━━━━━━━');
                  linhas.push('✨ VC instituído neste ano (ACT 1999/2000)');
                  linhas.push('   Substituiu a cesta básica em alimentos');
                }
                if (s.va_vc_estimado) {
                  linhas.push(' ⚠️ VC estimado (interpolação IPCA)');
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
            display: true,
            text: `Poder de Compra (base 100 = ${anoBase})`,
            font: { family: FONTE_TEXTO, size: 12 },
            color: CORES.vermelho,
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            color: CORES.vermelho,
          }
        },
        y1: {
          type: 'linear',
          position: 'right',
          min: 0,
          max: 2000,
          title: {
            display: true,
            text: 'VA + VC (R$ / mês)',
            font: { family: FONTE_TEXTO, size: 12 },
            color: CORES.ganho,
          },
          grid: { drawOnChartArea: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            color: CORES.ganho,
            callback: (v) => 'R$ ' + v.toLocaleString('pt-BR'),
          }
        },
        x: {
          title: {
            display: true,
            text: 'Ano',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { display: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            autoSkip: false,
            maxRotation: 60,
            minRotation: 60,
          },
          reverse: false,
        }
      }
    }
  });

  canvas.addEventListener('mouseenter', () => {
    if (loopTimeoutSalario) {
      clearTimeout(loopTimeoutSalario);
      loopTimeoutSalario = null;
    }
  });
  canvas.addEventListener('mouseleave', () => {
    if (chartSalarioReal && !loopTimeoutSalario) {
      loopTimeoutSalario = setTimeout(reiniciarAnimacaoSalario, 2000);
    }
  });
  canvas.addEventListener('dblclick', () => {
    if (loopTimeoutSalario) clearTimeout(loopTimeoutSalario);
    loopTimeoutSalario = null;
    reiniciarAnimacaoSalario();
  });
}

function reiniciarAnimacaoSalario() {
  if (!chartSalarioReal || !dadosGlobais) return;
  if (loopTimeoutSalario) {
    clearTimeout(loopTimeoutSalario);
    loopTimeoutSalario = null;
  }
  chartSalarioReal.destroy();
  chartSalarioReal = null;
  renderizarSalarioReal(dadosGlobais);
}

/* ------------------------------------------------------------
   GRÁFICO 2 — REAJUSTES (verde = ganho | cinza = perda)
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

  const ctx = document.getElementById('grafico-reajustes').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: serie.map(s => s.ano),
      datasets: [{
        label: 'Reajuste conquistado (%)',
        data: serie.map(s => s.reajuste_pct),
        backgroundColor: serie.map((s, i) =>
          s.reajuste_pct >= inflacaoAnual[i] + MARGEM_GANHO
            ? CORES.ganho
            : CORES.cinza
        ),
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        subtitle: {
          display: true,
          text: 'Verde = ganho real (acima do IPCA) | Cinza = perda real',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: 11, style: 'italic' },
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
              const status = ganho >= MARGEM_GANHO ? '✅ ganho real' : '❌ perda real';
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
            display: true,
            text: 'Reajuste (%)',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { font: { family: FONTE_TEXTO, size: 11 } }
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: FONTE_TEXTO, size: 11 } }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   GRÁFICO 3 — GOVERNOS
   ------------------------------------------------------------ */

function renderizarGovernos(dados) {
  const g = dados.por_governo || [];
  if (!g.length) return;

  const ctx = document.getElementById('grafico-governos').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: g.map(x => x.periodo),
      datasets: [{
        label: 'Média de ganho/perda real ao ano (%)',
        data: g.map(x => x.ganho_medio_anual),
        backgroundColor: g.map(x => {
          if (x.orientacao === 'progressista') return CORES.ganho;
          if (x.orientacao === 'conservador')  return CORES.perda;
          return CORES.cinza;
        }),
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        subtitle: {
          display: true,
          text: 'Média anual de ganho real (reajuste − IPCA) por período',
          position: 'bottom',
          font: { family: FONTE_TEXTO, size: 11, style: 'italic' },
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
              return o === 'progressista' ? '🟢 Progressista'
                   : o === 'conservador'  ? '🔴 Conservador'
                   : '⚪ Transição';
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Média de ganho/perda real ao ano (%)',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            callback: (v) => (v > 0 ? '+' : '') + v + '%'
          },
          min: -10,
          max: 10,
        },
        y: {
          grid: { display: false },
          ticks: { font: { family: FONTE_TEXTO, size: 12 } }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   GRÁFICO 4 — ACT vs DC
   ------------------------------------------------------------ */

function renderizarActVsDc(dados) {
  const d = dados.act_vs_dc || [];
  if (!d.length) return;

  const total = d.reduce((acc, x) => acc + x.total_clausulas, 0);
  const ctx = document.getElementById('grafico-act-dc').getContext('2d');
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: d.map(x => {
        const pct = ((x.total_clausulas / total) * 100).toFixed(1);
        return `${x.tipo} — ${x.total_clausulas.toLocaleString('pt-BR')} cláusulas (${pct}%)`;
      }),
      datasets: [{
        data: d.map(x => x.total_clausulas),
        backgroundColor: [CORES.vermelho, CORES.cinza],
        borderColor: CORES.branco,
        borderWidth: 3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '55%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { family: FONTE_TEXTO, size: 12 },
            padding: 16,
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

  const icones = {
    ganho:  '🟢',
    perda:  '🔴',
    neutro: '⚪',
  };

  container.innerHTML = eventos.map(ev => {
    const tipo = ev.tipo || 'neutro';
    const corImpacto = tipo === 'ganho' ? CORES.ganho
                     : tipo === 'perda' ? CORES.perda
                     : CORES.cinza;
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
   PAUSA / RETOMA QUANDO A ABA PERDE FOCO
   ------------------------------------------------------------ */

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (loopTimeoutSalario) {
      clearTimeout(loopTimeoutSalario);
      loopTimeoutSalario = null;
    }
    if (loopTimeoutGoverno) {
      clearTimeout(loopTimeoutGoverno);
      loopTimeoutGoverno = null;
    }
  } else {
    if (!loopTimeoutSalario && chartSalarioReal) {
      loopTimeoutSalario = setTimeout(reiniciarAnimacaoSalario, PAUSA_LOOP_MS);
    }
    if (!loopTimeoutGoverno && chartReajustesGoverno) {
      loopTimeoutGoverno = setTimeout(reiniciarReajustesGoverno, PAUSA_LOOP_MS);
    }
  }
});

/* ------------------------------------------------------------
   INICIALIZAÇÃO
   ------------------------------------------------------------ */

(async function init() {
  try {
    const dados = await carregarDados('data/financeiro.json');

    renderKPIs(dados);
    renderizarTimeline(dados);

    lazyChart('grafico-reajustes-governo', () => renderizarReajustesGoverno(dados));
    lazyChart('grafico-salario-real',      () => renderizarSalarioReal(dados));
    lazyChart('grafico-reajustes',         () => renderizarReajustes(dados));
    lazyChart('grafico-governos',          () => renderizarGovernos(dados));
    lazyChart('grafico-act-dc',            () => renderizarActVsDc(dados));

    console.log('[Raio-X/Financeiro] Página inicializada (lazy load).');
    console.log(`[Raio-X/Financeiro] Base: ${dados.metadados?.ano_base}`);
    console.log(`[Raio-X/Financeiro] Período: ${dados.metadados?.periodo_analisado}`);
    console.log(`[Raio-X/Financeiro] Greves: ${dados.metadados?.total_greves_historicas}`);
  } catch (err) {
    console.error('[Raio-X/Financeiro]', err);
    mostrarErro('Não foi possível carregar data/financeiro.json');
  }
})();