(() => {
  if (window.__teledropDashboardInitialized) {
    return;
  }
  window.__teledropDashboardInitialized = true;

  // DOM contract: selectable drop cards expose data-drop-key/data-select-key.
  const itemSelector = "[data-drop-key]";
  const hasOwn = Object.prototype.hasOwnProperty;
  const interactiveSelector = "a, button, input, select, textarea, label, form, summary";
  const LIGHT_THEME_COLOR = "#0ea5e9";
  const DARK_THEME_COLOR = "#1d232a";
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

  const selectedKeyFromUrl = () => {
    const params = new URLSearchParams(window.location.search);
    const slugFromQuery = params.get("slug");
    if (slugFromQuery) {
      return slugFromQuery;
    }

    const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
    if (!path) {
      return null;
    }
    return decodeURIComponent(path.split("/")[0]);
  };

  const setSelectedKey = (selectedKey) => {
    document.querySelectorAll(itemSelector).forEach((item) => {
      if (selectedKey && item.dataset.dropKey === selectedKey) {
        item.classList.add("is-selected");
      } else {
        item.classList.remove("is-selected");
      }
    });
  };

  const openDropDetailCard = (card) => {
    const slug = card?.dataset.dropKey;
    if (!slug || !document.querySelector("#main-panel")) {
      return;
    }

    htmx.ajax("GET", "/drop-detail", {
      values: { slug },
      target: "#main-panel",
      swap: "innerHTML",
    });

    const previewUrl = card.dataset.previewUrl;
    if (previewUrl) {
      history.pushState(null, "", previewUrl);
    }
  };

  const currentDropPanelValues = () => {
    const values = {};
    const sortBy = document.querySelector("#drop-sortby")?.value;
    const orderBy = document.querySelector("#drop-orderby")?.value;
    if (sortBy) {
      values.sortby = sortBy;
    }
    if (orderBy) {
      values.orderby = orderBy;
    }
    return values;
  };

  const refreshDropPanel = () => {
    if (!document.querySelector("#drop-panel")) {
      return;
    }
    htmx.ajax("GET", "/drop-panel", {
      target: "#drop-panel",
      swap: "innerHTML",
      values: currentDropPanelValues(),
    });
  };

  const syncSelectedKey = () => {
    setSelectedKey(selectedKeyFromUrl());
  };

  window.__teledropSetSelectedKey = setSelectedKey;
  window.__teledropCurrentListValues = currentDropPanelValues;
  window.__teledropRefreshDropPanel = refreshDropPanel;
  window.__teledropRefreshPanels = (options = {}) => {
    const detailPanel = document.querySelector("[data-detail-key]");
    const detailKey = hasOwn.call(options, "slug")
      ? options.slug
      : detailPanel?.dataset.detailKey;
    const detailPassword = hasOwn.call(options, "password")
      ? options.password
      : detailPanel?.dataset.detailPassword;

    if (detailKey && document.querySelector("#main-panel")) {
      const values = { slug: detailKey };
      if (detailPassword) {
        values.password = detailPassword;
      }
      htmx.ajax("GET", "/drop-detail", {
        target: "#main-panel",
        swap: "innerHTML",
        values,
      });
    }

    refreshDropPanel();
  };

  document.addEventListener("click", (event) => {
    const tdActionTrigger = event.target.closest("[data-td-action]");
    if (tdActionTrigger) {
      const action = tdActionTrigger.dataset.tdAction;
      if (action === "drop-panel-refresh") {
        event.preventDefault();
        tdActionTrigger
          .closest("section")
          ?.querySelector('form[action="/drop-panel"]')
          ?.requestSubmit();
        return;
      }

      if (action === "drop-sort-toggle") {
        event.preventDefault();
        const input = tdActionTrigger.form?.querySelector("#drop-orderby");
        if (input) {
          input.value = input.value === "desc" ? "asc" : "desc";
          tdActionTrigger.form.requestSubmit();
        }
        return;
      }

      if (action === "open-dialog" || action === "close-dialog") {
        event.preventDefault();
        const dialogId = tdActionTrigger.dataset.tdDialogId;
        const dialog = dialogId ? document.getElementById(dialogId) : null;
        if (!dialog) {
          return;
        }
        if (action === "open-dialog" && typeof dialog.showModal === "function") {
          dialog.showModal();
          return;
        }
        if (action === "close-dialog" && typeof dialog.close === "function") {
          dialog.close();
        }
        return;
      }
    }

    const card = event.target.closest("[data-drop-key][data-preview-url]");
    if (card && event.target.closest(interactiveSelector)) {
      return;
    }

    const trigger = event.target.closest("[data-select-key]");
    if (!trigger) {
      return;
    }
    setSelectedKey(trigger.dataset.selectKey || null);

    if (!card) {
      return;
    }
    openDropDetailCard(card);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const card = event.target.closest?.("[data-drop-key][data-preview-url]");
    if (!card) {
      return;
    }
    event.preventDefault();
    setSelectedKey(card.dataset.selectKey || null);
    openDropDetailCard(card);
  });

  document.addEventListener("submit", (event) => {
    const trigger = event.target.closest("form[data-select-key]");
    if (!trigger) {
      return;
    }
    setSelectedKey(trigger.dataset.selectKey || null);
  });

  document.body.addEventListener("htmx:afterSwap", syncSelectedKey);
  document.body.addEventListener("drop-list-refresh", refreshDropPanel);

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

  window.addEventListener("popstate", syncSelectedKey);

  applyThemePreference();
  syncThemeToggle();
  syncSelectedKey();
})();
