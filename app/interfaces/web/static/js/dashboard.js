(() => {
  if (window.__teledropDashboardInitialized) {
    return;
  }
  window.__teledropDashboardInitialized = true;

  // DOM contract: selectable drop cards expose data-drop-key/data-select-key.
  const itemSelector = "[data-drop-key]";
  const hasOwn = Object.prototype.hasOwnProperty;

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

    const trigger = event.target.closest("[data-select-key]");
    if (!trigger) {
      return;
    }
    setSelectedKey(trigger.dataset.selectKey || null);
  });

  document.body.addEventListener("htmx:afterSwap", syncSelectedKey);
  document.body.addEventListener("drop-list-refresh", refreshDropPanel);

  window.addEventListener("popstate", syncSelectedKey);

  syncSelectedKey();
})();
