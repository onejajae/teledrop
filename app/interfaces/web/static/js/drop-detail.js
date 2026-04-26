(() => {
  const getPasswordFormParts = (form) => {
    if (!form) {
      return null;
    }

    const password = form.querySelector('[data-td-role="password-input"]');
    const confirm = form.querySelector('[data-td-role="password-confirm"]');
    const mismatch = form.querySelector('[data-td-role="password-mismatch"]');
    const submit = form.querySelector('[data-td-role="password-submit"]');

    if (!password || !confirm || !mismatch || !submit) {
      return null;
    }

    return { password, confirm, mismatch, submit };
  };

  const syncPasswordForm = (form) => {
    const parts = getPasswordFormParts(form);
    if (!parts) {
      return;
    }

    const { password, confirm, mismatch, submit } = parts;
    const isMatch = password.value === confirm.value;
    const showMismatch = confirm.value.length > 0 && !isMatch;
    mismatch.classList.toggle("hidden", !showMismatch);
    mismatch.setAttribute("aria-hidden", showMismatch ? "false" : "true");
    confirm.setAttribute("aria-invalid", showMismatch ? "true" : "false");
    submit.disabled = showMismatch;
  };

  const initPasswordForm = (form) => {
    if (!form || form.dataset.initialized === "true") {
      return;
    }
    const parts = getPasswordFormParts(form);
    if (!parts) {
      return;
    }
    form.dataset.initialized = "true";

    const { password, confirm, mismatch } = parts;
    if (mismatch.id) {
      const describedBy = confirm.getAttribute("aria-describedby") || "";
      const describedByIds = describedBy.split(/\s+/).filter(Boolean);
      if (!describedByIds.includes(mismatch.id)) {
        describedByIds.push(mismatch.id);
        confirm.setAttribute("aria-describedby", describedByIds.join(" "));
      }
    }

    const handleSync = () => syncPasswordForm(form);
    password.addEventListener("input", handleSync);
    password.addEventListener("change", handleSync);
    confirm.addEventListener("input", handleSync);
    confirm.addEventListener("change", handleSync);
    handleSync();
  };

  const initDetailPanel = (root) => {
    if (!root) {
      return;
    }

    root.querySelectorAll('[data-td-role="password-form"]').forEach(initPasswordForm);
  };

  const initDetailPanels = () => {
    document
      .querySelectorAll('[data-td-controller="drop-detail"]')
      .forEach(initDetailPanel);
  };

  document.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const form = target.closest('[data-td-role="password-form"]');
    if (!form) {
      return;
    }

    syncPasswordForm(form);
  });

  document.addEventListener("DOMContentLoaded", initDetailPanels);
  document.body.addEventListener("htmx:afterSwap", initDetailPanels);
})();
