(() => {
  if (window.__teledropThemeInitialized) {
    return;
  }
  window.__teledropThemeInitialized = true;

  const root = document.documentElement;

  const getThemeConfig = () => ({
    lightThemeColor: root.dataset.themeColorLight,
    darkThemeColor: root.dataset.themeColorDark,
    lightSurface: root.dataset.themeSurfaceLight,
    darkSurface: root.dataset.themeSurfaceDark,
  });

  const syncThemeSurface = () => {
    const { lightSurface, darkSurface } = getThemeConfig();
    if (lightSurface) {
      root.style.setProperty("--td-theme-surface-light", lightSurface);
    }
    if (darkSurface) {
      root.style.setProperty("--td-theme-surface-dark", darkSurface);
    }
  };

  const resolveThemeColor = (theme, { lightThemeColor, darkThemeColor }) => {
    if (theme === "dark") {
      return darkThemeColor || lightThemeColor;
    }
    return lightThemeColor || darkThemeColor;
  };

  const setDocumentTheme = (theme) => {
    const themeConfig = getThemeConfig();
    syncThemeSurface();
    root.setAttribute("data-theme", theme);
    root.style.colorScheme = theme === "dark" ? "dark" : "light";
    const themeColorMeta = document.querySelector('meta[name="theme-color"]');
    const themeColor = resolveThemeColor(theme, themeConfig);
    if (themeColorMeta && themeColor) {
      themeColorMeta.setAttribute("content", themeColor);
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
      const isDark = root.getAttribute("data-theme") === "dark";
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
    const currentTheme = root.getAttribute("data-theme");
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    setDocumentTheme(nextTheme);
    localStorage.setItem("color-theme", nextTheme);
    syncThemeToggle();
  });

  window.__teledropSetDocumentTheme = setDocumentTheme;

  syncThemeSurface();
  applyThemePreference();
  syncThemeToggle();
})();
