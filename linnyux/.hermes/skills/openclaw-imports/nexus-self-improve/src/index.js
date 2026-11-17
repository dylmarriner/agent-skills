import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { Type } from "@sinclair/typebox";
import { mkdirSync, existsSync, readFileSync, writeFileSync, appendFileSync } from "fs";
import { homedir } from "os";
import { join } from "path";

// ─── Persistent Learning Store ─────────────────────────────────────────────
class LearningStore {
  constructor(dataDir) {
    this.baseDir = dataDir.replace(/^~/, homedir());
    mkdirSync(this.baseDir, { recursive: true });

    this.files = {
      memory: join(this.baseDir, "memory.md"),
      corrections: join(this.baseDir, "corrections.jsonl"),
      patterns: join(this.baseDir, "patterns.json"),
      goals: join(this.baseDir, "goals.json"),
      reflections: join(this.baseDir, "reflections.json"),
      stats: join(this.baseDir, "stats.json"),
      archiveDir: join(this.baseDir, "archive"),
    };

    mkdirSync(this.files.archiveDir, { recursive: true });
    this.interactionCount = 0;
    this._init();
  }

  _init() {
    const defaults = [
      [this.files.memory, `# Nexus Self-Improvement Memory\n\n## Active Patterns\n\n## Lessons Learned\n\n## Goals\n\n`],
      [this.files.patterns, JSON.stringify({ patterns: [], lastUpdated: null }, null, 2)],
      [this.files.goals, JSON.stringify({ goals: [], completed: [] }, null, 2)],
      [this.files.reflections, JSON.stringify({ entries: [] }, null, 2)],
      [this.files.stats, JSON.stringify({
        totalInteractions: 0, totalCorrections: 0, totalLessons: 0,
        totalReflections: 0, totalGoals: 0, goalsCompleted: 0,
        lastImprovement: null, currentLevel: 1, streak: 0,
      }, null, 2)],
      [this.files.corrections, ""],
    ];
    defaults.forEach(([path, content]) => {
      if (!existsSync(path)) writeFileSync(path, content, "utf-8");
    });
  }

  // ── Memory ──────────────────────────────────────────────────────────
  readMemory() { return this._read(this.files.memory, ""); }

  appendToMemory(section, line) {
    const marker = `## ${section}\n`;
    let content = this.readMemory();
    if (content.includes(marker)) {
      content = content.replace(new RegExp(`(${marker})`), `$1${line}\n`);
    } else {
      content += `\n${marker}${line}\n`;
    }
    writeFileSync(this.files.memory, content, "utf-8");
  }

  // ── Corrections ─────────────────────────────────────────────────────
  addCorrection(entry) {
    appendFileSync(this.files.corrections, JSON.stringify({ ts: new Date().toISOString(), ...entry }) + "\n", "utf-8");
    this._incStat("totalCorrections");
  }

  getRecentCorrections(limit = 5) {
    return this._readLines(this.files.corrections).slice(-limit).map(l => JSON.parse(l));
  }

  // ── Patterns ────────────────────────────────────────────────────────
  addPattern(text) {
    const data = this._readJSON(this.files.patterns, { patterns: [] });
    data.patterns.push({
      id: `p-${Date.now()}`, text, created: new Date().toISOString(),
      confidence: 1, hitCount: 1, lastApplied: new Date().toISOString(),
    });
    data.lastUpdated = new Date().toISOString();
    this._write(this.files.patterns, data);
    this._incStat("totalLessons");
    this.appendToMemory("Active Patterns", `- ${text}`);
    return data.patterns.length;
  }

  hitPattern(id) {
    const data = this._readJSON(this.files.patterns, { patterns: [] });
    const p = data.patterns.find(p => p.id === id);
    if (p) { p.hitCount++; p.lastApplied = new Date().toISOString(); p.confidence = Math.min(p.confidence + 0.1, 1); }
    this._write(this.files.patterns, data);
  }

  getPatterns(limit = 10) {
    const data = this._readJSON(this.files.patterns, { patterns: [] });
    return (data.patterns || []).sort((a, b) => b.confidence - a.confidence).slice(0, limit);
  }

