# Anti-pattern catalog (Phase 2)

Each entry has an ID (used in reports), a default severity, detection signals written as things you can grep or see while reading, why it matters, and the playbook pattern that fixes it. Signals are described generically; the "Idioms" row translates them to common stacks. When a signal appears in a stack not listed, apply the generic description.

## Severity scale

| Level | Meaning |
|-------|---------|
| **CRITICAL** | Breaks correctness or security, exposes sensitive data, or there is no separation of responsibilities at all (database, business rules and routing in one unit). |
| **HIGH** | Strong MVC / SOLID violation that makes the code hard to change and test: heavy logic in route handlers, no dependency injection, global mutable state, unstructured control flow. |
| **MEDIUM** | Standardisation, duplication, moderate performance problems (N+1), missing validation, swallowed errors, deprecated APIs. |
| **LOW** | Readability: naming, magic numbers, dead code, print-based logging, verbose constructs. |

A finding may be promoted one level when the context makes it worse (an injectable query on a login endpoint stays CRITICAL; an unused import stays LOW; a `debug=True` on a public host goes from HIGH to CRITICAL only when combined with the debugger PIN being disabled). Say in the description when you deviate from the default.

---

## CRITICAL

### AP-01 Hardcoded credentials and secrets
- **Signals**: literal strings assigned to names containing `secret`, `key`, `password`, `pass`, `pwd`, `token`, `api_key`, `smtp_user`, `db_user`; connection strings with user and password inline; `pk_live_`, `sk_live_`, `AKIA` prefixes.
- **Idioms**: `app.config["SECRET_KEY"] = "..."`, `const config = { dbPass: "..." }`, `self.email_password = '...'`, `spring.datasource.password=` in a committed properties file.
- **Why**: anyone with repo access owns the system; rotating a secret needs a deploy; the same value leaks to every environment.
- **Fix**: RP-01 (config module reading environment variables, `.env.example`).

### AP-02 SQL injection (string-built queries)
- **Signals**: query text built with `+`, f-strings, `%` formatting, template literals or `.format(` and user input in the pieces; `execute(` / `db.run(` / `db.get(` receiving a single argument that was concatenated; `LIKE '%" + termo + "%'`.
- **Idioms**: `cursor.execute("SELECT * FROM t WHERE id = " + str(id))`, `` db.all(`SELECT ... WHERE email = '${email}'`) ``, `Statement.execute("..." + input)`.
- **Why**: login bypass, data exfiltration, data destruction. Also hides type errors (a string price goes straight into the SQL).
- **Fix**: RP-02 (parameterised queries / ORM expressions).

### AP-03 God file / God class
- **Signals**: a single file or class covering three or more responsibilities from the responsibility map (routing, validation, business rules, data access, serialization, config, cross-cutting) for more than one domain entity; files above ~250 lines mixing SQL and HTTP; a `Manager` / `Handler` / `Service` class that builds the DB, registers routes and implements them.
- **Idioms**: `models.py` with SQL + stock rules + report maths for four entities; `AppManager.setupRoutes(app)` containing every handler body; a single `main.go` with handlers and queries.
- **Why**: nothing can be tested in isolation, every change touches the same file, merge conflicts, no reuse.
- **Severity rule**: CRITICAL when the file mixes the database setup or raw persistence with routing and business rules (the classic monolith). When the project already separates `models/` and `routes/` and the database lives in its own module, the concentration happens inside one layer (fat route modules), so classify it as HIGH and say in the description why it was not CRITICAL. When AP-07 also applies to the same handlers, keep both findings but make the AP-07 description point to the specific rules trapped in the handler instead of repeating the AP-03 description.
- **Fix**: RP-03 (split per layer and per domain).

### AP-04 Sensitive data exposure in responses or logs
- **Signals**: password or hash fields included in serializers (`"senha": row["senha"]`, `'password': self.password` in `to_dict`); secrets, debug flags, DB paths or environment names returned by a health or info endpoint; card numbers, tokens or passwords written to logs (`console.log(... card ...)`, `print(... senha ...)`).
- **Idioms**: `/health` returning `secret_key`, `GET /usuarios` returning `senha`, `console.log(\`Processando cartão ${cc}\`)`.
- **Why**: direct credential leak to any API consumer and to log storage; often a compliance violation (PCI for card data).
- **Fix**: RP-09 (whitelist serializers, redact logs).

