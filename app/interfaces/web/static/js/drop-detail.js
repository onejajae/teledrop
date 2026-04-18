(() => {
  const toggleDialog = (trigger) => {
    const action = trigger.dataset.tdAction;
    if (action !== "open-dialog" && action !== "close-dialog") {
      return false;
    }

    const dialogId = trigger.dataset.tdDialogId;
    const dialog = dialogId ? document.getElementById(dialogId) : null;
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

  const copyPreviewUrl = (button) => {
    const relativeUrl = button.dataset.copyUrl;
    if (!relativeUrl) {
      return;
    }

    const label = button.querySelector(".detail-copy-label");
    const original = label?.textContent ?? "";
    const originalAriaLabel = button.getAttribute("aria-label") ?? "";
    const originalTitle = button.getAttribute("title") ?? "";
    navigator.clipboard.writeText(`${window.location.origin}${relativeUrl}`).then(() => {
      if (label) {
        label.textContent = "복사됨";
      }
      button.setAttribute("aria-label", "링크 복사됨");
      button.setAttribute("title", "링크 복사됨");
      window.setTimeout(() => {
        if (label) {
          label.textContent = original;
        }
        if (originalAriaLabel) {
          button.setAttribute("aria-label", originalAriaLabel);
        }
        if (originalTitle) {
          button.setAttribute("title", originalTitle);
        }
      }, 1200);
    });
  };

  const initDetailPasswordForm = () => {
    const form = document.getElementById("detail-password-form");
    if (!form || form.dataset.initialized === "true") {
      return;
    }
    form.dataset.initialized = "true";

    const password = document.getElementById("detail-password-new");
    const confirm = document.getElementById("detail-password-confirm");
    const mismatch = document.getElementById("detail-password-mismatch");
    const submit = document.getElementById("detail-password-submit");

    if (!password || !confirm || !mismatch || !submit) {
      return;
    }

    const sync = () => {
      const isMatch = password.value === confirm.value;
      const showMismatch = confirm.value.length > 0 && !isMatch;
      mismatch.classList.toggle("hidden", !showMismatch);
      submit.disabled = !isMatch;
    };

    password.addEventListener("input", sync);
    confirm.addEventListener("input", sync);
    sync();
  };

  document.addEventListener("DOMContentLoaded", initDetailPasswordForm);
  document.body.addEventListener("htmx:afterSwap", initDetailPasswordForm);
  document.addEventListener("click", (event) => {
    const tdActionTrigger = event.target.closest("[data-td-action]");
    if (tdActionTrigger && toggleDialog(tdActionTrigger)) {
      event.preventDefault();
      return;
    }

    const button = event.target.closest(".detail-copy-link");
    if (!button) {
      return;
    }
    copyPreviewUrl(button);
  });
})();
