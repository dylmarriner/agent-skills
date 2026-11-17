/**
 * Install this OpenClaw plugin into a local OpenClaw installation.
 *
 * Usage:
 *   node scripts/install-to-openclaw.mjs                     # auto-detect
 *   OPENCLAW_ROOT=/path/to/openclaw node scripts/install-to-openclaw.mjs
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(__dirname, "..");
const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || findOpenClawRoot();

function findOpenClawRoot() {
  const candidates = [
    path.resolve(PLUGIN_ROOT, "..", "..", "openclaw"),
    path.resolve(PLUGIN_ROOT, "..", "openclaw"),
    "/home/lin/openclaw",
    process.cwd(),
  ];
  for (const dir of candidates) {
    const pkg = path.join(dir, "package.json");
    if (fs.existsSync(pkg)) {
      try {
        const data = JSON.parse(fs.readFileSync(pkg, "utf8"));
        if (data.name === "openclaw" || data.openclaw) return dir;
      } catch { continue; }
    }
  }
  console.error("Could not find OpenClaw. Set OPENCLAW_ROOT env var.");
  process.exit(1);
}

const TARGET_DIR = path.join(OPENCLAW_ROOT, "extensions", "synapse");

const FILES_TO_COPY = [
  "package.json", "openclaw.plugin.json", "tsconfig.json",
  "src/index.ts", "src/plugin.ts", "src/config.ts",
  "src/tool.ts", "src/types.ts", "src/prompt-guidance.ts",
  "skills/synapse/SKILL.md",
];

console.log(`Installing plugin into: ${OPENCLAW_ROOT}`);
fs.mkdirSync(TARGET_DIR, { recursive: true });

for (const file of FILES_TO_COPY) {
  const src = path.join(PLUGIN_ROOT, file);
  const dst = path.join(TARGET_DIR, file);
  if (fs.existsSync(src)) {
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(src, dst);
    console.log(`  ✓ ${file}`);
  }
}

// Generate api.ts barrel
const apiContent = `export type { SynapseConfig } from "./src/types.js";
export { registerSynapsePlugin, type SynapsePluginApi } from "./src/plugin.js";
`;
fs.writeFileSync(path.join(TARGET_DIR, "api.ts"), apiContent);
console.log("  ✓ api.ts (generated)");