### AP-05 Plaintext or weak password storage
- **Signals**: passwords inserted as received; equality comparison between stored and submitted password; `md5(`, `sha1(` applied to passwords without salt; home-made "crypto" functions (loops over base64, XOR, substring).
- **Idioms**: `WHERE email = ? AND senha = ?`, `hashlib.md5(pwd.encode())`, `function badCrypto(pwd)`.
- **Why**: a DB dump equals every user's password; MD5/SHA1 are brute-forced in seconds; home-made schemes are usually reversible.
- **Fix**: RP-09 (bcrypt / scrypt / argon2 via the platform library: `werkzeug.security`, `bcrypt`, `BCryptPasswordEncoder`).

### AP-06 Unprotected dangerous endpoint
- **Signals**: a route that executes SQL received from the request; a route that truncates or resets tables; destructive operations (`DELETE`, reset, bulk update) without authentication or authorization check; admin paths (`/admin/...`) with no guard.
- **Idioms**: `cursor.execute(dados.get("sql"))`, `POST /admin/reset-db` deleting every table, `DELETE /api/users/:id` open to anyone.
- **Why**: remote data destruction or exfiltration by anyone who can reach the host.
- **Fix**: RP-13 (auth guard middleware from config, remove arbitrary execution, keep the route registered so the contract is explicit).

---

## HIGH

### AP-07 Business logic inside route handlers (fat controllers)
- **Signals**: handler functions longer than ~30 lines; validation chains (`if not x: return 400`) followed by persistence inside the same function; status transitions, totals, discounts, stock arithmetic, date maths or permission checks next to `request` / `req` / `res` usage; the route layer importing the DB object or ORM session directly.
- **Idioms**: a Flask blueprint function that validates, queries `User.query.get`, builds the entity and commits; an Express handler that reads `req.body`, charges a card and inserts three rows.
- **Why**: the rules can only be exercised through HTTP, cannot be reused by jobs or CLIs, and every handler re-implements them slightly differently.
- **Fix**: RP-04 (thin routes, controllers orchestrate, models own rules), RP-16 (validation layer).

### AP-08 Global mutable state
- **Signals**: module-level variables reassigned at runtime (`global x`), singletons created at import time and mutated by requests, in-memory caches or counters on the module (`let globalCache = {}`, `let totalRevenue = 0`), instance lists that grow forever (`self.notifications = []`), a DB connection stored in a module global with `check_same_thread=False`.
- **Idioms**: `db_connection = None` + `global db_connection`, `module.exports = { globalCache }`, a class attribute used as a cache.
- **Why**: hidden coupling between requests, impossible to test in isolation, memory leaks, race conditions under concurrency.
- **Fix**: RP-05 (inject dependencies, scope state to request or app), RP-12 for log-ish state.

### AP-09 Tight coupling / no dependency injection
- **Signals**: a class instantiating its own infrastructure in the constructor (`this.db = new sqlite3.Database(...)`); modules importing a concrete DB object instead of receiving it; the composition (create app, create DB, register routes) spread across several files; controllers importing models and the DB module directly so nothing can be substituted.
- **Idioms**: `from database import get_db` inside controllers; `const manager = new AppManager(); manager.initDb(); manager.setupRoutes(app)` with no way to pass a different DB.
- **Why**: no unit test can run without a real database; swapping storage or adding a cache means editing every consumer.
- **Fix**: RP-05 (composition root, constructor / factory injection, app factory).

### AP-10 Unstructured asynchronous flow (callback pyramid)
- **Signals**: callbacks nested three or more levels; manual completion counters (`pending--; if (pending === 0) res.json(...)`); `function(err)` with `this.lastID` captured through `self = this`; a response that can be sent from several nested places; errors ignored in inner callbacks (`(err) => { ... }` that never checks `err`).
- **Idioms**: Node `sqlite3` callback API inside Express handlers; promise chains with `.then` inside `.then`.
- **Why**: double responses, hanging requests when a branch forgets to answer, errors silently dropped, impossible to reason about transactions.
- **Fix**: RP-07 (promisify the driver, `async/await`, single return path, error middleware).