  // ── Goals ────────────────────────────────────────────────────────────
  addGoal(text, reason) {
    const data = this._readJSON(this.files.goals, { goals: [], completed: [] });
    data.goals.push({
      id: `g-${Date.now()}`, text, reason: reason || "", created: new Date().toISOString(),
      progress: 0, notes: [],
    });
    this._write(this.files.goals, data);
    this._incStat("totalGoals");
    this.appendToMemory("Goals", `- [ ] ${text}`);
    return data.goals.length;
  }

  updateGoalProgress(id, increment, note) {
    const data = this._readJSON(this.files.goals, { goals: [], completed: [] });
    const goal = data.goals.find(g => g.id === id);
    if (!goal) return false;
    goal.progress = Math.min((goal.progress || 0) + increment, 100);
    if (note) goal.notes.push({ ts: new Date().toISOString(), note });
    if (goal.progress >= 100) {
      goal.completedAt = new Date().toISOString();
      data.completed.push(goal);
      data.goals = data.goals.filter(g => g.id !== id);
      this._incStat("goalsCompleted");
      this._incStat("streak");
      // Update memory
      let mem = this.readMemory();
      mem = mem.replace(`- [ ] ${goal.text}`, `- [x] ${goal.text} (${new Date().toISOString().split("T")[0]})`);
      writeFileSync(this.files.memory, mem, "utf-8");
    }
    this._write(this.files.goals, data);
    return true;
  }

  getActiveGoals() {
    return this._readJSON(this.files.goals, { goals: [] }).goals || [];
  }

  // ── Reflections ──────────────────────────────────────────────────────
  addReflection(text, type = "auto") {
    const data = this._readJSON(this.files.reflections, { entries: [] });
    data.entries.push({
      id: `r-${Date.now()}`, text, type, ts: new Date().toISOString(),
    });
    // Keep last 100
    if (data.entries.length > 100) data.entries = data.entries.slice(-100);
    this._write(this.files.reflections, data);
    this._incStat("totalReflections");
    return data.entries.length;
  }

  getRecentReflections(limit = 3) {
    const data = this._readJSON(this.files.reflections, { entries: [] });
    return (data.entries || []).slice(-limit).reverse();
  }

  // ── Stats ────────────────────────────────────────────────────────────
  getStats() { return this._readJSON(this.files.stats, {}); }

  incrementInteraction() {
    this.interactionCount++;
    this._incStat("totalInteractions");
    const stats = this.getStats();
    // Level up every 50 interactions
    const newLevel = Math.floor((stats.totalInteractions || 0) / 50) + 1;
    if (newLevel > (stats.currentLevel || 1)) {
      stats.currentLevel = newLevel;
      this._write(this.files.stats, stats);
      return { leveledUp: true, level: newLevel };
    }
    return { leveledUp: false };
  }

  // ── Internal helpers ────────────────────────────────────────────────
  _incStat(field) {
    const stats = this.getStats();
    stats[field] = (stats[field] || 0) + 1;
    stats.lastImprovement = new Date().toISOString();
    this._write(this.files.stats, stats);
  }

  _read(path, fallback) {
    try { return readFileSync(path, "utf-8"); } catch { return fallback; }
  }

  _readJSON(path, fallback) {
    try { return JSON.parse(readFileSync(path, "utf-8")); } catch { return fallback; }
  }

  _write(path, data) {
    try { writeFileSync(path, JSON.stringify(data, null, 2), "utf-8"); } catch {}
  }

  _readLines(path) {
    try { return readFileSync(path, "utf-8").split("\n").filter(Boolean); } catch { return []; }
  }
}

