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
        let pageNumber = 1;
        let rendering = false;
        const render = async (number) => {
            if (rendering) return;
            rendering = true;
            previous.disabled = next.disabled = true;
            try {
                const page = await pdf.getPage(number);
                const base = page.getViewport({ scale: 1 });
                const scale = Math.min(window.devicePixelRatio || 1, 2) * Math.max(root.clientWidth, 320) / base.width;
                const viewport = page.getViewport({ scale });
                canvas.width = Math.ceil(viewport.width);
                canvas.height = Math.ceil(viewport.height);
                await page.render({ canvas, viewport }).promise;
                canvas.hidden = false;
                pageNumber = number;
                status.textContent = `${pageNumber} / ${pdf.numPages} 페이지`;
                canvas.setAttribute("aria-label", `PDF ${pageNumber} / ${pdf.numPages} 페이지`);
            } catch {
                status.textContent = "페이지를 표시하지 못했습니다. 다운로드 버튼으로 파일을 저장해주세요.";
            } finally {
                rendering = false;
                previous.disabled = pageNumber <= 1;
                next.disabled = pageNumber >= pdf.numPages;
            }
        };
        previous.addEventListener("click", () => void render(pageNumber - 1));
        next.addEventListener("click", () => void render(pageNumber + 1));
        await render(1);
    } catch {
        status.textContent = "PDF를 표시하지 못했습니다. 다운로드 버튼으로 파일을 저장해주세요.";
    }
}

initializePdfPreviews();
document.addEventListener("htmx:after:swap", initializePdfPreviews);