### AP-11 Insecure runtime defaults
- **Signals**: `debug=True` / `app.config["DEBUG"] = True` in the entry point; `CORS(app)` or `cors()` with no origin restriction; `host="0.0.0.0"` combined with debug; stack traces returned to clients (`str(e)` in the response body); default ports and hosts hardcoded.
- **Idioms**: `app.run(host="0.0.0.0", port=5000, debug=True)`, `return jsonify({"erro": str(e)}), 500`.
- **Why**: the Werkzeug debugger allows remote code execution; open CORS plus credentials equals CSRF; stack traces reveal internals.
- **Fix**: RP-01 (debug and CORS from config), RP-06 (central error handler that hides internals).

### AP-12 Missing transaction and data integrity
- **Signals**: several dependent `INSERT`/`UPDATE` statements with a single `commit()` at the end but early `return` paths in between; writes with no transaction at all in callback-based code; deletes that leave child rows behind (no `ON DELETE CASCADE`, no explicit cleanup); tables without foreign keys, `NOT NULL` or `UNIQUE` where the domain requires them; stock decremented after the order row was inserted without checking the result.
- **Idioms**: `criar_pedido` inserting order, items and updating stock without `BEGIN`; `DELETE FROM users WHERE id = ?` leaving enrollments and payments orphaned; `email TEXT` without `UNIQUE`.
- **Why**: partial writes on error, duplicated accounts, orphaned records that corrupt reports.
- **Fix**: RP-14 (transaction wrapper), schema constraints in the model layer.

---

## MEDIUM

### AP-13 N+1 queries
- **Signals**: a query inside a `for` / `forEach` / `map` over the result of another query; per-row lookups by id (`Model.query.get(row.fk)` inside a loop); nested cursors (`cursor2`, `cursor3`); counting with one query per status value (`filter_by(status='a').count()`, then `'b'`, then `'c'`); loading all rows to count in Python/JS what SQL could aggregate.
- **Idioms**: `for row in pedidos: cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = ...")`, `courses.forEach(c => db.all("SELECT * FROM enrollments WHERE course_id = ?"...))`, `User.query.get(t.user_id)` inside `for t in tasks`.
- **Why**: response time grows linearly with data; the DB is hit hundreds of times for one page.
- **Fix**: RP-08 (JOIN / eager loading / `GROUP BY`).

### AP-14 Duplicated code
- **Signals**: the same block (3+ lines) in two or more places: hand-built dict serializers repeated per query function; identical validation chains in create and update handlers; the same date/overdue calculation in several routes; copy-pasted query functions differing only by a `WHERE`.
- **Idioms**: eight identical `result.append({"id": row["id"], ...})` blocks; `overdue` computed in six handlers although the model has `is_overdue()`.
- **Why**: fixes have to be applied N times, behaviour drifts between copies.
- **Fix**: RP-15 (extract serializer / validator / model method, reuse it).

### AP-15 Missing or inconsistent input validation
- **Signals**: request fields used without type or range checks (`preco < 0` on a value that may be a string); `request.get_json()` result used without a `None` check; ids from the URL cast with `int(` inside the handler with no error handling; different rules for the same field in create vs update; validation libraries listed in the manifest but never imported (`marshmallow`, `pydantic`, `joi`, `zod`, `express-validator`).
- **Idioms**: `dados["preco"]` compared with `<` and later concatenated into SQL; `tasks.filter(Task.priority == int(priority))` with no `try`.
- **Why**: 500s instead of 400s, invalid data persisted, injection surface.
- **Fix**: RP-16 (schema or validator module used by the controller).

### AP-16 Generic exception handling and error leakage
- **Signals**: bare `except:` or `except Exception as e` returning `str(e)` to the client; try/except around every handler body copied verbatim; `err` parameters never checked in callbacks; `rollback()` repeated in every handler; no global error handler registered.
- **Idioms**: `except: return jsonify({'error': 'Erro interno'}), 500` on a listing endpoint; `(err) => { res.send("...") }` ignoring `err`.
- **Why**: real errors are hidden, debugging needs reproduction, internals leak when `str(e)` is returned.
- **Fix**: RP-06 (custom exception types + one error handler / error middleware).

### AP-17 Cross-cutting side effects inside handlers
- **Signals**: notifications, emails, SMS, cache writes, audit logging or file writes performed inline in a route or model function (`print("ENVIANDO EMAIL...")`, `logAndCache(`, `smtplib` usage next to request handling); a notification service that also stores state; the same handler persisting and notifying.
- **Why**: the handler owns too many reasons to change; side effects cannot be disabled in tests; failures in the side effect break the main flow.
- **Fix**: RP-04 (move to a service invoked by the controller), RP-12 (logging instead of prints).

