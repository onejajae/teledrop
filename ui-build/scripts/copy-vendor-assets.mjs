import { copyFile, cp, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "../..");

const vendorAssets = [
  {
    source: path.join(
      projectRoot,
      "ui-build/node_modules/htmx.org/dist/htmx.min.js",
    ),
    target: path.join(
      projectRoot,
      "app/interfaces/web/static/vendor/htmx/htmx.min.js",
    ),
  },
  {
    source: path.join(
      projectRoot,
      "ui-build/node_modules/pretendard/dist/web/variable/pretendardvariable.css",
    ),
    target: path.join(
      projectRoot,
      "app/interfaces/web/static/vendor/pretendard/variable/pretendardvariable.css",
    ),
  },
  {
    source: path.join(
      projectRoot,
      "ui-build/node_modules/pretendard/dist/LICENSE.txt",
    ),
    target: path.join(
      projectRoot,
      "app/interfaces/web/static/vendor/pretendard/LICENSE.txt",
    ),
  },
];

const vendorDirectories = [
  {
    source: path.join(
      projectRoot,
      "ui-build/node_modules/pretendard/dist/web/variable/woff2",
    ),
    target: path.join(
      projectRoot,
      "app/interfaces/web/static/vendor/pretendard/variable/woff2",
    ),
  },
];

await Promise.all(
  vendorAssets.map(async ({ source, target }) => {
    await mkdir(path.dirname(target), { recursive: true });
    await copyFile(source, target);
  }),
);

await Promise.all(
  vendorDirectories.map(async ({ source, target }) => {
    await mkdir(path.dirname(target), { recursive: true });
    await cp(source, target, { recursive: true, force: true });
  }),
);
