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
    const dialogs = { metadata: "metadata-dialog", password: "password-dialog", slug: "url-dialog", delete: "delete-dialog" };
    const isNavigation = group => group === "slug" || group === "delete";
    const notify = name => document.body.dispatchEvent(new CustomEvent(name, { bubbles: true }));

    function message(group, text = "") {
        for (const node of document.querySelectorAll(`[data-operation-error="${group}"]`)) {
            node.textContent = text;
            node.hidden = !text;
        }
    }
    function recovery(show) {
        const node = document.getElementById("favorite-recovery");
        if (node) node.hidden = !show;
    }
    function showFavorite(value) {
        const button = document.getElementById("favorite-button");
        if (!button) return;
        button.setAttribute("aria-pressed", String(value));
        const label = value ? "즐겨찾기 해제" : "즐겨찾기 설정";
        button.setAttribute("aria-label", label);
        button.dataset.tooltip = label;
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
        const info = { group, form, desired: form.querySelector("[name=IsFavorite]")?.value === "true" };
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
                if (error) { error.textContent = "요청에 실패했습니다. 다시 시도하세요."; error.hidden = false; }
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
                    message("favorite", matches ? "" : "즐겨찾기 적용 결과가 확정되지 않았습니다. 확인된 서버 상태를 표시합니다.");
                    recovery(!matches);
                    if (matches) retryFavorite = null;
                    dirty = true;
                } else {
                    message("favorite", "즐겨찾기 상태를 확인할 수 없습니다. 다시 확인하거나 원래 요청을 재시도하세요.");
                    recovery(true);
                }
            } else {
                message("shared", successful ? "" : "공유 안내를 갱신하지 못했습니다. 목록 새로고침 후 다시 확인하세요.");
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
            if (!document.querySelector("dialog:modal")) document.getElementById(`${info.group}-open`)?.focus();
            const heading = document.getElementById("drop-heading");
            if (info.group === "metadata" && heading) document.title = `${heading.textContent} - teledrop`;
        } else if (outcome !== "invalid") {
            message(info.group, ctx.response?.status === 404 ? "Drop을 찾을 수 없습니다. 페이지를 새로고침해 주세요." : "변경을 저장하지 못했습니다. 입력을 확인하고 다시 시도하세요.");
            if (info.group === "favorite") favoriteNeeded = true;
        }
        if (isNavigation(info.group)) navigation = null;
        initDialogs(); drain();
    });

    document.addEventListener("click", async event => {
        if (event.target.closest("#copy-share-link")) {
            const button = document.getElementById("copy-share-link");
            const input = document.getElementById("share-link");
            try { await navigator.clipboard.writeText(input.value); button.textContent = "복사됨"; }
            catch { input.select(); button.textContent = "링크 선택됨"; }
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
        confirmation?.setCustomValidity(password.value === confirmation.value ? "" : "비밀번호가 일치하지 않습니다.");
    });
    document.addEventListener("htmx:after:swap", initDialogs);
    initDialogs();
})();
