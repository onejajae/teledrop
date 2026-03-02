(() => {
  if (window.__teledropThemeInitialized) {
    return;
  }
  window.__teledropThemeInitialized = true;

  const LIGHT_THEME_COLOR = "#0ea5e9";
  const DARK_THEME_COLOR = "#1f2937";

  const setDocumentTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme === "dark" ? "dark" : "light";
    const themeColorMeta = document.querySelector('meta[name="theme-color"]');
    if (themeColorMeta) {
      themeColorMeta.setAttribute("content", theme === "dark" ? DARK_THEME_COLOR : LIGHT_THEME_COLOR);
    }
  };

  const applyThemePreference = () => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const stored = localStorage.getItem("color-theme");
    const theme = stored || (prefersDark ? "dark" : "light");
    setDocumentTheme(theme);
  };

  // DOM contract: header renders #theme-toggle as button[aria-pressed].
  const syncThemeToggle = () => {
    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      toggle.classList.toggle("swap-active", isDark);
      toggle.setAttribute("aria-pressed", String(isDark));
    }
  };

  document.body.addEventListener("htmx:afterSwap", syncThemeToggle);
  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("#theme-toggle");
    if (!toggle) {
      return;
    }
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    setDocumentTheme(nextTheme);
    localStorage.setItem("color-theme", nextTheme);
    syncThemeToggle();
  });

  window.__teledropSetDocumentTheme = setDocumentTheme;

  applyThemePreference();
  syncThemeToggle();
})();
