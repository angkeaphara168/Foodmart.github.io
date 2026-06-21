(function () {
  const STORAGE_KEY = 'foodmart_theme';
  const root = document.documentElement;
  const mediaQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function normalizeTheme(theme) {
    return theme === 'dark' ? 'dark' : 'light';
  }

  function readStoredTheme() {
    try {
      const theme = window.localStorage.getItem(STORAGE_KEY);
      return theme === 'dark' || theme === 'light' ? theme : null;
    } catch (error) {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (error) {
      // Local storage can be unavailable in a locked-down browser context.
    }
  }

  function getPreferredTheme() {
    const storedTheme = readStoredTheme();
    if (storedTheme) return storedTheme;
    return mediaQuery && mediaQuery.matches ? 'dark' : 'light';
  }

  function ensureControlMarkup(button) {
    if (button.querySelector('[data-theme-label]')) return;

    button.innerHTML = [
      '<i class="bx theme-toggle-icon" data-theme-icon aria-hidden="true"></i>',
      '<span data-theme-label></span>'
    ].join('');
  }

  function updateControls(theme) {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    const label = nextTheme === 'dark' ? 'Dark' : 'Light';

    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      ensureControlMarkup(button);
      button.setAttribute('aria-label', `Switch to ${nextTheme} theme`);
      button.setAttribute('title', `Switch to ${nextTheme} theme`);
      button.dataset.nextTheme = nextTheme;

      const labelNode = button.querySelector('[data-theme-label]');
      if (labelNode) labelNode.textContent = label;

      const iconNode = button.querySelector('[data-theme-icon]');
      if (iconNode) {
        iconNode.className = `bx theme-toggle-icon ${nextTheme === 'dark' ? 'bx-moon' : 'bx-sun'}`;
      }
    });
  }

  function setTheme(theme, shouldSave) {
    const nextTheme = normalizeTheme(theme);
    root.dataset.theme = nextTheme;
    root.style.colorScheme = nextTheme;

    if (shouldSave) saveTheme(nextTheme);
    updateControls(nextTheme);

    return nextTheme;
  }

  function toggleTheme() {
    const activeTheme = normalizeTheme(root.dataset.theme);
    return setTheme(activeTheme === 'dark' ? 'light' : 'dark', true);
  }

  function ensureToggleButton() {
    if (document.querySelector('[data-theme-toggle]')) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'theme-toggle';
    button.dataset.themeToggle = 'true';
    document.body.appendChild(button);
  }

  function initThemeToggle() {
    ensureToggleButton();
    updateControls(normalizeTheme(root.dataset.theme));

    document.addEventListener('click', event => {
      const toggle = event.target.closest('[data-theme-toggle]');
      if (!toggle) return;

      event.preventDefault();
      toggleTheme();
    });

    if (mediaQuery && mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', event => {
        if (!readStoredTheme()) setTheme(event.matches ? 'dark' : 'light', false);
      });
    }
  }

  window.FoodMartTheme = {
    getTheme: () => normalizeTheme(root.dataset.theme),
    setTheme: theme => setTheme(theme, true),
    toggleTheme
  };

  setTheme(getPreferredTheme(), false);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeToggle);
  } else {
    initThemeToggle();
  }
}());
