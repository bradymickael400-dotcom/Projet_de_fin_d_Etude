(function () {
  const baseUrl = '/static/js/';
  const files = [
    'core-state.js',
    'auth-qr.js',
    'data-pages.js',
    'ui-navigation.js',
    'black-boxes.js',
    'direct-bridge.js'
  ];

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `${baseUrl}${src}?v=20261028-regulatory-history-v1`;
      script.async = false;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Impossible de charger ${src}`));
      document.head.appendChild(script);
    });
  }

  (async function () {
    try {
      for (const file of files) {
        await loadScript(file);
      }
      if (typeof initializeQrLoginFlow === 'function') initializeQrLoginFlow();
    } catch (error) {
      console.error('Erreur de chargement des modules ARGOS:', error);
    }
  })();
})();
