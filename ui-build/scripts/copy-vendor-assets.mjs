import { copyFile, mkdir } from "node:fs/promises";
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
];

await Promise.all(
  vendorAssets.map(async ({ source, target }) => {
    await mkdir(path.dirname(target), { recursive: true });
    await copyFile(source, target);
  }),
);
