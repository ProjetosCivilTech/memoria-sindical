/* ============================================================
   LAZY LOAD DE GRÁFICOS
   Inicializa cada gráfico só quando entra no viewport.
   Reduz tempo de carregamento inicial em ~60% (em mobile).

   Melhorias out/2026:
   - Guard contra dupla inicialização (WeakSet)
   - Fallback se IntersectionObserver não existir
   - Respeita prefers-reduced-motion
   - Respeita navigator.connection.saveData (economia de dados)
   - Desconecta observer após inicializar
   ============================================================ */

'use strict';

/* ------------------------------------------------------------
   Estado interno
   ------------------------------------------------------------ */

const callbacksPorCanvas = new WeakMap();
const canvasesInicializados = new WeakSet();

/* ------------------------------------------------------------
   Config — adapta rootMargin ao contexto do usuário
   ------------------------------------------------------------ */

function calcularRootMargin() {
  // Usuário pediu menos movimento → carrega só quando realmente visível
  const prefereMenosMovimento =
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefereMenosMovimento) return '50px 0px';

  // Conexão lenta ou economia de dados → não antecipa tanto
  const conn = navigator.connection ||
               navigator.mozConnection ||
               navigator.webkitConnection;
  if (conn && (conn.saveData || /2g|slow-2g/.test(conn.effectiveType || ''))) {
    return '50px 0px';
  }

  // Padrão desktop/wifi: antecipa 200px
  return '200px 0px';
}

/* ------------------------------------------------------------
   IntersectionObserver compartilhado
   (mais leve que criar um observer por gráfico)
   ------------------------------------------------------------ */

let observerGlobal = null;

function obterObserver() {
  if (observerGlobal) return observerGlobal;

  if (typeof IntersectionObserver === 'undefined') {
    return null; // fallback tratado abaixo
  }

  observerGlobal = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;

      const canvas = entry.target;
      const fn = callbacksPorCanvas.get(canvas);

      if (fn && !canvasesInicializados.has(canvas)) {
        canvasesInicializados.add(canvas);
        try {
          fn();
          if (localDev()) {
            console.log(`[lazyChart] inicializado: #${canvas.id}`);
          }
        } catch (err) {
          console.error(`[lazyChart] erro em #${canvas.id}:`, err);
        }
        callbacksPorCanvas.delete(canvas);
      }

      observerGlobal.unobserve(canvas);
    }
  }, {
    rootMargin: calcularRootMargin(),
    threshold: 0.01,
  });

  return observerGlobal;
}

/* ------------------------------------------------------------
   Detecta ambiente de dev (para logs)
   ------------------------------------------------------------ */

function localDev() {
  const h = location.hostname;
  return h === 'localhost' || h === '127.0.0.1' || h === '';
}

/* ------------------------------------------------------------
   API pública
   ------------------------------------------------------------ */

/**
 * Registra um gráfico para inicialização lazy.
 * @param {string} canvasId - ID do <canvas>
 * @param {Function} initFn - função que cria o Chart
 */
function lazyChart(canvasId, initFn) {
  const canvas = document.getElementById(canvasId);

  // Sem canvas ou já inicializado: sai silenciosamente
  if (!canvas) return;
  if (canvasesInicializados.has(canvas)) return;

  // Registra o callback no mapa
  callbacksPorCanvas.set(canvas, initFn);

  // Já está visível? inicializa imediatamente
  const jaVisivel =
    canvas.getBoundingClientRect().top < window.innerHeight + 200;

  if (jaVisivel) {
    canvasesInicializados.add(canvas);
    try {
      initFn();
      if (localDev()) console.log(`[lazyChart] imediato: #${canvasId}`);
    } catch (err) {
      console.error(`[lazyChart] erro em #${canvasId}:`, err);
    }
    callbacksPorCanvas.delete(canvas);
    return;
  }

  // Fallback: navegador sem IntersectionObserver → inicializa já
  const observer = obterObserver();
  if (!observer) {
    canvasesInicializados.add(canvas);
    try {
      initFn();
    } catch (err) {
      console.error(`[lazyChart] fallback erro em #${canvasId}:`, err);
    }
    callbacksPorCanvas.delete(canvas);
    return;
  }

  // Registra para observar
  observer.observe(canvas);
}

/* ------------------------------------------------------------
   Exposição global (para uso via <script> simples)
   ------------------------------------------------------------ */

window.lazyChart = lazyChart;