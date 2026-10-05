(() => {
    const detail = document.getElementById("drop-detail");
    const active = new Map();
    const requests = new WeakMap();
    let epoch = 0;
    let dirty = false;
    let sharedNeeded = false;
    let sharedReading = false;
    let favoriteNeeded = false;
    let favoriteReading = false;
    let retryFavorite = null;
    let optimisticFavorite = null;
    let navigation = null;
    let leaving = false;
    const dialogs = { access: "password-dialog", slug: "url-dialog", delete: "delete-dialog" };
    const isNavigation = group => group === "slug" || group === "delete";
    const notify = name => document.body.dispatchEvent(new CustomEvent(name, { bubbles: true }));

    function message(group, key = "") {
        for (const node of document.querySelectorAll(`[data-operation-error="${group}"]`)) {
            tdI18n.setText(node, key);
            node.hidden = !key;
        }
    }
    function recovery(show) {
        const node = document.getElementById("favorite-recovery");
        if (node) node.hidden = !show;
    }
    function showFavorite(value) {
        const button = document.getElementById("favorite-button");
        if (!button) return;
        tdI18n.setText(button.querySelector("[data-favorite-label]"), value ? "Favorite.Clear" : "Favorite.Set");
        button.querySelector("[data-favorite-filled]").hidden = !value;
        button.querySelector("[data-favorite-empty]").hidden = value;
        document.querySelector("#drop-favorite [name=IsFavorite]").value = String(!value);
        for (const row of document.querySelectorAll("#drop-list [data-drop-slug]")) {
            if (row.dataset.dropSlug === detail?.dataset.dropSlug) {
                row.querySelector("[data-list-favorite]").hidden = !value;
            }
        }
    }
    function locks() {
        for (const form of document.querySelectorAll("form[data-drop-action]")) {
            const group = form.dataset.dropAction;
            const blocked = active.has(group) || (group === "favorite" && (favoriteNeeded || favoriteReading))
                || (navigation && (navigation.form !== form || navigation.started));
            form.setAttribute("aria-busy", String(Boolean(blocked)));
            for (const control of form.querySelectorAll("button[type=submit], input:not([type=hidden]), textarea")) {
                control.disabled = Boolean(blocked);
            }
        }
        // 공개 범위 응답이 메뉴와 비밀번호 대화상자를 새로 그리므로, 변경이 끝날 때까지 메뉴를 열지 않는다.
        const accessToggle = document.getElementById("access-toggle");
        if (accessToggle) accessToggle.disabled = Boolean(active.has("access") || (navigation && navigation.started));
        for (const button of document.querySelectorAll("[data-favorite-recheck], [data-favorite-retry]")) {
            button.disabled = Boolean(active.has("favorite") || favoriteReading || favoriteNeeded || navigation);
        }
        const status = document.getElementById("drop-navigation-status");
        if (status) status.hidden = !navigation || navigation.started;
    }
    function initDialogs() {
        for (const dialog of document.querySelectorAll("dialog[open]")) {
            if (!dialog.matches(":modal")) {
                dialog.close();
                dialog.showModal();
                dialog.querySelector(".input-validation-error, input:not([type=hidden])")?.focus();
            }
        }
        locks();
        if (optimisticFavorite !== null) showFavorite(optimisticFavorite);
    }
    function read(kind) {
        if (!detail) return;
        if (kind === "favorite") { favoriteNeeded = false; favoriteReading = true; }
        else { sharedNeeded = false; sharedReading = true; }
        locks();
        htmx.ajax("GET", kind === "favorite" ? detail.dataset.favoriteStateUrl : detail.dataset.sharedStateUrl, {
            source: detail, target: detail, swap: "none", headers: { "X-Drop-Read": kind },
        }).catch(() => {});
    }
    function drain() {
        if (leaving || active.size) return;
        if (favoriteNeeded && !favoriteReading) { read("favorite"); return; }
        if (favoriteReading) return;
        if (navigation && !navigation.started) {
            navigation.started = true;
            const { form, submitter } = navigation;
            // A queued navigation keeps its original form and submitter.
            for (const input of form.querySelectorAll("input, button, textarea")) input.disabled = false;
            form.requestSubmit(submitter);
            return;
        }
        if (dirty) { dirty = false; sharedNeeded = true; notify("drop-changed"); }
        if (sharedNeeded && !sharedReading) read("shared");
    }
    document.addEventListener("submit", event => {
        const form = event.target;
        const group = form.dataset.dropAction;
        if (!group || !window.htmx) return;
        if (active.has(group) || (group === "favorite" && (favoriteNeeded || favoriteReading))
            || (navigation && navigation.form !== form)) {
            event.preventDefault(); event.stopImmediatePropagation(); return;
        }
        if (isNavigation(group)) {
            navigation ??= { form, submitter: event.submitter, started: false };
            if (active.size || favoriteNeeded || favoriteReading) {
                event.preventDefault(); event.stopImmediatePropagation(); locks(); return;
            }
            navigation.started = true;
        }
    }, true);

    document.addEventListener("htmx:before:request", event => {
        const { ctx } = event.detail;
        const elt = ctx.sourceElement;
        const requestConfig = ctx.request;
        const readKind = requestConfig.headers["X-Drop-Read"];
        if (readKind) {
            requests.set(ctx, { read: readKind, epoch });
            return;
        }
        const form = elt.closest?.("form[data-drop-action]");
        if (!form) return;
        const group = form.dataset.dropAction;
        const info = { group, form, focus: form.contains(document.activeElement) ? document.activeElement : null, desired: form.querySelector("[name=IsFavorite]")?.value === "true" };
        requests.set(ctx, info);
        active.set(group, info);
        epoch++;
        notify("drop-change-started");
        message(group);
        if (group === "favorite") {
            retryFavorite = info.desired;
            optimisticFavorite = info.desired;
            recovery(false);
            showFavorite(info.desired);
        }
        locks();
    });

    document.addEventListener("htmx:before:swap", event => {
        const info = requests.get(event.detail.ctx);
        if (info?.read && (info.epoch !== epoch || active.size || leaving || navigation?.started)) {
            info.stale = true;
            event.preventDefault();
        }
        // Error pages must not replace owner controls. A public unlock 401
        // is the intentional validation fragment returned by that form.
        const { ctx } = event.detail;
        if (ctx.response.status >= 400
            && !(ctx.sourceElement.matches("[data-public-unlock]")
                && ctx.response.status === 401
                && ctx.response.headers.get("Content-Type")?.includes("text/html"))) {
            event.preventDefault();
        }
    });

    document.addEventListener("htmx:finally:request", event => {
        const { ctx } = event.detail;
        const successful = ctx.response?.raw.ok && !ctx.status.startsWith("error");
        const info = requests.get(ctx);
        if (!info) {
            if (ctx.sourceElement.matches?.("[data-public-unlock]") && !successful && ctx.response?.status !== 401) {
                const error = document.querySelector("[data-public-error]");
                if (error) { tdI18n.setText(error, "Request.Failed"); error.hidden = false; }
            }
            return;
        }
        requests.delete(ctx);
        if (ctx.response?.headers.get("HX-Redirect")) { leaving = true; return; }
        if (info.read) {
            if (info.read === "favorite") favoriteReading = false;
            else sharedReading = false;
            if (info.stale) {
                if (info.read === "favorite") favoriteNeeded = true;
                else sharedNeeded = true;
            } else if (info.read === "favorite") {
                if (successful) {
                    optimisticFavorite = null;
                    const actual = document.getElementById("drop-favorite").dataset.favoriteValue === "true";
                    showFavorite(actual);
                    const matches = actual === retryFavorite;
                    message("favorite", matches ? "" : "Favorite.Uncertain");
                    recovery(!matches);
                    if (matches) retryFavorite = null;
                    dirty = true;
                } else {
                    message("favorite", "Favorite.CheckFailed");
                    recovery(true);
                }
            } else {
                message("shared", successful ? "" : "Share.RefreshFailed");
            }
            locks(); drain(); return;
        }

        active.delete(info.group);
        const outcome = ctx.response?.headers.get("X-Drop-Outcome");
        if (successful && outcome === "changed") {
            dirty = true;
            if (info.group === "favorite") {
                optimisticFavorite = null; retryFavorite = null; recovery(false);
            }
            const dialog = document.getElementById(dialogs[info.group]);
            if (dialog?.open) dialog.close();
            locks();
            if (!document.querySelector("dialog:modal") && document.activeElement === document.body) {
                const target = { favorite: "drop-actions-toggle", metadata: "drop-actions-toggle", access: "access-toggle" }[info.group] ?? `${info.group}-open`;
                document.getElementById(target)?.focus();
            }
        } else if (outcome !== "invalid") {
            message(info.group, ctx.response?.status === 404 ? "Operation.NotFound" : "Operation.Failed");
            if (info.group === "favorite") favoriteNeeded = true;
        }
        if (isNavigation(info.group)) navigation = null;
        initDialogs();
        if (info.focus?.isConnected && document.activeElement === document.body) info.focus.focus();
        drain();
    });

    // 설명은 ⋯ 메뉴에서 열어 그 자리에서 고친다. 저장 요청은 다른 드롭 작업과 같은 metadata 흐름을 탄다.
    const fitDescription = input => { input.style.height = "auto"; input.style.height = `${input.scrollHeight + 2}px`; };
    function openDescription(editor) {
        const input = editor.querySelector("[data-description-input]");
        if (editor.classList.contains("is-editing")) { input.focus(); return; }
        input.dataset.original = input.value;
        editor.classList.add("is-editing");
        fitDescription(input);
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    }
    function closeDescription(editor) {
        if (active.has("metadata")) return;
        const input = editor.querySelector("[data-description-input]");
        input.value = input.dataset.original ?? input.value;
        editor.classList.remove("is-editing");
        message("metadata");
        document.getElementById("drop-actions-toggle")?.focus();
    }
    document.addEventListener("click", event => {
        const editor = document.getElementById("drop-description-editor");
        if (!editor) return;
        if (event.target.closest?.("[data-description-edit]")) openDescription(editor);
        else if (event.target.closest?.("#drop-description-editor [data-description-cancel]")) closeDescription(editor);
    });
    document.addEventListener("keydown", event => {
        const input = event.target.closest?.("[data-description-input]");
        if (!input) return;
        if (event.key === "Escape") { event.preventDefault(); closeDescription(input.closest("#drop-description-editor")); }
        else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) { event.preventDefault(); input.form.requestSubmit(); }
    });
    document.addEventListener("input", event => {
        if (event.target.matches?.("[data-description-input]")) fitDescription(event.target);
    });

    document.addEventListener("click", async event => {
        if (event.target.closest("#copy-share-link")) {
            const button = document.getElementById("copy-share-link");
            const input = document.getElementById("share-link");
            try { await navigator.clipboard.writeText(input.value); tdI18n.setText(button, "Copy.Done"); }
            catch { input.select(); tdI18n.setText(button, "Copy.Selected"); }
        }
        if (event.target.closest("[data-favorite-recheck]")) { favoriteNeeded = true; drain(); }
        if (event.target.closest("[data-favorite-retry]") && retryFavorite !== null) {
            const form = document.getElementById("drop-favorite");
            form.querySelector("[name=IsFavorite]").value = String(retryFavorite);
            form.requestSubmit();
        }
    });
    document.addEventListener("input", event => {
        if (!event.target.matches("#NewDropPassword, [data-password-confirm]")) return;
        const password = document.getElementById("NewDropPassword");
        const confirmation = document.querySelector("[data-password-confirm]");
        tdI18n.setValidity(confirmation, password.value === confirmation?.value ? "" : "Password.Mismatch");
    });
    document.addEventListener("htmx:before:swap", event => {
        if (event.detail.ctx.sourceElement.matches?.("[data-public-unlock]")) {
            event.detail.ctx.restoreUnlockFocus = Boolean(document.activeElement.closest?.("[data-public-unlock]"));
        }
    });
    document.addEventListener("htmx:after:swap", event => {
        initDialogs();
        const publicHeading = document.getElementById("public-drop-heading");
        if (publicHeading && event.detail.ctx.sourceElement.matches?.("[data-public-unlock]")) tdI18n.setPageTitle(publicHeading);
        if (event.detail.ctx.restoreUnlockFocus && document.activeElement === document.body) {
            (document.getElementById("DropPassword") || document.getElementById("public-drop-heading"))?.focus();
        }
    });
    initDialogs();
})();
