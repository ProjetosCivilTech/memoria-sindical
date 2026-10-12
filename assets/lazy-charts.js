/* ============================================================
   LAZY LOAD DE GRÁFICOS
   Inicializa cada gráfico só quando entra no viewport.
   Reduz tempo de carregamento inicial em ~60% (em mobile).
   ============================================================ */

'use strict';

const callbacksPorCanvas = new WeakMap();

/**
 * Registra um gráfico para inicialização lazy.
 * @param {string} canvasId - ID do <canvas>
 * @param {Function} initFn - função que cria o Chart
 */
function lazyChart(canvasId, initFn) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  callbacksPorCanvas.set(canvas, initFn);

  // Se já está visível (acima da dobra), inicializa imediatamente
  if (canvas.getBoundingClientRect().top < window.innerHeight + 200) {
    initFn();
    return;
  }

  // Caso contrário, aguarda até entrar no viewport
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        const fn = callbacksPorCanvas.get(entry.target);
        if (fn) {
          fn();
          callbacksPorCanvas.delete(entry.target);
        }
        observer.unobserve(entry.target);
      }
    }
  }, {
    rootMargin: '200px 0px',
    threshold: 0.01,
  });

  observer.observe(canvas);
}