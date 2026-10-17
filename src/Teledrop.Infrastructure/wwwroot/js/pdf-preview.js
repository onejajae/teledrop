const initializePdfPreviews = () => {
    for (const root of document.querySelectorAll("[data-pdf-url]:not([data-pdf-ready])")) {
        root.dataset.pdfReady = "true";
        void loadPdf(root);
    }
};

async function loadPdf(root) {
    const status = root.querySelector("[data-pdf-status]");
    const canvas = root.querySelector("[data-pdf-canvas]");
    const previous = root.querySelector("[data-pdf-prev]");
    const next = root.querySelector("[data-pdf-next]");
    try {
        const pdfjs = await import("./pdfjs/pdf.min.mjs");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL("./pdfjs/pdf.worker.min.mjs", import.meta.url).href;
        const assets = new URL("./pdfjs/", import.meta.url).href;
        const pdf = await pdfjs.getDocument({
            url: root.dataset.pdfUrl,
            cMapUrl: `${assets}cmaps/`, cMapPacked: true,
            standardFontDataUrl: `${assets}standard_fonts/`,
            wasmUrl: `${assets}wasm/`,
            isEvalSupported: false,
        }).promise;
        let pageNumber = 0; // No page is available for navigation until the first render succeeds.
        let rendering = false;
        const render = async (number) => {
            if (rendering) return;
            rendering = true;
            const focused = root.contains(document.activeElement) ? document.activeElement : null;
            previous.disabled = next.disabled = true;
            let renderTask;
            try {
                const page = await pdf.getPage(number);
                const base = page.getViewport({ scale: 1 });
                const scale = Math.min(window.devicePixelRatio || 1, 2) * Math.max(root.clientWidth, 320) / base.width;
                const viewport = page.getViewport({ scale });
                canvas.width = Math.ceil(viewport.width);
                canvas.height = Math.ceil(viewport.height);
                renderTask = page.render({ canvas, viewport });
                await renderTask.promise;
                canvas.hidden = false;
                pageNumber = number;
                tdI18n.setText(status, "Pdf.Page", [pageNumber, pdf.numPages]);
                tdI18n.setAttribute(canvas, "aria-label", "Pdf.PageLabel", [pageNumber, pdf.numPages]);
            } catch {
                // Release PDF.js's canvas ownership even if graphics initialization failed.
                renderTask?.cancel();
                tdI18n.setText(status, "Pdf.PageFailed");
            } finally {
                rendering = false;
                previous.disabled = pageNumber <= 1;
                next.disabled = pageNumber === 0 || pageNumber >= pdf.numPages;
                if (focused && document.activeElement === document.body) {
                    if (focused.isConnected && !focused.disabled) focused.focus();
                    else (number >= pdf.numPages ? previous : next).focus();
                    if (document.activeElement === document.body) status.focus();
                }
            }
        };
        previous.addEventListener("click", () => void render(pageNumber - 1));
        next.addEventListener("click", () => void render(pageNumber + 1));
        await render(1);
    } catch {
        tdI18n.setText(status, "Pdf.Failed");
    }
}

initializePdfPreviews();
document.addEventListener("htmx:after:swap", initializePdfPreviews);
