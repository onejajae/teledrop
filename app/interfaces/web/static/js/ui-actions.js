(() => {
  const findDialog = (dialogName) => {
    if (!dialogName) {
      return null;
    }
    return Array.from(document.querySelectorAll("dialog[data-td-dialog]")).find(
      (dialog) => dialog.dataset.tdDialog === dialogName,
    ) || null;
  };

  const toggleDialog = (trigger) => {
    const action = trigger.dataset.tdAction;
    if (action !== "open-dialog" && action !== "close-dialog") {
      return false;
    }

    const dialogName = trigger.dataset.tdDialog;
    const dialog = findDialog(dialogName);
    if (!dialog) {
      return true;
    }

    if (action === "open-dialog" && typeof dialog.showModal === "function") {
      dialog.showModal();
      return true;
    }

    if (action === "close-dialog" && typeof dialog.close === "function") {
      dialog.close();
    }
    return true;
  };

  const isHtmlResponse = (xhr) => {
    const contentType = xhr.getResponseHeader("content-type") || "";
    return contentType.toLowerCase().includes("text/html");
  };

  const allowClientErrorHtmlSwap = (event) => {
    const xhr = event.detail?.xhr;
    if (!xhr || xhr.status < 400 || xhr.status >= 500) {
      return;
    }

    if (xhr.getResponseHeader("HX-Redirect") || !isHtmlResponse(xhr)) {
      return;
    }

    event.detail.shouldSwap = true;
    event.detail.isError = false;
  };

  const copyShareUrl = (trigger) => {
    const relativeUrl = trigger.dataset.tdCopyUrl;
    if (!relativeUrl || !navigator.clipboard) {
      return;
    }

    const label = trigger.querySelector('[data-td-role="copy-label"]');
    const original = label?.textContent ?? "";
    const originalAriaLabel = trigger.getAttribute("aria-label") ?? "";
    const originalTitle = trigger.getAttribute("title") ?? "";

    navigator.clipboard.writeText(`${window.location.origin}${relativeUrl}`).then(() => {
      if (label) {
        label.textContent = "복사됨";
      }
      trigger.setAttribute("aria-label", "링크 복사됨");
      trigger.setAttribute("title", "링크 복사됨");
      window.setTimeout(() => {
        if (label) {
          label.textContent = original;
        }
        if (originalAriaLabel) {
          trigger.setAttribute("aria-label", originalAriaLabel);
        }
        if (originalTitle) {
          trigger.setAttribute("title", originalTitle);
        }
      }, 1200);
    });
  };

  const toggleSort = (trigger) => {
    const targetId = trigger.dataset.tdSortTarget;
    const form = trigger.closest("form");
    const orderInput = targetId ? document.getElementById(targetId) : null;
    if (!form || !orderInput) {
      return;
    }

    orderInput.value = orderInput.value === "asc" ? "desc" : "asc";
    form.requestSubmit();
  };

  const submitClosestForm = (trigger) => {
    const form = trigger.form || trigger.closest("form");
    if (!form) {
      return;
    }
    form.requestSubmit();
  };

  const maybeConfirmSubmit = (form) => {
    if (form.dataset.tdAction !== "confirm-submit") {
      return true;
    }

    const message = form.dataset.tdConfirm || "계속하시겠습니까?";
    return window.confirm(message);
  };

  const syncTimezoneOffsets = () => {
    const offsetMinutes = String(new Date().getTimezoneOffset());
    document.querySelectorAll('[data-td-role="timezone-offset"]').forEach((input) => {
      if (input instanceof HTMLInputElement) {
        input.value = offsetMinutes;
      }
    });
  };

  syncTimezoneOffsets();
  document.body.addEventListener("htmx:beforeSwap", allowClientErrorHtmlSwap);

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-td-action]");
    if (!trigger) {
      return;
    }

    if (toggleDialog(trigger)) {
      event.preventDefault();
      return;
    }

    if (trigger.dataset.tdAction === "copy-link") {
      event.preventDefault();
      copyShareUrl(trigger);
      return;
    }

    if (trigger.dataset.tdAction === "toggle-sort") {
      event.preventDefault();
      toggleSort(trigger);
    }
  });

  document.addEventListener("change", (event) => {
    const trigger = event.target.closest('[data-td-action="submit-form"]');
    if (!trigger) {
      return;
    }

    submitClosestForm(trigger);
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }

    if (!maybeConfirmSubmit(form)) {
      event.preventDefault();
    }
  });
})();
