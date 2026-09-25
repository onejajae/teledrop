(() => {
    let desired = null;
    let generation = 0;
    let mutationEpoch = 0;
    const requests = new WeakMap();
    const root = () => document.getElementById("drop-list");
    const fields = ["search", "sort", "direction", "pageNumber", "currentSlug"];
    const readState = () => JSON.parse(root()?.dataset.listState || "{}");
    desired = readState();

    document.addEventListener("htmx:config:request", event => {
        const { ctx } = event.detail;
        const detail = ctx.request;
        const list = ctx.sourceElement.closest?.("#drop-list");
        if (!list) return;
        const values = new URL(detail.action, document.baseURI).searchParams;
        const refresh = detail.headers["X-Drop-List-Refresh"] === "true";
        if (!refresh) {
            // Capture the requested state before its response can replace the list.
            const next = { ...readState(), pageNumber: 1 };
            for (const name of fields) {
                if (values.has(name)) next[name] = values.get(name);
                if (detail.body.has(name)) next[name] = detail.body.get(name);
            }
            desired = next;
        }
        detail.action = new URL(list.dataset.listUrl, document.baseURI).pathname;
        detail.body.set("handler", "DropList");
        for (const name of fields) detail.body.set(name, desired[name] ?? "");
    });

    document.addEventListener("htmx:before:request", event => {
        if (!event.detail.ctx.sourceElement.closest?.("#drop-list")) return;
        requests.set(event.detail.ctx, { generation: ++generation, epoch: mutationEpoch });
    });
    document.addEventListener("htmx:before:swap", event => {
        const request = requests.get(event.detail.ctx);
        if (request && (request.generation !== generation || request.epoch !== mutationEpoch)) {
            event.preventDefault();
        }
    });
    document.addEventListener("htmx:finally:request", event => {
        const request = requests.get(event.detail.ctx);
        if (!request || request.generation !== generation || request.epoch !== mutationEpoch) return;
        const successful = event.detail.ctx.response?.raw.ok && !event.detail.ctx.status.startsWith("error");
        const error = root()?.querySelector("[data-list-error]");
        if (error) error.hidden = successful;
        if (successful) desired = readState();
    });
    document.addEventListener("drop-change-started", () => { mutationEpoch++; });
    document.addEventListener("drop-changed", () => {
        const list = root();
        if (!list) return;
        htmx.ajax("GET", list.dataset.listUrl, {
            source: list, target: list, swap: "outerHTML",
            headers: { "X-Drop-List-Refresh": "true" },
        }).catch(() => {});
    });
})();
