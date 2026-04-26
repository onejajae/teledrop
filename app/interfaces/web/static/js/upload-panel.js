(() => {
  const initUploadPanel = (root) => {
    if (!root || root.dataset.initialized === "true") {
      return;
    }
    root.dataset.initialized = "true";

    const form = root;
    const fileInput = root.querySelector('[data-td-role="file-input"]');
    const dropzone = root.querySelector('[data-td-role="dropzone"]');
    const placeholder = root.querySelector('[data-td-role="placeholder"]');
    const selection = root.querySelector('[data-td-role="selection"]');
    const fileNameText = root.querySelector('[data-td-role="filename"]');
    const submitButton = root.querySelector('[data-td-role="submit"]');
    const progressWrap = root.querySelector('[data-td-role="progress-wrap"]');
    const progress = root.querySelector('[data-td-role="progress"]');

    if (!fileInput || !dropzone || !submitButton) {
      return;
    }

    let dragDepth = 0;

    const setDragState = (isDragging) => {
      dropzone.dataset.dragging = isDragging ? "true" : "false";
    };

    const updateSubmitState = () => {
      const hasFile = Boolean(fileInput.files && fileInput.files[0]);
      submitButton.disabled = !hasFile;
    };

    const renderSelection = (file) => {
      if (!file) {
        placeholder?.classList.remove("hidden");
        selection?.classList.add("hidden");
        if (fileNameText) {
          fileNameText.textContent = "";
        }
        updateSubmitState();
        return;
      }

      placeholder?.classList.add("hidden");
      selection?.classList.remove("hidden");
      if (fileNameText) {
        fileNameText.textContent = file.name;
      }

      updateSubmitState();
    };

    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0] || null;
      renderSelection(file);
    });

    dropzone.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      event.preventDefault();
      fileInput.click();
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        if (eventName === "dragenter") {
          dragDepth += 1;
        }
        setDragState(true);
      });
    });

    dropzone.addEventListener("dragleave", (event) => {
      event.preventDefault();
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) {
        setDragState(false);
      }
    });

    dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      dragDepth = 0;
      setDragState(false);

      const droppedFile = event.dataTransfer?.files?.[0];
      if (!droppedFile) {
        return;
      }
      const transfer = new DataTransfer();
      transfer.items.add(droppedFile);
      fileInput.files = transfer.files;
      renderSelection(droppedFile);
    });

    form.addEventListener("submit", (event) => {
      if (submitButton.disabled) {
        event.preventDefault();
        return;
      }
      setDragState(false);
      progressWrap?.classList.remove("hidden");
      if (progress) {
        progress.value = 0;
      }
    });

    if (typeof htmx !== "undefined") {
      htmx.on(form, "htmx:xhr:progress", (event) => {
        progressWrap?.classList.remove("hidden");
        progress?.setAttribute("value", (event.detail.loaded / event.detail.total) * 100);
      });
    }

    setDragState(false);
    updateSubmitState();
  };

  const initUploadPanels = () => {
    document
      .querySelectorAll('[data-td-controller="upload-panel"]')
      .forEach(initUploadPanel);
  };

  document.addEventListener("DOMContentLoaded", initUploadPanels);
  document.body.addEventListener("htmx:afterSwap", initUploadPanels);
})();
