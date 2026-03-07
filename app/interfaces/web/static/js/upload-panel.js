(() => {
  const initUploadPanel = () => {
    const form = document.getElementById("upload-form");
    if (!form || form.dataset.initialized === "true") {
      return;
    }
    form.dataset.initialized = "true";

    const fileInput = document.getElementById("upload-file");
    const dropzone = document.getElementById("upload-dropzone");
    const placeholder = document.getElementById("upload-drop-placeholder");
    const preview = document.getElementById("upload-preview");
    const previewImage = document.getElementById("upload-preview-image");
    const previewVideo = document.getElementById("upload-preview-video");
    const previewVideoSource = document.getElementById("upload-preview-video-source");
    const previewFile = document.getElementById("upload-preview-file");
    const fileNameText = document.getElementById("upload-filename");
    const submitButton = document.getElementById("upload-submit");
    const progressWrap = document.getElementById("upload-progress");
    const progress = document.getElementById("progress");

    if (!fileInput || !dropzone || !submitButton) {
      return;
    }

    let previewUrl = null;
    let dragDepth = 0;

    const setDragState = (isDragging) => {
      dropzone.classList.toggle("border-primary", isDragging);
      dropzone.classList.toggle("ring", isDragging);
      dropzone.classList.toggle("ring-primary/15", isDragging);
      dropzone.classList.toggle("bg-base-200", isDragging);
      dropzone.classList.toggle("border-base-300", !isDragging);
      dropzone.classList.toggle("bg-base-100", !isDragging);
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
      previewImage.classList.add("hidden");
      previewVideo.classList.add("hidden");
      previewFile.classList.add("hidden");

      if (!file) {
        placeholder.classList.remove("hidden");
        preview.classList.add("hidden");
        fileNameText.textContent = "";
        updateSubmitState();
        return;
      }

      placeholder.classList.add("hidden");
      preview.classList.remove("hidden");
      fileNameText.textContent = file.name;
      previewUrl = URL.createObjectURL(file);

      if (file.type.startsWith("image/")) {
        previewImage.src = previewUrl;
        previewImage.classList.remove("hidden");
      } else if (file.type.startsWith("video/")) {
        previewVideoSource.src = previewUrl;
        previewVideo.load();
        previewVideo.classList.remove("hidden");
      } else {
        previewFile.classList.remove("hidden");
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
      progressWrap.classList.remove("hidden");
      progress.value = 0;
    });

    htmx.on(form, "htmx:xhr:progress", (event) => {
      progressWrap.classList.remove("hidden");
      progress.setAttribute("value", (event.detail.loaded / event.detail.total) * 100);
    });

    updateSubmitState();
  };

  document.addEventListener("DOMContentLoaded", initUploadPanel);
  document.body.addEventListener("htmx:afterSwap", initUploadPanel);
})();
