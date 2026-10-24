# MVC guidelines (Phase 3 target)

This is the architecture every project is moved to. The names are the classic MVC ones because the challenge asks for them; in an API without HTML the **View** is the HTTP boundary (routes + serialization), not a template.

## Layers and responsibilities

| Layer | Owns | Must not |
|-------|------|----------|
| **config/** | reading environment variables, defaults for local dev, feature flags (debug, CORS origins, ports, DB URL, secrets, admin token) | import anything from the other layers |
| **models/** | schema / entities, data access (queries, ORM mapping), domain rules that belong to the entity (price cannot be negative, valid status transitions, `is_overdue`), serialization whitelist (`to_dict` without secrets) | import the web framework (`flask.request`, `express`), format HTTP responses, know about status codes |
| **controllers/** | one use case per public function or method: validate input (through the validation module), call models/services, enforce business flow (check stock, compute total, decide on payment), raise domain errors, return plain data | build SQL, touch `request`/`req`/`res` objects, return framework response objects, hold state between calls |
| **views/** (or **routes/**) | binding HTTP method + path to a controller call, extracting params/body/query, serializing the controller result into the HTTP response with the right status code | contain `if` chains of business validation, query the database, catch exceptions individually |
| **middlewares/** | error handler (maps exception types to status codes), request logging, auth guard, CORS setup | business rules |
| **services/** (optional) | cross-cutting or external integrations invoked by controllers: notifications, payments, email, cache | data access of core entities (that is the model's job) |
| **validators/** or **schemas/** (optional) | request shape rules; reused by create and update | persistence |
| **app** (composition root) | create the framework app, load config, initialise DB, register middlewares and routes, expose `create_app()` / `createApp()` | implement handlers |
| **entry point** | start the server (`python app.py`, `node src/server.js`) | anything else |

Dependency direction (arrows mean "may import"):

```
entry point -> app (composition root) -> routes -> controllers -> models
                                      -> middlewares        -> services
                                      -> config  (config may be imported by any layer, imports nothing)
```

Models never import controllers or routes. Controllers never import routes. Routes never import the DB object.

## Target trees

### Python / Flask

```
<project>/
├── app.py                     # create_app() + run when executed
├── config/
│   ├── __init__.py
│   └── settings.py            # Config class reading os.environ
├── models/
│   ├── __init__.py
│   ├── base.py                # db handle / session helper (sqlite3 connection factory or SQLAlchemy db)
│   ├── <entity>_model.py      # one per entity (or <entity>.py when the folder already exists)
│   └── ...
├── controllers/
│   ├── __init__.py
│   └── <entity>_controller.py
├── views/                     # or routes/ when the project already uses that name
│   ├── __init__.py
│   └── <entity>_routes.py     # Blueprint per domain
├── middlewares/
│   ├── __init__.py
│   ├── error_handler.py       # register_error_handlers(app)
│   └── auth.py                # admin guard when needed
├── validators/                # or schemas/ when marshmallow / pydantic is available
├── services/                  # only when cross-cutting services exist
├── .env.example
├── requirements.txt
└── README.md
```

Rules for Flask:
- `create_app(config_object=None)` factory in `app.py`; `if __name__ == "__main__": create_app().run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)`.
- One Blueprint per domain, registered by the factory.
- Raw `sqlite3`: a connection factory in `models/base.py` that returns a per-request connection stored on `flask.g` and closed on teardown, or a small repository class receiving the connection; no module-level global connection.
- SQLAlchemy: `db = SQLAlchemy()` lives in `models/base.py` (or the existing `database.py` re-exported), `db.init_app(app)` in the factory, queries through `db.session`.
- Errors: domain exception classes (`NotFoundError`, `ValidationError`, `ConflictError`, `AuthError`) in `middlewares/error_handler.py` or `controllers/errors.py`; `app.register_error_handler` maps them to JSON + status; a catch-all for `Exception` returning 500 with a generic message and logging the stack.
- Logging through `logging.getLogger(__name__)`.

### Node / Express

```
<project>/
├── src/
│   ├── server.js              # entry point: createApp().listen(config.port)
│   ├── app.js                 # createApp({ db }) composition root
│   ├── config/
│   │   └── index.js           # process.env with defaults
│   ├── models/
│   │   ├── database.js        # connection factory + promise wrapper (run/get/all)
│   │   └── <entity>Model.js   # queries per entity, receive db in constructor or factory
│   ├── controllers/
│   │   └── <entity>Controller.js
│   ├── routes/                # the View layer in an API
│   │   ├── index.js
│   │   └── <entity>Routes.js  # express.Router()
│   ├── middlewares/
│   │   ├── errorHandler.js    # (err, req, res, next)
│   │   ├── asyncHandler.js    # wraps async route handlers
│   │   └── auth.js
│   ├── services/              # payment gateway, notifications, cache
│   └── validators/
├── .env.example
├── package.json
└── README.md
```

Rules for Express:
- Handlers are `async`; wrap with `asyncHandler` so rejections reach the error middleware; a handler returns exactly once.
- The DB driver is wrapped once (promise API) in `models/database.js`; models receive the wrapper, nothing else touches the driver.
- `createApp` receives dependencies (`db`, `services`) so tests can inject fakes.
- `package.json` `main` and `start` point to `src/server.js`.

### Other stacks

Apply the same layer table with the idiomatic names: Spring (`config/`, `model/` + `repository/`, `service/`, `controller/`, `advice/` for error handling), Go (`internal/config`, `internal/model`, `internal/handler`, `internal/service`, `internal/middleware`, `cmd/<app>/main.go`), Rails already is MVC (fix the violations inside it: fat controllers to services/concerns, callbacks to explicit flow), Laravel (`app/Http/Controllers`, `app/Models`, `app/Services`, `config/`).

## Adapting to a partially organised project

Do not rebuild what already follows the pattern. When `models/`, `routes/`, `services/`, `utils/` exist:

1. Keep the folder names and module names users already know (`routes/task_routes.py` stays).
2. Add the missing layers (`controllers/`, `config/`, `middlewares/`, `validators/`).
3. Move business logic and queries out of the routes into controllers and models; routes become thin.
4. Pull the duplicated helpers into the right layer and delete the duplicates; an unused `utils/helpers.py` function that implements something routes re-implement inline is the signal that the helper should become the single implementation (usually inside the model or validator).
5. Rename only when the current name lies about its content (a `report_routes.py` serving `/categories` gets a `category_routes.py` for those endpoints).
6. Fix the dependency direction (routes importing `db` go through controllers; models never import `flask`).
7. Modules that only hold dead code (a service never instantiated, a helpers file nobody imports) are removed, not carried into the target tree; the Phase 2 report lists them under "Removed" and the Phase 3 summary confirms the removal. Configuration that only existed to serve dead code (for example SMTP settings for a notification service that was never called) goes away with it.

## Behaviour preservation

The Phase 1 route list is the contract. After Phase 3:

- Every (method, path) pair still exists.
- Status codes and response JSON keys are unchanged for successful calls and for the validation errors already present.
- Request field names stay the same even when they are ugly (`usr`, `eml`); map them to good names inside the route layer.
- Seed data and default DB location keep working with the documented run command (`python app.py`, `npm start`, `python seed.py`).
- The port stays the documented default unless overridden by environment.

### Contract decisions

Some findings cannot be fixed without changing behaviour. Allowed changes, each one must be listed in the Phase 2 preview and in the Phase 3 summary:

| Situation | Decision |
|-----------|----------|
| Response includes passwords / hashes / secrets | remove the field; everything else in the payload stays |
| Health or info endpoint leaks config | keep `status` and counts, drop secrets, debug flag, DB path, environment |
| Endpoint executes arbitrary SQL from the request | keep the route registered; require an admin token from config (`403` when missing or wrong, `503` when the token is not configured); restrict to read-only statements (`SELECT`) using parameter-less execution on a read-only connection |
| Destructive admin endpoint (reset, truncate) | keep the route; require the admin token; refuse when `APP_ENV=production` |
| Delete without authentication | keep the route; require the admin token or ownership check; delete child rows in the same transaction instead of leaving orphans; the response message becomes a normal success message |
| Plaintext password compare | hash on write, verify on read; existing seed users are re-seeded with hashed passwords so documented credentials keep working |
| Sensitive data in logs | log the event without the data (last 4 digits of a card at most) |
| `debug=True`, open CORS | read from config; local default may keep debug on, production default off |

Anything outside this table that changes an observable behaviour is not allowed without asking the user.

## Definition of done for Phase 3

- Target tree in place; old monolithic files deleted (no `models.py` next to `models/`).
- No file carries more than one layer responsibility.
- Every finding in the report maps to a resolution line in the Phase 3 summary.
- `.env.example` documents every variable read by `config/`.
- README of the project updated: run instructions, layout, env vars, contract decisions.
- Validation block fully green or with explicit residuals.
