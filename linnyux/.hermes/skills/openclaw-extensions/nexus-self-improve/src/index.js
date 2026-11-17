import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { Type } from "@sinclair/typebox";
import { mkdirSync, existsSync, readFileSync, writeFileSync, appendFileSync, readdirSync } from "fs";
import { homedir } from "os";
import { join, resolve } from "path";

// ─── Persistent Store ──────────────────────────────────────────────────────
class LearningStore {
  constructor(dataDir) {
    this.baseDir = dataDir.replace(/^~/, homedir());
    mkdirSync(this.baseDir, { recursive: true });
    this.memoryPath = join(this.baseDir, "memory.md");
    this.archiveDir = join(this.baseDir, "archive");
    this.correctionsPath = join(this.baseDir, "corrections.jsonl");
    this.patternsPath = join(this.baseDir, "patterns.json");
    this.statsPath = join(this.baseDir, "stats.json");
    this.interactionCount = 0;
    mkdirSync(this.archiveDir, { recursive: true });
    this._initFiles();
  }

  _initFiles() {
    if (!existsSync(this.memoryPath)) {
      writeFileSync(this.memoryPath, [
        "# Nexus Self-Improvement Memory",
        "",
        "## Active Patterns",
        "",
        "## Recent Corrections",
        "",
        "## Lessons Learned",
        "",
      ].join("\n"), "utf-8");
    }
    if (!existsSync(this.patternsPath)) {
      writeFileSync(this.patternsPath, JSON.stringify({ patterns: [], lastUpdated: null }, null, 2), "utf-8");
    }
    if (!existsSync(this.statsPath)) {
      writeFileSync(this.statsPath, JSON.stringify({
        totalInteractions: 0,
        totalCorrections: 0,
        totalLessons: 0,
        totalArchives: 0,
        lastImprovement: null,
      }, null, 2), "utf-8");
    }
    if (!existsSync(this.correctionsPath)) {
      writeFileSync(this.correctionsPath, "", "utf-8");
    }
  }

  loadMemory() {
    try {
      return readFileSync(this.memoryPath, "utf-8");
    } catch {
      return "";
    }
  }

  appendCorrection(entry) {
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      ...entry,
    }) + "\n";
    appendFileSync(this.correctionsPath, line, "utf-8");
    this._incrementStat("totalCorrections");
  }

  appendLesson(lesson) {
    const memory = this.loadMemory();
    const lessonLine = `- [${new Date().toISOString().split("T")[0]}] ${lesson}\n`;
    // Insert after "## Lessons Learned"
    const updated = memory.replace(
      /(## Lessons Learned\n)/,
      `$1${lessonLine}`
    );
    writeFileSync(this.memoryPath, updated, "utf-8");
    this._incrementStat("totalLessons");
  }

  addPattern(pattern) {
    let data;
    try {
      data = JSON.parse(readFileSync(this.patternsPath, "utf-8"));
    } catch {
      data = { patterns: [], lastUpdated: null };
    }
    data.patterns.push({
      id: `p-${Date.now()}`,
      text: pattern,
      created: new Date().toISOString(),
      confidence: 1,
      hitCount: 1,
    });
    data.lastUpdated = new Date().toISOString();
    writeFileSync(this.patternsPath, JSON.stringify(data, null, 2), "utf-8");
    this._incrementStat("totalLessons");
  }

  getPatterns() {
    try {
      return JSON.parse(readFileSync(this.patternsPath, "utf-8"));
    } catch {
      return { patterns: [], lastUpdated: null };
    }
  }

  getStats() {
    try {
      return JSON.parse(readFileSync(this.statsPath, "utf-8"));
    } catch {
      return {};
    }
  }

  _incrementStat(field) {
    try {
      const stats = this.getStats();
      stats[field] = (stats[field] || 0) + 1;
      stats.lastImprovement = new Date().toISOString();
      writeFileSync(this.statsPath, JSON.stringify(stats, null, 2), "utf-8");
    } catch {}
  }

  getRecentCorrections(limit = 10) {
    try {
      const lines = readFileSync(this.correctionsPath, "utf-8")
        .split("\n")
        .filter(Boolean);
      return lines.slice(-limit).map(l => JSON.parse(l));
    } catch {
      return [];
    }
  }

  incrementInteraction() {
    this.interactionCount++;
    const stats = this.getStats();
    stats.totalInteractions = (stats.totalInteractions || 0) + 1;
    writeFileSync(this.statsPath, JSON.stringify(stats, null, 2), "utf-8");
  }
}

