import { cpSync, mkdirSync, rmSync } from "node:fs";
// htmx, PDF.js, Pretendard는 저장소에 커밋하지 않는다. npm install·ci 때마다 node_modules에서 다시 복사한다.
mkdirSync("wwwroot/js", { recursive: true });
cpSync("node_modules/htmx.org/dist/htmx.min.js", "wwwroot/js/htmx.min.js");

const source = "node_modules/pdfjs-dist";
const target = "wwwroot/js/pdfjs";
rmSync(target, { recursive: true, force: true });
mkdirSync(target, { recursive: true });
for (const name of ["pdf.min.mjs", "pdf.worker.min.mjs"])
    cpSync(`${source}/build/${name}`, `${target}/${name}`);
for (const name of ["cmaps", "standard_fonts", "wasm", "LICENSE"])
    cpSync(`${source}/${name}`, `${target}/${name}`, { recursive: true });

const fonts = "wwwroot/fonts";
rmSync(fonts, { recursive: true, force: true });
mkdirSync(fonts, { recursive: true });
for (const weight of ["Regular", "Medium", "SemiBold", "Bold"])
    cpSync(`node_modules/pretendard/dist/web/static/woff2/Pretendard-${weight}.woff2`, `${fonts}/Pretendard-${weight}.woff2`);
cpSync("node_modules/pretendard/dist/LICENSE.txt", `${fonts}/OFL.txt`);
