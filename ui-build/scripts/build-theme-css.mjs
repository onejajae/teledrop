import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "../..");
const themeTokensPath = path.join(
  projectRoot,
  "app/interfaces/web/static/theme/theme_tokens.json",
);
const outputPath = path.join(
  projectRoot,
  "app/interfaces/web/static/css/generated/theme-tokens.css",
);

const themePluginPath =
  "../../../../../../ui-build/node_modules/daisyui/theme/index.js";
const daisyuiPluginPath =
  "../../../../../../ui-build/node_modules/daisyui/index.js";

const payload = JSON.parse(await readFile(themeTokensPath, "utf8"));
const themeOrder = ["light", "dark"];

const formatThemeBlock = (name, config) => {
  const lines = [
    `@plugin "${themePluginPath}" {`,
    `  name: "${name}";`,
  ];

  if (config.daisyui.default) {
    lines.push("  default: true;");
  }
  if (config.daisyui.prefers_dark) {
    lines.push("  prefersdark: true;");
  }

  lines.push(`  color-scheme: ${config.daisyui.color_scheme};`);

  for (const [token, value] of Object.entries(config.daisyui.tokens)) {
    lines.push(`  ${token}: ${value};`);
  }

  lines.push("}");
  return lines.join("\n");
};

const css = [
  `@plugin "${daisyuiPluginPath}" {`,
  "  themes: false;",
  "}",
  "",
  ...themeOrder.map((name) => formatThemeBlock(name, payload[name])),
  "",
  "@layer components {",
  "  .td-logo-wordmark {",
  "    display: block;",
  "    width: 100%;",
  "    aspect-ratio: 1100 / 230;",
  `    background-color: ${payload.light.logo_color};`,
  '    -webkit-mask: url("/static/images/logo.svg") center / contain no-repeat;',
  '    mask: url("/static/images/logo.svg") center / contain no-repeat;',
  "    transition: background-color 0.2s ease, opacity 0.2s ease;",
  "  }",
  "",
  '  html[data-theme="light"] .td-logo-wordmark {',
  `    background-color: ${payload.light.logo_color};`,
  "    opacity: 1;",
  "  }",
  "",
  '  html[data-theme="dark"] .td-logo-wordmark {',
  `    background-color: ${payload.dark.logo_color};`,
  "    opacity: 1;",
  "  }",
  "}",
  "",
].join("\n");

await mkdir(path.dirname(outputPath), { recursive: true });
await writeFile(outputPath, css, "utf8");