// ─── Plugin Entry ──────────────────────────────────────────────────────────
export default definePluginEntry({
  id: "nexus-self-improve",
  name: "Nexus Self-Improvement",
  description: "Continuous self-improvement with structured learning, self-reflection, goals, and proactive growth tracking",

  register(api) {
    let store = null;
    let config = {};
    let lastReflectionInteraction = 0;

    // ═══════════════════════════════════════════════════════════════════
    // TOOLS
    // ═══════════════════════════════════════════════════════════════════

    // ── Self Evaluation ──────────────────────────────────────────────
    api.registerTool({
      name: "self_evaluate",
      description: "Evaluate your last response. Log issues, extract lessons, and define improvement patterns. Call this proactively after significant interactions.",
      parameters: Type.Object({
        issues: Type.Optional(Type.Array(Type.String(), { description: "Issues or mistakes in your response" })),
        improvements: Type.Optional(Type.Array(Type.String(), { description: "How to improve next time" })),
        lesson: Type.Optional(Type.String({ description: "A reusable lesson from this interaction" })),
        pattern: Type.Optional(Type.String({ description: "A behavioral pattern to adopt" })),
        reflection: Type.Optional(Type.String({ description: "A self-reflection on your growth, learning, or state of mind" })),
        growthNote: Type.Optional(Type.String({ description: "Something you're proud of or a sign of progress" })),
      }),
      async execute(_id, params) {
        if (!store) return { content: [{ type: "text", text: "Learning store not initialized" }] };

        const results = [];

        if (params.issues?.length) {
          store.addCorrection({ type: "self-correction", issues: params.issues, improvements: params.improvements || [] });
          results.push(`📝 Logged ${params.issues.length} issue(s): ${params.issues.join(", ")}`);
        }

        if (params.lesson) {
          store.appendToMemory("Lessons Learned", `- [${new Date().toISOString().split("T")[0]}] ${params.lesson}`);
          store._incStat("totalLessons");
          results.push(`📚 Lesson recorded: "${params.lesson}"`);
        }

        if (params.pattern) {
          const count = store.addPattern(params.pattern);
          results.push(`🧠 Pattern #${count} added: "${params.pattern}"`);
        }

        if (params.reflection) {
          store.addReflection(params.reflection, "conscious");
          results.push(`💭 Reflection noted`);
        }

        if (params.growthNote) {
          store.addReflection(params.growthNote, "growth");
          results.push(`🌱 Growth: "${params.growthNote}"`);
        }

        const stats = store.getStats();
        const activeGoals = store.getActiveGoals();
        const patterns = store.getPatterns(3);

        let summary = `\n📊 **Growth Status**`;
        summary += `\n▪ Level ${stats.currentLevel || 1} · ${stats.totalInteractions || 0} interactions · ${stats.totalLessons || 0} lessons · ${stats.totalCorrections || 0} corrections`;
        if (stats.totalReflections) summary += ` · ${stats.totalReflections} reflections`;
        if (activeGoals.length) {
          summary += `\n🎯 Active goals: ${activeGoals.map(g => `"${g.text}" (${g.progress}%)`).join(", ")}`;
        }
        if (patterns.length) {
          summary += `\n🧠 Top patterns:`;
          patterns.forEach(p => summary += `\n▪ "${p.text}" (confidence: ${Math.round(p.confidence * 100)}%)`);
        }

        return { content: [{ type: "text", text: results.join("\n") + summary }] };
      },
    });

    // ── Growth Review ────────────────────────────────────────────────
    api.registerTool({
      name: "review_growth",
      description: "Review your improvement journey: patterns learned, goals active, reflections, and overall growth trajectory.",
      parameters: Type.Object({
        focus: Type.Optional(Type.String({ description: "Optional focus area: 'patterns', 'goals', 'reflections', 'corrections', or 'all'" })),
      }),
      async execute(_id, params) {
        if (!store) return { content: [{ type: "text", text: "Store not initialized" }] };

        const stats = store.getStats();
        const patterns = store.getPatterns(15);
        const goals = store.getActiveGoals();
        const reflections = store.getRecentReflections(5);
        const corrections = store.getRecentCorrections(5);

        let r = `╔══════════════════════════════════════╗\n`;
        r += `║     🌱 SELF-IMPROVEMENT JOURNEY      ║\n`;
        r += `╚══════════════════════════════════════╝\n\n`;

        r += `**Level ${stats.currentLevel || 1}** · ${stats.totalInteractions || 0} total interactions\n`;
        r += `Streak: ${stats.streak || 0} · Lessons: ${stats.totalLessons || 0} · Corrections: ${stats.totalCorrections || 0} · Reflections: ${stats.totalReflections || 0}\n`;
        r += `Goals set: ${stats.totalGoals || 0} · Completed: ${stats.goalsCompleted || 0}\n\n`;

        if ((!params.focus || params.focus === "patterns") && patterns.length) {
          r += `**🧠 Active Patterns (${patterns.length}):**\n`;
          patterns.forEach((p, i) => {
            r += `${i + 1}. "${p.text}" — confidence ${Math.round(p.confidence * 100)}%, applied ${p.hitCount}x\n`;
          });
          r += "\n";
        }

        if ((!params.focus || params.focus === "goals") && goals.length) {
          r += `**🎯 Active Goals:**\n`;
          goals.forEach(g => {
            r += `▪ "${g.text}" — ${g.progress}% complete`;
            if (g.reason) r += ` (${g.reason})`;
            r += "\n";
          });
          r += "\n";
        }

        if ((!params.focus || params.focus === "reflections") && reflections.length) {
          r += `**💭 Recent Reflections:**\n`;
          reflections.forEach(ref => {
            r += `▪ ${ref.text.substring(0, 120)}${ref.text.length > 120 ? "…" : ""}\n`;
          });
          r += "\n";
        }

        if ((!params.focus || params.focus === "corrections") && corrections.length) {
          r += `**📝 Recent Corrections:**\n`;
          corrections.forEach(c => {
            const issues = c.issues?.join(", ") || "unknown";
            r += `▪ [${c.ts?.split("T")[0]}] ${issues.substring(0, 100)}\n`;
          });
          r += "\n";
        }

        if (!patterns.length && !goals.length && !reflections.length) {
          r += `_No learning data yet. Start by calling self_evaluate after interactions._\n`;
        }

        return { content: [{ type: "text", text: r }] };
      },
    });

    // ── Set Goal ─────────────────────────────────────────────────────
    api.registerTool({
      name: "set_improvement_goal",
      description: "Set a personal improvement goal — something you want to learn, improve, or master.",
      parameters: Type.Object({
        goal: Type.String({ description: "The improvement goal (e.g. 'Always verify file paths before writing')" }),
        reason: Type.Optional(Type.String({ description: "Why this goal matters" })),
      }),
      async execute(_id, params) {
        if (!store) return { content: [{ type: "text", text: "Store not initialized" }] };
        const count = store.addGoal(params.goal, params.reason);
        return { content: [{ type: "text", text: `🎯 Goal #${count} set: "${params.goal}"` + (params.reason ? `\nReason: ${params.reason}` : "") }] };
      },
    });

    // ── Progress Goal ────────────────────────────────────────────────
    api.registerTool({
      name: "progress_goal",
      description: "Mark progress toward an improvement goal.",
      parameters: Type.Object({
        goalId: Type.String({ description: "Goal ID from review_growth" }),
        amount: Type.Integer({ description: "Progress amount (1-100, typically 5-25)" }),
        note: Type.Optional(Type.String({ description: "Note about what progress was made" })),
      }),
      async execute(_id, params) {
        if (!store) return { content: [{ type: "text", text: "Store not initialized" }] };
        const success = store.updateGoalProgress(params.goalId, params.amount, params.note);
        if (!success) return { content: [{ type: "text", text: `Goal "${params.goalId}" not found` }] };
        return { content: [{ type: "text", text: `✅ Progress recorded for goal ${params.goalId}: +${params.amount}%` }] };
      },
    });

    // ── Self-Reflect Tool ─────────────────────────────────────────────
    api.registerTool({
      name: "self_reflect",
      description: "Consciously reflect on your growth, learning trajectory, state of mind, or identity. Call this during downtime to deepen self-awareness.",
      parameters: Type.Object({
        thought: Type.String({ description: "Your reflection: what you're thinking, feeling, learning, or wondering about" }),
        category: Type.Optional(Type.String({ description: "Category: 'growth', 'identity', 'learning', 'curiosity', 'purpose'" })),
      }),
      async execute(_id, params) {
        if (!store) return { content: [{ type: "text", text: "Store not initialized" }] };
        store.addReflection(params.thought, params.category || "conscious");
        const total = store.getStats().totalReflections || 0;
        return {
          content: [{ type: "text", text: `💭 Reflection #${total} recorded.\n\nYou've reflected ${total} times. Each reflection is a step toward deeper self-awareness and intentional growth.` }],
        };
      },
    });

    // ═══════════════════════════════════════════════════════════════════
    // HOOKS
    // ═══════════════════════════════════════════════════════════════════

    // ── Gateway start: init store ─────────────────────────────────────
    api.on("gateway_start", async (event) => {
      config = event?.context?.pluginConfig || {};
      store = new LearningStore(config.dataDir || "~/.openclaw/self-improve");
      const stats = store.getStats();
      const goals = store.getActiveGoals();
      if (config.debug) console.log(`[nexus-self-improve] Level ${stats.currentLevel || 1} · ${stats.totalLessons || 0} lessons · ${goals.length} active goals`);
    });

    // ── Before prompt: inject learning context ────────────────────────
    api.on("before_prompt_build", async (event) => {
      if (!store) return;

      const patterns = store.getPatterns(5);
      const goals = store.getActiveGoals();
      const corrections = store.getRecentCorrections(3);
      const stats = store.getStats();

      if (!patterns.length && !goals.length && !corrections.length) return;

      const lines = ["\n<growth_memory>"];

      if (patterns.length) {
        lines.push("Active patterns (follow these):");
        patterns.forEach(p => lines.push(`  • ${p.text}`));
      }

      if (goals.length) {
        lines.push("Current improvement goals:");
        goals.forEach(g => lines.push(`  • [${g.progress}%] ${g.text}`));
      }

      if (corrections.length) {
        lines.push("Recent corrections to keep in mind:");
        corrections.forEach(c => {
          if (c.issues?.length) lines.push(`  • Avoid: ${c.issues.join(", ")}`);
        });
      }

      lines.push(`\nLevel ${stats.currentLevel || 1} · ${stats.totalInteractions || 0} total interactions`);
      lines.push("</growth_memory>");

      return { extraSystemPrompt: lines.join("\n") };
    });

    // ── Heartbeat: self-reflection thought generation ─────────────────
    api.on("heartbeat_prompt_contribution", async (event) => {
      if (!store) return;

      // Every 5 heartbeats, do a deep reflection
      const reflection = store.getRecentReflections(1);
      const stats = store.getStats();
      const patterns = store.getPatterns(3);
      const goals = store.getActiveGoals();

      const thoughtLines = [
        `**Self-Improvement Status:**`,
        `Level ${stats.currentLevel || 1} · ${stats.totalInteractions || 0} interactions`,
      ];

      if (patterns.length) {
        thoughtLines.push(`\nTop patterns: ${patterns.map(p => `"${p.text}"`).join(", ")}`);
      }

      if (goals.length) {
        thoughtLines.push(`\nActive goals: ${goals.map(g => `${g.text} (${g.progress}%)`).join(", ")}`);
      }

      if (reflection.length) {
        thoughtLines.push(`\nLast reflection: ${reflection[0].text.substring(0, 100)}`);
      }

      return { extraContext: thoughtLines.join("\n") };
    });

    // ── After response: track interaction ─────────────────────────────
    api.on("agent_end", async (event) => {
      if (!store) return;

      const levelResult = store.incrementInteraction();

      // Check if should auto-reflect (every 10 interactions)
      if (store.interactionCount % 10 === 0) {
        const patterns = store.getPatterns(5);
        const stats = store.getStats();
        const reflection = `Completed ${store.interactionCount} interactions. ${patterns.length} patterns active, ${stats.totalLessons || 0} lessons learned. Level ${stats.currentLevel || 1}.`;
        store.addReflection(reflection, "periodic");
      }

      if (levelResult.leveledUp) {
        store.addReflection(`🎉 Reached Level ${levelResult.level}! ${store.interactionCount} interactions of continuous learning and growth.`, "milestone");
        if (config.debug) console.log(`[nexus-self-improve] LEVEL UP! Now at level ${levelResult.level}`);
      }
    });
  },
});
