document.addEventListener('DOMContentLoaded', () => {
  const config = window.perfilThemeConfig || {};
  const perfilDataUrl = config.perfilDataUrl;
  const updateThemeUrl = config.updateThemeUrl;

  const form = document.getElementById('theme-form');
  const msgBox = document.getElementById('theme-msg');
  const themeSelect = document.getElementById('theme');

  const showMsg = (message, type = 'info') => {
    msgBox.textContent = message;
    msgBox.className = `msg ${type}`;
  };

  const applyThemeLocal = (theme) => {
    const validTheme = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', validTheme);
    localStorage.setItem('theme', validTheme);
  };

  const loadCurrentTheme = async () => {
    try {
      const response = await fetch(perfilDataUrl, { method: 'GET' });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'No se pudo cargar el tema actual.');
      }
      const theme = (data.user?.theme || localStorage.getItem('theme') || 'light').toLowerCase();
      themeSelect.value = theme === 'dark' ? 'dark' : 'light';
      applyThemeLocal(themeSelect.value);
    } catch (error) {
      showMsg(error.message || 'Error cargando tema.', 'error');
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const theme = (themeSelect.value || 'light').toLowerCase();

    try {
      const response = await fetch(updateThemeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'No se pudo guardar el tema.');
      }
      applyThemeLocal(theme);
      showMsg(data.msg || 'Tema actualizado correctamente.', 'success');
    } catch (error) {
      showMsg(error.message || 'Error guardando tema.', 'error');
    }
  });

  loadCurrentTheme();
});
