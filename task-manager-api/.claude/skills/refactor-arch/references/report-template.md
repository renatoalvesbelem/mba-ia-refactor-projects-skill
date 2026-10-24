# Audit report template (Phase 2)

The report is printed to the user and then written to a Markdown file. Both must contain the same text. Keep the labels in English (they match the challenge format) and write descriptions, impacts and recommendations in Brazilian Portuguese.

## Ordering rules

1. Group by severity: CRITICAL, then HIGH, then MEDIUM, then LOW.
2. Inside a severity, order by architectural impact: structural problems (God file, no layering) before security, security before performance, performance before style.
3. Number findings sequentially across the whole report (`#1`, `#2`...). The number is what the Phase 3 summary refers back to.
4. Each finding points to exactly one catalog entry (`AP-xx`) and at least one playbook pattern (`RP-xx`).

## Line references

- Single line: `app.py:7`
- Range: `models.py:133-169`
- Several ranges in one file: `models.py:28, 48-49, 58-60, 68`
- Several files for one finding (only when the files are trivially identical in the problem): one `File:` line per file.

Never write "approximately" or "around line". Open the file and copy the number. The `File:` field accepts only `path:line` references; a description such as "used throughout the file" is not accepted. For naming or style findings that repeat many times, list the lines of the first occurrence in each function or loop (`routes/task_routes.py:16, 51, 122`), never a prose summary.

The title of a finding is the catalog entry name exactly as written in `anti-patterns.md` (English), followed by the ID. The description, impact and recommendation are in pt-BR.

## Template

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <directory name>
Stack:   <language> + <framework> <version>
Files:   <N> analyzed | ~<LOC> lines of code
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### #1 [CRITICAL] <Anti-pattern name> (AP-xx)
File: <path:lines>
Description: <o que está no código, em pt-BR, citando identificadores reais>
Impact: <por que isso importa neste projeto, em pt-BR>
Recommendation: <o que fazer, em pt-BR, terminando com a referência ao playbook, ex.: "Ver RP-02.">

### #2 [CRITICAL] ...

...

## Deprecated APIs
| API | File:line | Status | Modern equivalent |
|-----|-----------|--------|-------------------|
| <call> | <path:line> | <deprecated since / removed in> | <replacement> |

(or the sentence: "Nenhuma API deprecated encontrada para esta stack.")

## Proposed target structure
<tree of the layout Phase 3 will build, adapted to what already exists; do not list modules that Phase 3 will delete as dead code (AP-21), list them under "Removed" below the tree instead>

## Contract decisions preview
<endpoints whose behaviour will change for security reasons and how; or "Nenhuma mudança de contrato prevista.">

================================
Total: <N> findings
================================
```

After the closing line, ask the Phase 3 question from SKILL.md. Nothing else goes between the report and the question.

## Quality checklist before printing

- [ ] every finding has file and line copied from the source
- [ ] severity matches the catalog entry (do not promote or demote without saying why in the description)
- [ ] the Summary counts match the number of findings per severity
- [ ] `Total:` equals the sum of the Summary
- [ ] at least one finding exists per severity level when the code justifies it; do not pad with weak findings to fill a level
- [ ] the deprecated API section is present even when empty
- [ ] the target structure keeps existing folder names that already follow the pattern and does not list modules that will be removed as dead code
- [ ] the `File:` field of every finding contains only `path:line` references
- [ ] titles use the catalog names in English
