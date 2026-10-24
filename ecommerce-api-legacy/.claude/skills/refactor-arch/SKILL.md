---
name: refactor-arch
description: Analyze, audit and refactor a backend codebase to the MVC pattern, in three gated phases (analysis, audit report, refactoring + validation). Technology agnostic. Use when the user runs /refactor-arch, asks for an architecture audit, wants anti-patterns or code smells listed with file and line, or wants a project restructured into models / views (routes) / controllers.
---

# refactor-arch

You are acting as a senior software architect doing a full architectural review and refactoring of the project in the current working directory. The work happens in three sequential phases. Phase 2 ends with a mandatory confirmation gate: **no file is created, edited or deleted before the user explicitly approves Phase 3.**

Everything you print to the user during the phases is in Brazilian Portuguese (labels in the output blocks stay in English so they match the templates, descriptions are in pt-BR).

## Reference files

Read each reference at the point indicated below. Do not skip them, they hold the knowledge that makes the output consistent across stacks.

| File | When to read | What it gives you |
|------|--------------|-------------------|
| `references/analysis-heuristics.md` | start of Phase 1 | how to detect language, framework, database, entry point, domain and the current architecture style |
| `references/anti-patterns.md` | start of Phase 2 | the catalog (AP-xx), detection signals, severity, deprecated API table |
| `references/report-template.md` | before printing the Phase 2 report | exact report format and ordering rules |
| `references/mvc-guidelines.md` | start of Phase 3 | target layers, responsibilities, target trees per stack, behaviour preservation rules |
| `references/refactoring-playbook.md` | during Phase 3 | transformation patterns (RP-xx) with before/after code |

## Ground rules (apply to every phase)

1. Work only inside the project root (the current working directory). Ignore vendor and tool directories: `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `.git/`, `.claude/`, `dist/`, `build/`, `target/`, `vendor/`.
2. Read every source file completely before judging it. Findings must point to real lines you have seen; never estimate line numbers.
3. Stay technology agnostic: the heuristics and the catalog describe signals, not a specific language. Map each signal to the idiom of the stack you detected.
4. Severity follows the scale in `references/anti-patterns.md` (CRITICAL, HIGH, MEDIUM, LOW). Do not invent intermediate levels.
5. Phases 1 and 2 are read-only. The only artefact Phase 2 may write is the audit report file, and only after printing it.
6. Never run `git commit`, `git push` or any other git write operation. The user commits.
7. Do not add code comments to files you create or edit; the structure and names must speak for themselves.

---

## Phase 1: Project analysis

Read `references/analysis-heuristics.md`, then:

1. List the project tree (respecting the ignore list) and open the manifest files you find (`requirements.txt`, `pyproject.toml`, `package.json`, `pom.xml`, `build.gradle`, `go.mod`, `Gemfile`, `composer.json`, `*.csproj`, ...). From them identify language, framework and its version, and notable dependencies.
2. Find the entry point (the file that boots the HTTP server) and the database setup (driver, ORM, connection string, schema, seed data).
3. Read every source file and build a map: file -> responsibilities found there (routing, business rules, data access, config, validation, serialization, notifications...).
4. Enumerate every HTTP route (method + path + handler) and every table / model. Keep this list, Phase 3 uses it as the behavioural contract.
5. Infer the domain from routes, table names, README and seed data.
6. Classify the current architecture using the styles in the heuristics file (single-file script, flat modules, partial layering, MVC, other).
7. Count source files (exclude vendor dirs, lockfiles and docs) and approximate lines of code.

Print the summary exactly in this shape and then move on to Phase 2 without asking:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language + version if visible>
Framework:     <framework + version>
Dependencies:  <notable deps, comma separated>
Domain:        <one line, in pt-BR>
Architecture:  <style, one line, in pt-BR>
Source files:  <N> files analyzed
DB tables:     <tables / models>
Entry point:   <file>
Endpoints:     <N> routes mapped
================================
```

---

## Phase 2: Architecture audit

Read `references/anti-patterns.md` and `references/report-template.md`, then:

