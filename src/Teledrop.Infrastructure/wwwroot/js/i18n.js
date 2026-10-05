(() => {
    const catalogs = JSON.parse(document.getElementById("td-translations").textContent);
    let language = document.documentElement.lang === "ko" ? "ko" : "en";
    const targets = { text: null, "aria-label": "aria-label", title: "title", placeholder: "placeholder", tooltip: "data-tooltip", alt: "alt", summary: "data-list-summary" };
    const selector = Object.keys(targets).map(target => `[data-i18n-${target}]`).join(",");
    const locale = () => language === "ko" ? "ko-KR" : "en-US";
    const t = (key, args = []) => (catalogs[language][key] ?? catalogs.en[key] ?? key)
        .replace(/\{(\d+)\}/g, (_, index) => typeof args[index] === "number"
            ? new Intl.NumberFormat(locale()).format(args[index]) : String(args[index] ?? ""));
    const nodes = (root, query) => [...(root.matches?.(query) ? [root] : []), ...root.querySelectorAll(query)];
    function translate(node) {
        const args = JSON.parse(node.getAttribute("data-i18n-args") || "[]");
        for (const [target, attribute] of Object.entries(targets)) {
            const key = node.getAttribute(`data-i18n-${target}`);
            if (!key) continue;
            const value = t(key, args);
            if (attribute) node.setAttribute(attribute, value);
            else if (node.textContent !== value) node.textContent = value;
        }
    }
    function bind(node, target, key, args = []) {
        if (!node) return;
        if (key) {
            node.setAttribute(`data-i18n-${target}`, key);
            node.setAttribute("data-i18n-args", JSON.stringify(args));
            translate(node);
        } else {
            node.removeAttribute(`data-i18n-${target}`);
            if (target === "text") node.textContent = "";
        }
    }
    function format(root) {
        const dates = new Intl.DateTimeFormat(locale(), { dateStyle: "medium", timeStyle: "medium" });
        const shortDates = new Intl.DateTimeFormat(locale(), { dateStyle: "medium", timeStyle: "short" });
        const relative = new Intl.RelativeTimeFormat(locale(), { numeric: "auto" });
        for (const time of nodes(root, "time[data-relative-time], time[data-local-date]")) {
            const date = new Date(time.dateTime);
            if (Number.isNaN(date.getTime())) continue;
            time.title = dates.format(date);
            if (time.hasAttribute("data-local-date")) { time.textContent = time.dataset.localDate === "long" ? time.title : shortDates.format(date); continue; }
            const seconds = Math.max(0, (Date.now() - date.getTime()) / 1000);
            const [value, unit] = seconds < 90 ? [1, "minute"]
                : seconds < 2700 ? [Math.round(seconds / 60), "minute"]
                : seconds < 5400 ? [1, "hour"]
                : seconds < 79200 ? [Math.round(seconds / 3600), "hour"]
                : seconds < 129600 ? [1, "day"]
                : seconds < 2246400 ? [Math.round(seconds / 86400), "day"]
                : seconds < 3888000 ? [1, "month"]
                : seconds < 27648000 ? [Math.round(seconds / 2592000), "month"]
                : [Math.round(seconds / 31536000), "year"];
            time.textContent = seconds < 45 ? t("Time.SecondsAgo") : relative.format(-value, unit);
        }
        for (const node of nodes(root, "[data-file-size]")) {
            let value = Number(node.dataset.fileSize), unit = 0;
            while (value >= 1024 && unit < 4) { value /= 1024; unit++; }
            node.textContent = `${new Intl.NumberFormat(locale(), { maximumFractionDigits: 2 }).format(value)} ${["B", "KB", "MB", "GB", "TB"][unit]}`;
        }
        for (const node of nodes(root, "[data-number]")) node.textContent = new Intl.NumberFormat(locale()).format(Number(node.dataset.number));
    }
    function updateTitle() {
        const title = document.querySelector("title");
        if (title?.dataset.pageTitleKey) title.textContent = `${t(title.dataset.pageTitleKey)} - teledrop`;
    }
    function refresh(root = document) {
        for (const node of nodes(root, selector)) translate(node);
        format(root);
        for (const input of nodes(root, "[data-validation-key]")) input.setCustomValidity(t(input.dataset.validationKey));
        if (root === document) updateTitle();
    }
    function setValidity(input, key) {
        if (!input) return;
        if (key) input.dataset.validationKey = key;
        else delete input.dataset.validationKey;
        input.setCustomValidity(key ? t(key) : "");
    }
    window.tdI18n = {
        t, refresh, setValidity,
        setText: (node, key, args) => bind(node, "text", key, args),
        setAttribute: (node, attribute, key, args) => bind(node, attribute === "data-tooltip" ? "tooltip" : attribute, key, args),
        setPageTitle: heading => {
            const title = document.querySelector("title");
            title.dataset.pageTitleKey = heading.getAttribute("data-i18n-text")
                || heading.querySelector("[data-i18n-text]")?.getAttribute("data-i18n-text") || "";
            title.textContent = `${heading.textContent} - teledrop`;
        },
    };
    // Translate incoming HTML before it is inserted, even if the request began
    // before the language changed. Never retry or discard a successful mutation.
    document.addEventListener("htmx:after:request", event => {
        const ctx = event.detail.ctx;
        if (typeof ctx.text !== "string" || !ctx.response?.headers.get("Content-Type")?.includes("text/html")) return;
        const fragment = document.createElement("template");
        fragment.innerHTML = ctx.text;
        refresh(fragment.content);
        ctx.text = fragment.innerHTML;
    });
    document.addEventListener("htmx:after:swap", () => refresh());
    document.addEventListener("invalid", event => {
        if (event.target.validity?.valueMissing) setValidity(event.target, "Validation.Required");
    }, true);
    document.addEventListener("input", event => {
        if (event.target.dataset.validationKey === "Validation.Required" && event.target.value) setValidity(event.target, "");
    });
    refresh();

    const picker = document.getElementById("language-picker");
    if (!picker) return;
    const button = document.getElementById("language-toggle");
    const list = document.getElementById("language-options");
    const options = [...list.querySelectorAll("[data-value]")];
    const form = document.getElementById("language-form");
    const error = document.getElementById("language-error");
    let saving = false;
    // 메뉴 여닫기와 키보드는 site.js의 공용 메뉴가 맡는다. 현재 언어를 다시 골라도 선택을 저장한다.
    button.addEventListener("click", () => { error.hidden = true; });
    list.addEventListener("click", event => {
        const option = event.target.closest("[data-value]");
        if (option) void choose(option.dataset.value);
    });
    async function choose(next) {
        if (saving) return;
        saving = true;
        button.setAttribute("aria-disabled", "true");
        button.setAttribute("aria-busy", "true");
        error.hidden = true;
        const body = new FormData(form);
        body.set("language", next);
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        try {
            const response = await fetch(form.action, { method: "POST", body, signal: controller.signal,
                headers: { "X-Requested-With": "XMLHttpRequest" } });
            if (response.status !== 204) throw new Error("Language preference was not saved");
            language = next;
            document.documentElement.lang = language;
            document.getElementById("language-native").value = language;
            options.forEach(option => option.setAttribute("aria-checked", String(option.dataset.value === language)));
            bind(button, "aria-label", "Language.Current", [language === "ko" ? "한국어" : "English"]);
            refresh();
            bind(document.getElementById("language-status"), "text", "Language.Changed");
        } catch {
            bind(error, "text", "Language.Error");
            error.hidden = false;
        } finally {
            clearTimeout(timeout);
            saving = false;
            button.removeAttribute("aria-disabled");
            button.removeAttribute("aria-busy");
        }
    }
    form.addEventListener("submit", event => { event.preventDefault(); void choose(new FormData(form).get("language")); });
})();
