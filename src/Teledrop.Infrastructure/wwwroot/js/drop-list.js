(() => {
    let desired = null;
    let generation = 0;
    let mutationEpoch = 0;
    const requests = new WeakMap();
    const root = () => document.getElementById("drop-list");
    const fields = ["search", "sort", "direction", "pageNumber", "currentSlug"];
    const readState = () => JSON.parse(root()?.dataset.listState || "{}");
    desired = readState();

    document.addEventListener("htmx:configRequest", event => {
        const detail = event.detail;
        const list = detail.elt.closest?.("#drop-list");
        if (!list) return;
        const values = new URL(detail.path, document.baseURI).searchParams;
        const refresh = detail.headers["X-Drop-List-Refresh"] === "true";
        if (!refresh) {
            // Capture the requested state before its response can replace the list.
            const next = { ...readState(), pageNumber: 1 };
            for (const name of fields) {
                if (values.has(name)) next[name] = values.get(name);
                if (detail.parameters[name] !== undefined) next[name] = detail.parameters[name];
            }
            desired = next;
        }
        detail.path = new URL(list.dataset.listUrl, document.baseURI).pathname;
        detail.parameters.handler = "DropList";
        for (const name of fields) detail.parameters[name] = desired[name] ?? "";
    });

    document.addEventListener("htmx:beforeRequest", event => {
        if (!event.detail.elt.closest?.("#drop-list")) return;
        requests.set(event.detail.xhr, { generation: ++generation, epoch: mutationEpoch });
    });
    document.addEventListener("htmx:beforeSwap", event => {
        const request = requests.get(event.detail.xhr);
        if (request && (request.generation !== generation || request.epoch !== mutationEpoch)) {
            event.detail.shouldSwap = false;
        }
    });
    document.addEventListener("htmx:afterRequest", event => {
        const request = requests.get(event.detail.xhr);
        if (!request || request.generation !== generation || request.epoch !== mutationEpoch) return;
        const error = root()?.querySelector("[data-list-error]");
        if (error) error.hidden = event.detail.successful;
        if (event.detail.successful) desired = readState();
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