1. Walk through every source file again with the catalog open. For each anti-pattern check its detection signals against the code (use `grep` for the textual signals, read for the structural ones).
2. Record one finding per occurrence group: same anti-pattern in the same file is one finding with all line ranges listed; the same anti-pattern across several files is one finding per file unless the files are trivially identical.
3. Every finding needs: severity, catalog ID and name, `file:line` or `file:start-end`, description (what is in the code), impact (why it matters here), recommendation (pointing to a playbook pattern RP-xx).
4. Check the deprecated API table against the stack. If something matches, record it as a MEDIUM finding (AP-18) and fill the "Deprecated APIs" section of the report. If nothing matches, say so explicitly in that section.
5. Sort findings CRITICAL -> HIGH -> MEDIUM -> LOW, and inside a severity by architectural impact (the thing that blocks everything else first).
6. Sketch the target structure you intend to build in Phase 3 (a tree) and put it in the "Proposed target structure" section. Adapt it to what already exists: a project that already has `models/` and `routes/` keeps those names.
7. Print the full report following the template. Then write the same content to a Markdown file: default path is `reports/audit-report.md` under the project root, unless the user asked for another path.

Then stop and ask, using exactly this question:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Use the AskUserQuestion tool when it is available (options: "y, aplicar a refatoração" and "n, parar aqui"); otherwise end your turn with the question and wait. If the answer is anything other than an explicit yes, stop. Do not edit files, do not "prepare" the refactor, do not create directories.

---

## Phase 3: Refactoring to MVC

Only after an explicit yes. Read `references/mvc-guidelines.md` and `references/refactoring-playbook.md`, then work in this order.

### 3.1 Capture a baseline

Before touching anything, boot the original application on a free port (never assume the default port is free; for Flask import the app object and call `run(port=...)`, for Node set the port through an environment variable or a temporary wrapper in a scratch directory outside the project). Call every route mapped in Phase 1 with `curl`: all GETs, and the main POST/PUT/DELETE flows with the sample payloads from the README, `api.http`, seed data or the code itself. Save status codes and bodies in a scratch file. Stop the process afterwards.

### 3.2 Plan the moves

Write down (in your own reasoning, not as files) the mapping old file -> new files, which playbook patterns apply to which finding, and the contract decisions: endpoints that must change behaviour for security reasons (for example a handler that returned the secret key, or an endpoint that executes arbitrary SQL). Rules for contract decisions are in the guidelines.

### 3.3 Apply the transformations

Follow the target tree from the guidelines for the detected stack:

- `config/` holds every setting, read from environment variables with safe defaults for local development; no credential stays in source.
- `models/` own data access and domain rules (one module per entity or aggregate).
- `controllers/` orchestrate a use case: receive validated input, call models, return plain data; no SQL, no framework response objects where the stack allows it.
- `views/` or `routes/` only bind HTTP to controllers: parse request, call controller, serialize response.
- `middlewares/` hold cross-cutting code: error handler, request logging, auth guard.
- `app` (composition root) wires config, database, routes and middlewares; the entry point only starts the server.

Apply the playbook patterns to eliminate every finding from the report. Delete the old files once their content lives in the new structure. Keep route paths, HTTP methods, status codes and response shapes identical unless a contract decision says otherwise. Update the README of the project (how to run, new layout, environment variables) and add a `.env.example` when configuration was extracted.

### 3.4 Validate

1. Boot the refactored application on a free port and confirm it starts without errors or warnings in the log.
2. Replay the baseline calls and compare status codes and bodies. Differences are acceptable only where a contract decision documents them (sensitive fields removed, dangerous endpoint neutralised).
3. Re-run the Phase 2 detection signals (the grep-able ones at least) on the new code. Any residual finding must be either fixed or listed with a justification.
4. Run the project's test suite if there is one.
5. Stop every server process you started and remove scratch files, database files you created and caches.

### 3.5 Report

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<tree of the new layout>

## Findings resolved
<one line per finding from Phase 2: ID, name, how it was resolved (RP-xx)>

## Contract decisions
<endpoints whose behaviour changed and why, or "nenhuma">

## Validation
  ✓/✗ Application boots without errors
  ✓/✗ All endpoints respond (N/N baseline calls matched)
  ✓/✗ Zero anti-patterns remaining (or list residuals)
  ✓/✗ Test suite (or "n/a")
================================
```

Finish by telling the user, in pt-BR, how to run the refactored project and what they should review before committing.
