// Macacolandia site · interações leves, sem dependências e sem TypeScript.
(() => {
  const downloadLinks = document.querySelectorAll('a[href*="releases/latest"]');
  downloadLinks.forEach((link) => {
    link.addEventListener('click', () => {
      link.dataset.originalLabel = link.textContent;
      link.textContent = 'Abrindo releases…';
      window.setTimeout(() => { link.textContent = link.dataset.originalLabel || 'Baixar versão mais recente ↗'; }, 1400);
    });
  });
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();
