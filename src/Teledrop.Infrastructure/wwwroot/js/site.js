(() => {
    const openDialog = (dialog) => {
        if (!dialog) return;
        if (dialog.open) dialog.close();
        dialog.showModal();
        // autofocus는 htmx가 교체한 조각에서도 초점을 옮기므로, 열 때만 쓰는 표시를 따로 둔다.
        dialog.querySelector("[data-dialog-focus]")?.focus();
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
            if (panel.open && panel.dataset.searchActive === "true") {
                panel.querySelector("input[type=search]").focus();
                return;
            }
            panel.open = !panel.open;
            search.setAttribute("aria-expanded", String(panel.open));
            if (panel.open) panel.querySelector("input[type=search]").focus();
        }
    });

    // 파일 세부 정보의 SHA-256 복사. 클립보드를 쓸 수 없으면 해시를 선택해 둔다.
    const restoreCopyHash = button => {
        tdI18n.setAttribute(button, "data-tooltip", "Hash.Copy");
        tdI18n.setAttribute(button, "aria-label", "Hash.Copy");
    };
    document.addEventListener("click", async event => {
        const button = event.target.closest("[data-copy-hash]");
        if (!button) return;
        const hash = button.parentElement.querySelector("[data-file-hash]");
        let key = "Copy.Done";
        try { await navigator.clipboard.writeText(hash.textContent.trim()); }
        catch { getSelection().selectAllChildren(hash); key = "Hash.Selected"; }
        tdI18n.setAttribute(button, "data-tooltip", key);
        tdI18n.setAttribute(button, "aria-label", key);
        clearTimeout(button.copyHashTimer);
        button.copyHashTimer = setTimeout(() => restoreCopyHash(button), 2000);
    });

    document.addEventListener("close", event => {
        if (!(event.target instanceof HTMLDialogElement) || document.querySelector("dialog:modal")) return;
        if (document.activeElement === document.body || event.target.contains(document.activeElement)) {
            const opener = document.querySelector(`[data-dialog-open="${CSS.escape(event.target.id)}"]`);
            // 메뉴 항목에서 연 대화상자는 닫힌 메뉴 대신 메뉴 버튼으로 돌아간다.
            const menu = opener?.closest("[role=menu]");
            (menu && !menu.classList.contains("is-open") ? document.querySelector(`[aria-controls="${CSS.escape(menu.id)}"]`) : opener)?.focus();
        }
    }, true);

    // 작업 메뉴: 버튼이 메뉴를 열고 닫으며, 열리면 항목으로 초점을 옮긴다.
    // hidden 속성 대신 클래스로 여닫아 JS 없는 화면의 noscript 스타일이 메뉴를 펼칠 수 있게 한다.
    const menuOf = toggle => document.getElementById(toggle.getAttribute("aria-controls"));
    const menuItems = menu => [...menu.querySelectorAll("[role^=menuitem]")];
    function openMenu(toggle, index) {
        if (toggle.disabled || toggle.getAttribute("aria-disabled") === "true") return;
        const menu = menuOf(toggle);
        const items = menuItems(menu);
        menu.classList.add("is-open");
        toggle.setAttribute("aria-expanded", "true");
        // 선택형 메뉴는 현재 값에서 시작한다.
        items.at(index ?? Math.max(0, items.findIndex(item => item.matches("[role=menuitemradio][aria-checked=true]"))))?.focus();
    }
    function closeMenu(toggle, focus = false) {
        menuOf(toggle).classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        if (focus) toggle.focus();
    }
    const openToggles = () => document.querySelectorAll("[data-menu-toggle][aria-expanded=true]");
    document.addEventListener("click", event => {
        const toggle = event.target.closest("[data-menu-toggle]");
        if (toggle) {
            if (toggle.getAttribute("aria-expanded") === "true") closeMenu(toggle, true);
            else openMenu(toggle);
        }
        for (const open of openToggles()) {
            if (open === toggle) continue;
            // 항목을 누르면 메뉴를 닫고 항목의 동작(대화상자 열기)이 이어진다.
            // 항목을 고르면 메뉴 버튼으로 돌아온다. 항목이 대화상자나 입력칸으로 초점을 옮겼다면 그대로 둔다.
            if (event.target.closest("[role^=menuitem]")) {
                const menu = menuOf(open);
                closeMenu(open, menu.contains(document.activeElement) || document.activeElement === document.body);
            }
            else if (!menuOf(open).contains(event.target)) closeMenu(open);
        }
    });
    document.addEventListener("keydown", event => {
        const toggle = event.target.closest?.("[data-menu-toggle]");
        if (toggle && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
            event.preventDefault();
            openMenu(toggle, event.key === "ArrowDown" ? 0 : -1);
            return;
        }
        const menu = event.target.closest?.("[role=menu]");
        if (!menu) return;
        const owner = document.querySelector(`[aria-controls="${CSS.escape(menu.id)}"]`);
        const items = menuItems(menu);
        const index = items.indexOf(event.target);
        const move = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: items.length - 1 }[event.key];
        if (move !== undefined) {
            event.preventDefault();
            items[(move + items.length) % items.length].focus();
        } else if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            closeMenu(owner, true);
        } else if (event.key === "Tab") {
            closeMenu(owner);
        }
    }, true);
    document.addEventListener("focusout", event => {
        for (const open of openToggles()) {
            const area = open.closest(".td-menu");
            if (area.contains(event.target) && event.relatedTarget && !area.contains(event.relatedTarget)) closeMenu(open);
        }
    });

    document.addEventListener("toggle", event => {
        if (event.target.id !== "drop-search") return;
        if (!event.target.open && event.target.dataset.searchActive === "true") {
            event.target.open = true;
            return;
        }
        document.querySelector("[data-toggle-search]")?.setAttribute("aria-expanded", String(event.target.open));
        if (!event.target.open && event.target.contains(document.activeElement)) {
            document.querySelector("[data-toggle-search]")?.focus();
        }
    }, true);

    // Pseudo-element tooltips stay hoverable; Escape dismisses them without
    // moving focus or closing their containing dialog.
    document.addEventListener("keydown", event => {
        if (event.key !== "Escape") return;
        const visible = document.querySelectorAll("[data-tooltip]:not([data-tooltip-dismissed], [aria-haspopup][aria-expanded=true]):is(:hover, :focus-visible)");
        if (!visible.length) return;
        for (const node of visible) node.setAttribute("data-tooltip-dismissed", "");
        event.preventDefault();
        event.stopPropagation();
    }, true);
    for (const name of ["pointerover", "focusin"]) {
        document.addEventListener(name, event => {
            const node = event.target.closest?.("[data-tooltip]");
            if (node && !node.contains(event.relatedTarget)) node.removeAttribute("data-tooltip-dismissed");
        });
    }

    for (const dialog of document.querySelectorAll("dialog[open]")) openDialog(dialog);
})();
