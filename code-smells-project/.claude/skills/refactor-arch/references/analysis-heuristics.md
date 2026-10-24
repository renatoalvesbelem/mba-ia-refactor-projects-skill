# Analysis heuristics (Phase 1)

Goal: describe the project as it is, with evidence, before judging it. Every value printed in the Phase 1 block must come from a file you opened.

## 1. Language and framework

Look for manifest files at the project root first, then one level down (`src/`, `app/`, `backend/`).

| Manifest | Language | Where the framework shows up |
|----------|----------|------------------------------|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | Python | `flask`, `fastapi`, `django`, `starlette`, `tornado`, `bottle` |
| `package.json` | JavaScript / TypeScript (check `tsconfig.json`, `.ts` files) | `express`, `fastify`, `koa`, `@nestjs/core`, `hapi`, `next` |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin | `spring-boot-starter-web`, `quarkus`, `micronaut`, `javalin` |
| `go.mod` | Go | `gin-gonic/gin`, `labstack/echo`, `gofiber/fiber`, `net/http` only |
| `Gemfile` | Ruby | `rails`, `sinatra`, `hanami` |
| `composer.json` | PHP | `laravel/framework`, `symfony`, `slim/slim` |
| `*.csproj` | C# | `Microsoft.AspNetCore` |
| `mix.exs` | Elixir | `phoenix` |

Version: take it from the manifest pin (`flask==3.1.1`, `"express": "^4.18.2"`). When the manifest has a range, also check the lockfile (`package-lock.json`, `poetry.lock`) for the resolved version and print both ("Express ^4.18.2 (4.21.2 resolvido)"). If no manifest exists, fall back to import statements and say the version is unknown.

Confirm the framework from the code, not only from the manifest: `Flask(__name__)`, `express()`, `@SpringBootApplication`, `gin.Default()`. The manifest tells you what is installed; the import tells you what is used.

## 2. Entry point

The entry point is the file that starts the HTTP listener:

- Python: `app.run(`, `uvicorn.run(`, `if __name__ == "__main__"`, or a `wsgi.py` / `asgi.py`.
- Node: `app.listen(`, `server.listen(`, `"main"` and `"scripts.start"` in `package.json`.
- Java: `SpringApplication.run(`, `public static void main`.
- Go: `func main()` with `ListenAndServe` / `router.Run`.

Record the port and host it binds to and whether debug mode is on; both are also audit inputs.

## 3. Database and persistence

Signals, in order of reliability:

1. Driver or ORM import: `sqlite3`, `psycopg2`, `pymongo`, `sqlalchemy`, `flask_sqlalchemy`, `peewee`, `require('sqlite3')`, `pg`, `mysql2`, `mongoose`, `prisma`, `sequelize`, `typeorm`, `knex`, `gorm`, `database/sql`.
2. Connection string or file path: `sqlite:///`, `postgres://`, `mongodb://`, `':memory:'`, `"something.db"`.
3. Schema: `CREATE TABLE` statements, ORM model classes (`db.Model`, `@Entity`, `mongoose.Schema`), migration folders (`migrations/`, `alembic/`, `prisma/schema.prisma`).
4. Seed data: `INSERT INTO`, `executemany(`, `seed.py`, `seeds/`, `db.run("INSERT`.

List every table or collection with its columns when the schema is visible. Flag whether foreign keys and constraints exist; their absence is an audit input (data integrity).

## 4. Routes and contract

Enumerate every route with method, path and handler. Patterns:

- Flask: `@app.route(`, `@bp.route(`, `app.add_url_rule(`, `methods=[...]`.
- FastAPI: `@app.get(`, `@router.post(`.
- Express: `app.get(`, `router.post(`, `app.use('/prefix', router)`, `app.delete(`.
- Spring: `@GetMapping`, `@RequestMapping`, `@RestController`.
- Go: `r.GET(`, `http.HandleFunc(`.

Also capture for each route: the request payload fields it reads (`request.get_json()`, `req.body.x`, `request.args.get(`), the status codes it returns and the response shape. This is the behavioural contract Phase 3 must preserve.

## 5. Responsibility map

For each source file, tick which responsibilities it contains. One file carrying three or more of these is a God file candidate (AP-03):

| Responsibility | Signals |
|----------------|---------|
| Routing | route decorators / `app.get(` / `add_url_rule` |
| Request parsing and validation | `request.get_json`, `req.body`, `if not x: return 400` |
| Business rules | calculations, status transitions, stock checks, discounts, permission checks |
| Data access | raw SQL strings, ORM queries, `cursor.execute`, `db.run`, `Model.query` |
| Serialization | hand-built dicts from rows, `to_dict`, `jsonify(` of nested structures |
| Configuration | `app.config[...] =`, `const config = {`, literal ports, keys, passwords |
| Cross-cutting | logging, notifications, cache, email, audit |
| Bootstrap | create app, create tables, seed, `listen` / `run` |

## 6. Architecture classification

Pick exactly one style and justify it in one line (pt-BR):

| Style | How it looks |
|-------|--------------|
| **Single-file script** | one file does everything |
| **Flat modules** | a handful of files at the root named by technical role (`app.py`, `models.py`, `controllers.py`, `database.py`) but each file mixes responsibilities or crosses layers (routes talk to the DB, "models" hold SQL and business rules together) |
| **Manager / service object** | one class (`AppManager`, `Service`, `Handler`) that owns DB, routes and logic |
| **Partial layering** | folders like `models/`, `routes/`, `services/`, `utils/` exist, but routes still hold business logic and data access, there is no controller layer, config is inline, cross-cutting code is duplicated |
| **MVC** | models, views/routes, controllers, config and middlewares exist and respect the dependency direction in `mvc-guidelines.md` |
| **Other** | hexagonal, clean architecture, CQRS... describe it |

The presence of folders is not enough to call it MVC. Check the dependency direction: routes importing the database object, or models importing the web framework, break the pattern.

## 7. Domain inference

Combine three sources: route paths (`/produtos`, `/checkout`, `/tasks`), table names and README. Write one line in pt-BR that names the business and the main entities, for example "API de e-commerce (produtos, usuários, pedidos, itens de pedido)". Mention sub-flows that stand out (checkout com pagamento, relatórios, autenticação).

## 8. Counting

- **Source files**: files with code extensions (`.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, `.php`, `.cs`) outside the ignore list. Lockfiles, README, `.http` files, `requirements.txt` and `package.json` are not source files, but `__init__.py` files are (count them, and mention when they are empty).
- **Lines of code**: `wc -l` over the source files, rounded (`~800`).
- **Endpoints**: the number of (method, path) pairs mapped in section 4.

## 9. Things to note for Phase 2 while you read

Keep a scratch list of anything that looks off while mapping the project (string-concatenated SQL, literal passwords, `debug=True`, global mutable variables, nested callbacks, loops that query inside, duplicated blocks, `print` everywhere, unused imports, bare `except`). Phase 2 will formalize them against the catalog; collecting them now avoids a third pass over the code.
