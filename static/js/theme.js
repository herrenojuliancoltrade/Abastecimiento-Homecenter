(function () {
  function normalizeTheme(theme) {
    return theme === 'dark' ? 'dark' : 'light';
  }

  function setTheme(theme) {
    const validTheme = normalizeTheme(theme);
    document.documentElement.setAttribute('data-theme', validTheme);
    try {
      localStorage.setItem('theme', validTheme);
    } catch (e) {
      // ignore storage errors
    }
    return validTheme;
  }

  window.applyTheme = setTheme;

  try {
    const stored = localStorage.getItem('theme');
    setTheme(stored || 'light');
  } catch (e) {
    setTheme('light');
  }
})();
