#!/usr/bin/env node
// Forwards a Claude Code hook event to `python -m kaizen hook`.
// Node ships with Claude Code; Python's launcher name varies by platform, so try each.
// Exit code and stderr pass straight through: exit 2 blocks (PreToolUse) or sends the
// gate's violations back to the agent (PostToolUse).
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const input = readFileSync(0);

for (const py of ["python3", "python", "py"]) {
  const r = spawnSync(py, ["-m", "kaizen", "hook"], { cwd: root, input, encoding: "utf8" });
  if (r.error && r.error.code === "ENOENT") continue;
  if (r.stdout) process.stdout.write(r.stdout);
  if (r.stderr) process.stderr.write(r.stderr);
  process.exit(r.status ?? 1);
}
process.stderr.write("kaizen: no Python interpreter found (tried python3, python, py)\n");
process.exit(1);