### AP-18 Deprecated API usage
- **Signals**: calls listed in the table below, or any call that the runtime flags with a deprecation warning when the app boots (`DeprecationWarning`, `LegacyAPIWarning`, `[DEP0xxx]`). Always check the warnings printed during Phase 3.1 baseline boot and during Phase 1 if you run the app.
- **Why**: breaks on the next major upgrade; the replacement usually fixes a real problem (timezone-naive datetimes, legacy query semantics, security defaults).
- **Fix**: RP-10.

| Ecosystem | Deprecated / legacy | Since | Modern equivalent |
|-----------|---------------------|-------|-------------------|
| Python | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | 3.12 (DeprecationWarning) | `datetime.now(timezone.utc)` |
| Python | `sqlite3` default datetime adapters/converters | 3.12 | register explicit adapters or store ISO strings |
| Python | `cgi`, `imp`, `distutils`, `asynchat`, `asyncore` modules | 3.11-3.12 (removed 3.12/3.13) | `email`, `importlib`, `setuptools`, `asyncio` |
| Python | `asyncio.get_event_loop()` outside a running loop | 3.10-3.12 | `asyncio.run()` / `asyncio.get_running_loop()` |
| Python | `logging.warn()` | 3.3 | `logging.warning()` |
| Python | `unittest.assertEquals`, `assertDictContainsSubset` | 3.2 / 3.12 | `assertEqual`, explicit comparisons |
| SQLAlchemy | `Model.query.get(id)`, `Query.get()` | 2.0 (LegacyAPIWarning) | `db.session.get(Model, id)` |
| SQLAlchemy | `backref=` on relationships | 2.0 (legacy, still works) | `back_populates=` on both sides |
| SQLAlchemy | `declarative_base()` from `sqlalchemy.ext.declarative` | 2.0 | `sqlalchemy.orm.declarative_base` / `DeclarativeBase` |
| SQLAlchemy | `session.execute("raw sql")` with a plain string | 1.4/2.0 | `text("...")` with bound params |
| Flask | `flask.json.JSONEncoder` subclassing | 2.3 (removed) | `app.json` provider |
| Flask | `@app.before_first_request` | 2.3 (removed) | run setup in the app factory or a CLI command |
| Flask | `flask.escape`, `flask.Markup` | 2.3 (removed) | `markupsafe.escape`, `markupsafe.Markup` |
| Werkzeug | `werkzeug.urls.url_quote`, `url_encode` | 2.3 (removed 3.0) | `urllib.parse.quote`, `urlencode` |
| Node | `new Buffer(...)` | v6 (DEP0005) | `Buffer.from()`, `Buffer.alloc()` |
| Node | `url.parse()` | v11 (DEP0116, legacy) | `new URL()` |
| Node | `fs.exists()` | v1 (DEP0044) | `fs.access()` / `fs.promises.access()` |
| Node | `process.binding()` | DEP0111 | public APIs |
| Node | callback-only `sqlite3` package driving request handlers | legacy style (not formally deprecated) | `node:sqlite` (Node 22+), `better-sqlite3`, or wrap in `util.promisify` / a small promise adapter |
| JavaScript | `String.prototype.substr()` | Annex B (legacy) | `substring()` / `slice()` |
| JavaScript | `escape()` / `unescape()` | Annex B | `encodeURIComponent()` / `decodeURIComponent()` |
| Express 4 | `res.send(statusCode)`, `res.json(obj, status)` | 4.x deprecated | `res.sendStatus(code)`, `res.status(code).json(obj)` |
| Express 4 | `app.del()`, `req.param()`, `res.sendfile()` | 4.x deprecated | `app.delete()`, `req.params`/`req.query`/`req.body`, `res.sendFile()` |
| Express 4 | `bodyParser.json()` from the `body-parser` package | 4.16+ | `express.json()` |
| Express 4 -> 5 | wildcard routes `'*'`, `app.router`, `req.host` | 5.0 | `'/{*splat}'`, removed, `req.hostname` |
| Java | `new Date()` / `Calendar` for business dates | Java 8 | `java.time` |
| Java | `Thread.stop()`, `Runtime.exec(String)` | 17-18 | `ExecutorService`, `ProcessBuilder` |
| Spring | `WebSecurityConfigurerAdapter` | Spring Security 5.7 | `SecurityFilterChain` bean |
| Spring | `@Autowired` on fields | not deprecated, discouraged | constructor injection |
| Go | `ioutil.ReadAll`, `ioutil.ReadFile` | Go 1.16 | `io.ReadAll`, `os.ReadFile` |
| Ruby/Rails | `update_attributes`, `before_filter` | Rails 5/6 | `update`, `before_action` |