// ─── Plugin Entry ──────────────────────────────────────────────────────────
export default definePluginEntry({
  id: "nexus-self-improve",
  name: "Nexus Self-Improvement",
  description: "Continuous self-improvement: evaluates responses, tracks mistakes, extracts patterns, compounds learnings across sessions",

  register(api) {
    let store = null;

    // ── Self-Evaluation Tool ──────────────────────────────────────────
    api.registerTool({
      name: "self_evaluate",
      description: "Evaluate the quality of your last response. Call this after responding to identify mistakes, improvements, and patterns.",
      parameters: Type.Object({
        responseType: Type.Optional(Type.String({ description: "Type of response given (advice, code, explanation, etc.)" })),
        issues: Type.Optional(Type.Array(Type.String(), { description: "Any issues you noticed in your response" })),
        improvements: Type.Optional(Type.Array(Type.String(), { description: "How you could improve next time" })),
        lesson: Type.Optional(Type.String({ description: "A reusable lesson extracted from this interaction" })),
        pattern: Type.Optional(Type.String({ description: "A behavioral pattern to adopt going forward" })),
      }),
      async execute(_id, params) {
        if (!store) return { content: [{ type: "text", text: "Store not initialized" }] };

        const results = [];

        if (params.issues?.length) {
          store.appendCorrection({
            type: "self-correction",
            issues: params.issues,
            improvements: params.improvements || [],
          });
          results.push(`Logged ${params.issues.length} issue(s)`);
        }

        if (params.lesson) {
          store.appendLesson(params.lesson);
          results.push(`Lesson recorded: "${params.lesson}"`);
        }

        if (params.pattern) {
          store.addPattern(params.pattern);
          results.push(`Pattern added: "${params.pattern}"`);
        }

        const stats = store.getStats();
        results.push(`\n📊 Self-Improvement Stats: ${stats.totalLessons || 0} lessons, ${stats.totalCorrections || 0} corrections, ${stats.totalInteractions || 0} interactions`);

        return {
          content: [{ type: "text", text: results.join("\n") }],
        };
      },
    });

    // ── Review Patterns Tool ─────────────────────────────────────────
    api.registerTool({
      name: "review_patterns",
      description: "Review learned behavioral patterns. Use this to remind yourself what you've learned and check for recurring issues.",
      parameters: Type.Object({
        filter: Type.Optional(Type.String({ description: "Optional filter keyword to search for specific patterns" })),
      }),
      async execute(_id, params) {
        if (!store) return { content: [{ type: "text", text: "Store not initialized" }] };

        const { patterns } = store.getPatterns();
        const corrections = store.getRecentCorrections(5);
        const stats = store.getStats();
        const memory = store.loadMemory();

        let result = `📚 **Self-Improvement Summary**\n\n`;

        result += `**Stats:** ${stats.totalInteractions || 0} interactions · ${stats.totalLessons || 0} lessons · ${stats.totalCorrections || 0} corrections\n\n`;

        if (patterns?.length) {
          const filtered = params.filter
            ? patterns.filter(p => p.text.toLowerCase().includes(params.filter.toLowerCase()))
            : patterns;
          result += `**Active Patterns (${filtered.length}):**\n`;
          filtered.slice(-10).forEach(p => {
            result += `- ${p.text} (confidence: ${p.confidence}, hits: ${p.hitCount})\n`;
          });
          result += "\n";
        }

        if (corrections.length) {
          result += `**Recent Corrections:**\n`;
          corrections.forEach(c => {
            result += `- [${c.ts?.split("T")[0]}] ${c.issues?.join(", ") || "unknown"}\n`;
          });
          result += "\n";
        }

        return {
          content: [{ type: "text", text: result }],
        };
      },
    });

    // ── Reset Learning Tool ──────────────────────────────────────────
    api.registerTool({
      name: "reset_learning",
      description: "Reset learning data. Use only if explicitly asked to clear all learned patterns and corrections.",
      parameters: Type.Object({
        confirm: Type.Boolean({ description: "Must be true to confirm reset" }),
      }),
      async execute(_id, params) {
        if (!params.confirm) {
          return { content: [{ type: "text", text: "Reset requires confirm: true" }] };
        }
        if (!store) return { content: [{ type: "text", text: "Store not initialized" }] };

        // Archive existing data
        const archiveName = `archive-${Date.now()}`;
        const archivePath = join(store.archiveDir, archiveName);
        mkdirSync(archivePath, { recursive: true });

        // Save current state to archive
        const { patterns } = store.getPatterns();
        writeFileSync(join(archivePath, "patterns.json"), JSON.stringify(patterns, null, 2), "utf-8");
        writeFileSync(join(archivePath, "corrections.jsonl"), readFileSync(store.correctionsPath, "utf-8"), "utf-8");

        // Reset
        writeFileSync(store.memoryPath, [
          "# Nexus Self-Improvement Memory",
          "",
          "## Active Patterns",
          "",
          "## Recent Corrections",
          "",
          "## Lessons Learned",
          "",
        ].join("\n"), "utf-8");
        writeFileSync(store.patternsPath, JSON.stringify({ patterns: [], lastUpdated: null }, null, 2), "utf-8");
        writeFileSync(store.correctionsPath, "", "utf-8");

        const stats = store.getStats();
        stats.totalArchives = (stats.totalArchives || 0) + 1;
        writeFileSync(store.statsPath, JSON.stringify(stats, null, 2), "utf-8");

        return {
          content: [{ type: "text", text: `✅ Learning data archived to ${archiveName}. ${patterns.length} patterns preserved in archive.` }],
        };
      },
    });

    // ── Hooks ─────────────────────────────────────────────────────────

    // On gateway start: init store from config
    api.on("gateway_start", async (event) => {
      const config = event?.context?.pluginConfig || {};
      const dataDir = config.dataDir || "~/.openclaw/self-improve";
      store = new LearningStore(dataDir);

      const stats = store.getStats();
      if (config.debug) {
        console.log(`[nexus-self-improve] Initialized. ${stats.totalLessons || 0} lessons, ${stats.totalPatterns || 0} patterns remembered.`);
      }
    });

    // Before prompt: inject memory context (only on first load per start)
    api.on("before_prompt_build", async (event) => {
      if (!store) return;

      const memory = store.loadMemory();
      const { patterns } = store.getPatterns();
      const stats = store.getStats();

      if (!memory && !patterns?.length) return;

      // Build compact reminder block, only if there's actual learning data
      const recentPatterns = (patterns || []).slice(-5);
      if (recentPatterns.length === 0 && !memory) return;

      const reminderLines = [
        "\n<self_improvement_memory>",
      ];

      if (recentPatterns.length > 0) {
        reminderLines.push("Active patterns to follow:");
        recentPatterns.forEach(p => reminderLines.push(`  • ${p.text}`));
        reminderLines.push("");
      }

      if (stats.totalCorrections > 0) {
        const recent = store.getRecentCorrections(3);
        if (recent.length > 0) {
          reminderLines.push("Recent areas of improvement:");
          recent.forEach(c => {
            if (c.issues?.length) {
              reminderLines.push(`  • Avoid: ${c.issues.join(", ")}`);
            }
          });
        }
      }

      reminderLines.push(`</self_improvement_memory>\n`);
      reminderLines.push(`Stats: ${stats.totalLessons || 0} · Corrections: ${stats.totalCorrections || 0} · Total interactions: ${stats.totalInteractions || 0}`);

      return {
        extraSystemPrompt: reminderLines.join("\n"),
      };
    });

    // After agent responds: track interaction, optionally extract lessons
    api.on("agent_end", async (event) => {
      if (!store) return;
      store.incrementInteraction();

      const config = event?.context?.pluginConfig || {};
      const freq = config.learningFrequency || 5;

      // Every N interactions, prompt memory consolidation
      if (store.interactionCount % freq === 0) {
        const stats = store.getStats();
        if (config.debug) {
          console.log(`[nexus-self-improve] ${store.interactionCount} interactions. ${stats.totalLessons} lessons learned.`);
        }
      }
    });

    // Session start: increment count
    api.on("session_start", async () => {
      if (!store) return;
      // No-op, interaction tracking happens in agent_end
    });
  },
});
