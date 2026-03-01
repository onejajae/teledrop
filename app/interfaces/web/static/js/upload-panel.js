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
    const keyInput = document.getElementById("upload-key");
    const keyHelper = document.getElementById("upload-key-helper");
    const hostPrefix = document.getElementById("upload-host-prefix");
    const usePassword = document.getElementById("upload-use-password");
    const passwordFields = document.getElementById("upload-password-fields");
    const passwordInput = document.getElementById("upload-password");
    const passwordConfirmInput = document.getElementById("upload-password-confirm");
    const passwordHelper = document.getElementById("upload-password-helper");
    const submitButton = document.getElementById("upload-submit");
    const progressWrap = document.getElementById("upload-progress");
    const progress = document.getElementById("progress");

    if (!fileInput || !dropzone || !submitButton) {
      return;
    }

    let previewUrl = null;
    let keyExists = false;
    let keyCheckTimer = null;
    let keyCheckSeq = 0;

    const revokePreviewUrl = () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        previewUrl = null;
      }
    };

    const updateSubmitState = () => {
      const hasFile = Boolean(fileInput.files && fileInput.files[0]);
      const passwordEnabled = Boolean(usePassword?.checked);
      const passwordMatched =
        !passwordEnabled ||
        (passwordInput.value.length > 0 && passwordInput.value === passwordConfirmInput.value);

      passwordHelper.classList.toggle("hidden", passwordMatched || !passwordEnabled);
      submitButton.disabled = !(hasFile && !keyExists && passwordMatched);
    };

    const setKeyHelper = (message, isError = false) => {
      keyHelper.textContent = message;
      keyHelper.classList.toggle("text-error", isError);
      keyHelper.classList.toggle("opacity-70", !isError);
    };

    const checkKeyAvailability = async (key) => {
      if (!key) {
        keyExists = false;
        setKeyHelper("업로드 후 공유 링크의 마지막 주소가 됩니다. 비워두면 자동 생성됩니다.");
        updateSubmitState();
        return;
      }

      const seq = ++keyCheckSeq;
      setKeyHelper("공유 링크 주소 확인 중...", false);
      try {
        const response = await fetch(`/api/drop/availability/${encodeURIComponent(key)}`, {
          method: "GET",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
          },
        });
        if (!response.ok) {
          throw new Error("slug check failed");
        }
        const body = await response.json();
        const available = Boolean(body.available);
        if (seq !== keyCheckSeq) {
          return;
        }
        keyExists = !available;
        if (!available) {
          setKeyHelper("이미 사용 중이거나 사용할 수 없는 URL 입니다.", true);
        } else {
          setKeyHelper("사용 가능한 공유 링크 주소입니다.");
        }
      } catch (_error) {
        if (seq !== keyCheckSeq) {
          return;
        }
        keyExists = false;
        setKeyHelper("공유 링크 주소 확인에 실패했습니다. 업로드 시 다시 확인됩니다.", true);
      }
      updateSubmitState();
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

    hostPrefix.textContent = `${window.location.host}/`;
    hostPrefix.title = hostPrefix.textContent;

    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0] || null;
      renderPreview(file);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("border-primary", "bg-base-200");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.remove("border-primary", "bg-base-200");
      });
    });

    dropzone.addEventListener("drop", (event) => {
      const droppedFile = event.dataTransfer?.files?.[0];
      if (!droppedFile) {
        return;
      }
      const transfer = new DataTransfer();
      transfer.items.add(droppedFile);
      fileInput.files = transfer.files;
      renderPreview(droppedFile);
    });

    keyInput.addEventListener("input", () => {
      const key = keyInput.value.trim();
      if (keyCheckTimer) {
        clearTimeout(keyCheckTimer);
      }
      keyCheckTimer = setTimeout(() => {
        checkKeyAvailability(key);
      }, 250);
    });

    usePassword.addEventListener("change", () => {
      passwordFields.classList.toggle("hidden", !usePassword.checked);
      if (!usePassword.checked) {
        passwordInput.value = "";
        passwordConfirmInput.value = "";
      }
      updateSubmitState();
    });

    passwordInput.addEventListener("input", updateSubmitState);
    passwordConfirmInput.addEventListener("input", updateSubmitState);

    form.addEventListener("submit", (event) => {
      if (submitButton.disabled) {
        event.preventDefault();
        return;
      }
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
