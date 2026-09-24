import { cpSync, mkdirSync } from "node:fs";
const source = "node_modules/pdfjs-dist";
const target = "wwwroot/js/pdfjs";
mkdirSync(target, { recursive: true });
for (const name of ["pdf.min.mjs", "pdf.worker.min.mjs"])
    cpSync(`${source}/build/${name}`, `${target}/${name}`);
for (const name of ["cmaps", "standard_fonts", "wasm", "LICENSE"])
    cpSync(`${source}/${name}`, `${target}/${name}`, { recursive: true });
