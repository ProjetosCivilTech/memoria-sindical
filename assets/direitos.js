/* ============================================================
   Batalha pelos Direitos — Gráficos Dinâmicos
   Memória Sindical | Raio-X da Luta
   Versão: heatmap + barras + divergências + lazy loading
   ============================================================ */

'use strict';

const CORES = {
  vermelho:      '#C8102E',
  vermelhoEsc:   '#8B0000',
  vermelhoClaro: 'rgba(200, 16, 46, 0.12)',
  verde:         '#1E7A3C',
  cinza:         '#888888',
  cinzaEscuro:   '#555555',
  preto:         '#1A1A1A',
  branco:        '#FFFFFF',
};

const CORES_TEMA = {
  saude:       '#C8102E',
  familia:     '#E85D75',
  diversidade: '#8B0000',
  condicoes:   '#A00D24',
  sindical:    '#2D2D2D',
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

const LABEL_MAX = 32;

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

function encurtarLabel(txt, max = LABEL_MAX) {
  if (!txt) return '';
  return txt.length > max ? txt.slice(0, max - 1) + '…' : txt;
}

/* ------------------------------------------------------------
   KPIs
   ------------------------------------------------------------ */

function renderKPIs(dados) {
  const t = dados.totais || {};
  const setText = (id, valor) => {
    const el = document.getElementById(id);
    if (el) el.textContent = valor ?? '—';
  };

  setText('kpi-total', (t.clausulas_nao_financeiras || 0).toLocaleString('pt-BR'));
  setText('kpi-temas', Object.keys(dados.por_tema || {}).length);
  setText('kpi-ano-produtivo', t.ano_mais_produtivo);
  setText('kpi-ano-produtivo-qtd', (t.ano_mais_produtivo_qtd || 0) + ' cláusulas');
  setText('kpi-risco', t.direitos_em_risco);
}

/* ------------------------------------------------------------
   HEATMAP: DIREITOS POR GOVERNO
   Substitui o radar — HTML+CSS puro, mais legível
   ------------------------------------------------------------ */

function renderHeatmapGovernos(dados) {
  const container = document.getElementById('heatmap-governos');
  if (!container) {
    console.warn('[Raio-X] #heatmap-governos não encontrado');
    return;
  }

  const temas = Object.entries(dados.por_tema || {});
  const governos = dados.radar_governos || [];

  if (!temas.length || !governos.length) {
    container.innerHTML = '<p style="text-align:center;color:#888;">Sem dados.</p>';
    return;
  }

  const linhasHtml = governos.map(g => {
    const celulas = temas.map(([key, t]) => {
      const score = (g.scores && g.scores[key]) || 0;
      const cor = corHeatmap(score);
      const textoCor = score >= 60 ? '#FFFFFF' : CORES.preto;

      return `
        <div class="heatmap-celula"
             style="background:${cor};color:${textoCor};"
             title="${g.nome} — ${t.rotulo}: ${score}/100">
          <span class="heatmap-score">${score}</span>
        </div>
      `;
    }).join('');

    return `
      <div class="heatmap-linha">
        <div class="heatmap-rotulo-linha">
          <span class="heatmap-dot" style="background:${g.cor};"></span>
          <span>${g.nome}</span>
        </div>
        ${celulas}
      </div>
    `;
  }).join('');

  const cabecalho = temas.map(([, t]) =>
    `<div class="heatmap-celula heatmap-celula-titulo">${t.rotulo}</div>`
  ).join('');

  container.innerHTML = `
    <div class="heatmap-grid">
      <div class="heatmap-linha heatmap-linha-titulo">
        <div class="heatmap-rotulo-linha"></div>
        ${cabecalho}
      </div>
      ${linhasHtml}
    </div>
    <div class="heatmap-legenda">
      <span class="heatmap-legenda-item">
        <span class="heatmap-legenda-cor" style="background:#F4D7DC;"></span> Poucos direitos (0–30)
      </span>
      <span class="heatmap-legenda-item">
        <span class="heatmap-legenda-cor" style="background:#E85D75;"></span> Médio (31–60)
      </span>
      <span class="heatmap-legenda-item">
        <span class="heatmap-legenda-cor" style="background:#C8102E;"></span> Muitos (61–80)
      </span>
      <span class="heatmap-legenda-item">
        <span class="heatmap-legenda-cor" style="background:#8B0000;"></span> Muitíssimos (81–100)
      </span>
    </div>
  `;
}

function corHeatmap(score) {
  if (score >= 81) return '#8B0000';
  if (score >= 61) return '#C8102E';
  if (score >= 31) return '#E85D75';
  if (score >= 16) return '#F4A0B0';
  return '#F4D7DC';
}

/* ------------------------------------------------------------
   GRÁFICO — VOLUME POR TEMA
   ------------------------------------------------------------ */

function renderTemas(dados) {
  const temas = Object.entries(dados.por_tema || {});
  if (!temas.length) return;

  const canvas = document.getElementById('grafico-temas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: temas.map(([, t]) => t.rotulo),
      datasets: [{
        label: 'Cláusulas',
        data: temas.map(([, t]) => t.total),
        backgroundColor: temas.map(([k]) => CORES_TEMA[k] || CORES.cinza),
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
        tooltip: {
          ...TOOLTIP_PADRAO,
          callbacks: {
            title: (items) => items[0].label,
            label: (ctx) => `${ctx.raw} cláusulas`,
            afterLabel: (ctx) => {
              const [, t] = temas[ctx.dataIndex];
              const ex = t.exemplos || '';
              const linhas = [];
              for (let i = 0; i < ex.length; i += 50) {
                linhas.push(ex.slice(i, i + 50));
              }
              return ['Exemplos:', ...linhas];
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Total de cláusulas',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { font: { family: FONTE_TEXTO, size: 11 } }
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
   GRÁFICO — DIVERGÊNCIAS FENTECT vs FINDECT
   ------------------------------------------------------------ */

function renderDivergencias(dados) {
  const div = dados.divergencias_fentect_findect || [];
  if (!div.length) return;

  const canvas = document.getElementById('grafico-divergencias');
  if (!canvas) return;

  const ordenado = [...div].sort((a, b) =>
    a.score_similaridade - b.score_similaridade
  );

  const ctx = canvas.getContext('2d');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ordenado.map(d => encurtarLabel(d.id_canonico, 35)),
      datasets: [{
        label: 'Similaridade',
        data: ordenado.map(d => d.score_similaridade * 100),
        backgroundColor: ordenado.map(d =>
          d.tipo === 'material' ? CORES.vermelho : CORES.cinza
        ),
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          ...TOOLTIP_PADRAO,
          callbacks: {
            title: (items) => ordenado[items[0].dataIndex].id_canonico,
            label: (ctx) => {
              const d = ordenado[ctx.dataIndex];
              return [
                `Similaridade: ${(d.score_similaridade * 100).toFixed(0)}%`,
                `Tipo: ${d.tipo}`,
                `Magnitude: ${d.magnitude}`,
                `Ano: ${d.ano}`,
              ];
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          max: 100,
          title: {
            display: true,
            text: 'Similaridade (%) — menor = mais divergente',
            font: { family: FONTE_TEXTO, size: 12 }
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            callback: (v) => v + '%'
          }
        },
        y: {
          grid: { display: false },
          ticks: {
            font: { family: FONTE_TEXTO, size: 11 },
            color: CORES.preto,
          }
        }
      }
    }
  });
}

/* ------------------------------------------------------------
   TIMELINE
   ------------------------------------------------------------ */

function renderTimeline(dados) {
  const container = document.getElementById('timeline-direitos');
  if (!container) return;

  const eventos = dados.eventos_timeline || [];
  if (!eventos.length) {
    container.innerHTML = '<p style="text-align:center;color:#888;">Sem eventos cadastrados.</p>';
    return;
  }

  const icone = {
    'Saúde':       '🩺',
    'Família':     '👶',
    'Diversidade': '🌈',
    'Condições':   '🚚',
    'Sindical':    '✊',
  };

  container.innerHTML = eventos.map(ev => {
    const emoji = icone[ev.categoria] || '•';
    return `
      <div class="timeline-evento">
        <div class="marcador"></div>
        <div class="conteudo">
          <div class="ano">${ev.ano} — <span style="font-size:0.9em;">${emoji} ${ev.categoria || ''}</span></div>
          <div class="titulo">${ev.titulo || ''}</div>
          <div class="descricao">${ev.descricao || ''}</div>
          <div class="fonte">Fonte: ${ev.fonte || '—'}</div>
        </div>
      </div>
    `;
  }).join('');
}

/* ------------------------------------------------------------
   CARDS POR TEMA
   ------------------------------------------------------------ */

function renderCardsTemas(dados) {
  const container = document.getElementById('cards-temas');
  if (!container) return;

  const temas = Object.entries(dados.por_tema || {});
  if (!temas.length) return;

  container.innerHTML = temas.map(([key, t]) => {
    const cor = CORES_TEMA[key] || CORES.vermelho;
    return `
      <div class="kpi" style="border-left-color:${cor};">
        <div class="rotulo">${t.total} cláusulas</div>
        <div class="valor" style="font-size:1.35rem;">${t.rotulo}</div>
        <div class="variacao">${t.exemplos || ''}</div>
      </div>
    `;
  }).join('');
}

/* ------------------------------------------------------------
   INICIALIZAÇÃO
   ------------------------------------------------------------ */

(async function init() {
  try {
    const dados = await carregarDados('data/direitos.json');

    renderKPIs(dados);
    renderTimeline(dados);
    renderCardsTemas(dados);
    renderHeatmapGovernos(dados);

    lazyChart('grafico-temas',        () => renderTemas(dados));
    lazyChart('grafico-divergencias', () => renderDivergencias(dados));

    console.log('[Raio-X/Direitos] Página inicializada.');
  } catch (err) {
    console.error('[Raio-X/Direitos]', err);
    mostrarErro('Não foi possível carregar data/direitos.json');
  }
})();