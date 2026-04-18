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
    const preview = root.querySelector('[data-td-role="preview"]');
    const previewImage = root.querySelector('[data-td-role="preview-image"]');
    const previewVideo = root.querySelector('[data-td-role="preview-video"]');
    const previewVideoSource = root.querySelector('[data-td-role="preview-video-source"]');
    const previewFile = root.querySelector('[data-td-role="preview-file"]');
    const fileNameText = root.querySelector('[data-td-role="filename"]');
    const submitButton = root.querySelector('[data-td-role="submit"]');
    const progressWrap = root.querySelector('[data-td-role="progress-wrap"]');
    const progress = root.querySelector('[data-td-role="progress"]');

    if (!fileInput || !dropzone || !submitButton) {
      return;
    }

    let previewUrl = null;
    let dragDepth = 0;

    const setDragState = (isDragging) => {
      dropzone.dataset.dragging = isDragging ? "true" : "false";
    };

    const revokePreviewUrl = () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        previewUrl = null;
      }
    };

    const updateSubmitState = () => {
      const hasFile = Boolean(fileInput.files && fileInput.files[0]);
      submitButton.disabled = !hasFile;
    };

    const renderPreview = (file) => {
      revokePreviewUrl();
      previewImage?.classList.add("hidden");
      previewVideo?.classList.add("hidden");
      previewFile?.classList.add("hidden");

      if (!file) {
        placeholder?.classList.remove("hidden");
        preview?.classList.add("hidden");
        if (fileNameText) {
          fileNameText.textContent = "";
        }
        updateSubmitState();
        return;
      }

      placeholder?.classList.add("hidden");
      preview?.classList.remove("hidden");
      if (fileNameText) {
        fileNameText.textContent = file.name;
      }
      previewUrl = URL.createObjectURL(file);

      if (file.type.startsWith("image/")) {
        if (previewImage) {
          previewImage.src = previewUrl;
          previewImage.classList.remove("hidden");
        }
      } else if (file.type.startsWith("video/")) {
        if (previewVideoSource) {
          previewVideoSource.src = previewUrl;
        }
        if (previewVideo) {
          previewVideo.load();
          previewVideo.classList.remove("hidden");
        }
      } else {
        previewFile?.classList.remove("hidden");
      }

      updateSubmitState();
    };

    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0] || null;
      renderPreview(file);
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
      renderPreview(droppedFile);
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