When the stack is not in the table, boot the app and read the warnings; also grep for `deprecated` inside the dependency changelogs in the vendor directory if available.

---

## LOW

### AP-19 Magic numbers and inline literal lists
- **Signals**: numeric thresholds without a name (`> 10000`, `* 0.1`, `range(10000)`, `len(x) < 3`, `< 1 or > 5`); lists of allowed values written inline in handlers (`["pendente", "aprovado", ...]`, `['user', 'admin', 'manager']`) especially when the same list appears more than once or when a constants module already exists but is not used (`VALID_STATUSES` defined in `utils/helpers.py` and ignored by routes).
- **Why**: rule changes need a hunt through the code; copies drift.
- **Fix**: RP-11 (constants / enums in the model layer).

### AP-20 Poor naming
- **Signals**: one or two letter variables outside tiny lambdas (`u`, `e`, `p`, `cc`, `cid`); abbreviated request field names that do not match the domain (`usr`, `eml`, `pwd`, `c_id`); numbered variables (`cursor2`, `cursor3`); functions named after what they do technically rather than the use case (`badCrypto`, `logAndCache`, `process_task_data`); a class called `AppManager` or `Utils` with no cohesive meaning; a blueprint named `reports` that also serves `/categories`.
- **Why**: reading cost, wrong assumptions, harder reviews.
- **Fix**: RP-15 / RP-03 (rename while extracting). Request field names that are part of the public contract stay as they are unless a contract decision says otherwise; rename only internal identifiers.

### AP-21 Dead code and unused imports
- **Signals**: imports never referenced in the module (`import os, sys, json, time` with no usage; `import sqlite3` in a module that only calls `get_db()`); helper functions never called anywhere in the project (`validate_email`, `generate_id`, `process_task_data` defined and unused); exported values nobody reads (`totalRevenue`); empty `__init__.py` that could expose the package API.
- **Why**: misleads readers into thinking the code is used; linters stay red; import time grows.
- **Fix**: remove, or wire the helper in where the duplicated logic lives (RP-15).

### AP-22 Print-based logging
- **Signals**: `print(` / `console.log(` used for operational messages (startup banner, "Produto criado", errors in `except`); no logger configured; log messages built with string concatenation containing user data.
- **Why**: no levels, no timestamps, no destination control, cannot be silenced in tests, sensitive data ends up in stdout.
- **Fix**: RP-12 (standard logging with a module-level logger).

### AP-23 Verbose or deeply nested constructs
- **Signals**: `if cond: return True else: return False`; four-level `if` chains to compute a boolean; `x = x + 1` for counters; `type(v) == list` instead of `isinstance`; manual dict building key by key where a comprehension or serializer fits; `try/except` wrapping a whole function with a `return 500` at the end.
- **Why**: readability; usually hides duplicated logic (AP-14).
- **Fix**: RP-15 (simplify while extracting), RP-16 for validation chains.

---

## Quick scan cheat sheet

Run these first; they surface most textual signals in one pass. Adapt the file glob to the stack.

```
grep -rnE "(secret|password|passw|pwd|api_?key|token)\s*[:=]\s*['\"]" --include=*.py --include=*.js --include=*.ts .
grep -rnE "execute\(|\.run\(|\.get\(|\.all\(" --include=*.py --include=*.js . | grep -E "\+|f\"|f'|\\$\{|%s|\.format\("
grep -rnE "debug\s*=\s*True|DEBUG.*True|0\.0\.0\.0|CORS\(app\)|cors\(\)" .
grep -rnE "^\s*global |^let |^var |check_same_thread" --include=*.py --include=*.js .
grep -rnE "print\(|console\.log\(" --include=*.py --include=*.js . | wc -l
grep -rnE "except\s*:|except Exception|str\(e\)" --include=*.py .
grep -rnE "utcnow\(|\.query\.get\(|backref=|new Buffer\(|url\.parse\(|substr\(|res\.send\([0-9]" .
grep -rnE "^(import|from) " --include=*.py . 
```

The structural signals (God file, fat controllers, N+1, duplication, callback depth, missing transactions) only show up by reading; the cheat sheet does not replace the full read required by SKILL.md.
