(() => {
    const openDialog = (dialog) => {
        if (!dialog) return;
        if (dialog.open) dialog.close();
        dialog.showModal();
    };

    document.addEventListener("click", (event) => {
        const open = event.target.closest("[data-dialog-open]");
        if (open) openDialog(document.getElementById(open.dataset.dialogOpen));
        const close = event.target.closest("[data-dialog-close]");
        if (close) close.closest("dialog").close();
        if (event.target instanceof HTMLDialogElement) {
            const bounds = event.target.getBoundingClientRect();
            if (event.clientX < bounds.left || event.clientX > bounds.right
                || event.clientY < bounds.top || event.clientY > bounds.bottom) event.target.close();
        }
        const search = event.target.closest("[data-toggle-search]");
        if (search) {
            const panel = document.getElementById(search.getAttribute("aria-controls"));
            panel.open = !panel.open;
            search.setAttribute("aria-expanded", String(panel.open));
            if (panel.open) panel.querySelector("input[type=search]").focus();
        }
    });

    document.addEventListener("change", (event) => {
        if (event.target.matches("[data-auto-submit]")) {
            // Submit the selected sort without also toggling the direction button.
            const form = event.target.form;
            const direction = form.querySelector("button[name=direction]");
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "direction";
            input.value = direction.value === "asc" ? "desc" : "asc";
            form.append(input);
            form.requestSubmit();
            input.remove();
        }
    });

    const updateTimes = () => {
        for (const time of document.querySelectorAll("time[data-relative-time]")) {
            const seconds = Math.max(0, (Date.now() - Date.parse(time.dateTime)) / 1000);
            time.textContent = seconds < 45 ? "몇 초 전"
                : seconds < 90 ? "1분 전"
                : seconds < 2700 ? `${Math.round(seconds / 60)}분 전`
                : seconds < 5400 ? "한 시간 전"
                : seconds < 79200 ? `${Math.round(seconds / 3600)}시간 전`
                : seconds < 129600 ? "하루 전"
                : seconds < 2246400 ? `${Math.round(seconds / 86400)}일 전`
                : seconds < 3888000 ? "한 달 전"
                : seconds < 27648000 ? `${Math.round(seconds / 2592000)}달 전`
                : `${Math.round(seconds / 31536000)}년 전`;
        }
        for (const time of document.querySelectorAll("time[data-local-date]")) {
            const date = new Date(time.dateTime);
            const pad = value => String(value).padStart(2, "0");
            time.textContent = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} (${["일", "월", "화", "수", "목", "금", "토"][date.getDay()]}) ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
        }
    };
    for (const dialog of document.querySelectorAll("dialog[open]")) openDialog(dialog);
    updateTimes();
    document.addEventListener("htmx:afterSwap", updateTimes);
})();
