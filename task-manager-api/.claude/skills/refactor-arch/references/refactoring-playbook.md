# Refactoring playbook (Phase 3)

Concrete transformations, one per anti-pattern family. Each has the catalog IDs it resolves, the steps, and a before/after pair. Examples alternate between Python/Flask and Node/Express; the steps are stack-neutral.

Index:

| Pattern | Resolves | Name |
|---------|----------|------|
| RP-01 | AP-01, AP-11 | Extract configuration to a config module |
| RP-02 | AP-02 | Parameterise every query |
| RP-03 | AP-03, AP-20 | Split a God file into layers and domains |
| RP-04 | AP-07, AP-17 | Thin routes, controllers orchestrate |
| RP-05 | AP-08, AP-09 | Composition root and dependency injection |
| RP-06 | AP-16, AP-11 | Centralised error handling |
| RP-07 | AP-10 | Callback pyramid to async/await |
| RP-08 | AP-13 | Replace N+1 with joins and aggregates |
| RP-09 | AP-04, AP-05 | Password hashing and serializer whitelist |
| RP-10 | AP-18 | Replace deprecated APIs |
| RP-11 | AP-19 | Named constants and enums |
| RP-12 | AP-22, AP-17 | Structured logging |
| RP-13 | AP-06 | Guard or neutralise dangerous endpoints |
| RP-14 | AP-12 | Transactions and integrity |
| RP-15 | AP-14, AP-21, AP-23 | Deduplicate into shared model / validator code |
| RP-16 | AP-15 | Validation layer |

---

## RP-01 Extract configuration to a config module

Steps: list every literal setting (secret key, DB path/URL, port, host, debug, CORS, API keys, SMTP); create `config/settings.py` or `src/config/index.js` reading environment variables with local defaults; replace every literal with the config attribute; add `.env.example` with all keys and placeholder values; never commit a real secret.

Before (Python):
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
CORS(app)
app.run(host="0.0.0.0", port=5000, debug=True)
```

After:
```python
# config/settings.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")

# app.py
def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    CORS(app, origins=app.config["CORS_ORIGINS"])
    ...
    return app

if __name__ == "__main__":
    application = create_app()
    application.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
```

Before (Node):
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_1234567890abcdef", port: 3000 };
```

After:
```js
// src/config/index.js
module.exports = {
  port: Number(process.env.PORT) || 3000,
  env: process.env.NODE_ENV || 'development',
  database: { file: process.env.DATABASE_FILE || ':memory:' },
  payment: { gatewayKey: process.env.PAYMENT_GATEWAY_KEY || '' },
  adminToken: process.env.ADMIN_TOKEN || null,
};
```

`.env.example`:
```
PORT=3000
DATABASE_FILE=:memory:
PAYMENT_GATEWAY_KEY=
ADMIN_TOKEN=
```

---

## RP-02 Parameterise every query

Steps: find every query built by concatenation / interpolation; rewrite with placeholders (`?`, `%s`, `$1`, named params) and pass values separately; for dynamic filters build the `WHERE` from a list of fixed fragments and a parallel list of params; for ORMs use expressions (`Model.col == value`) instead of raw strings.

Before:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```

After:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
```

Dynamic search, before:
```python
query = "SELECT * FROM produtos WHERE 1=1"
if termo:
    query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
if categoria:
    query += " AND categoria = '" + categoria + "'"
```

After:
```python
clauses, params = [], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)
sql = "SELECT * FROM produtos" + (" WHERE " + " AND ".join(clauses) if clauses else "")
cursor.execute(sql, params)
```

Node:
```js
// before
db.all(`SELECT * FROM courses WHERE title LIKE '%${q}%'`, cb);
// after
await db.all('SELECT * FROM courses WHERE title LIKE ?', [`%${q}%`]);
```

---

## RP-03 Split a God file into layers and domains

Steps: list the responsibilities in the file (Phase 1 map); for each domain entity create `<entity>_model` (queries + entity rules), `<entity>_controller` (use cases), `<entity>_routes` (HTTP binding); move functions one domain at a time, keeping the old file importable until the last move; finally delete the old file and fix imports; give meaningful names while moving (`badCrypto` -> `PasswordHasher.hash`, `AppManager.setupRoutes` -> `routes/index.js`).

Before (`models.py` holding everything):
```python
def criar_pedido(usuario_id, itens):
    db = get_db(); cursor = db.cursor()
    total = 0
    for item in itens:
        cursor.execute("SELECT * FROM produtos WHERE id = " + str(item["produto_id"]))
        produto = cursor.fetchone()
        if produto["estoque"] < item["quantidade"]:
            return {"erro": "Estoque insuficiente para " + produto["nome"]}
        total = total + (produto["preco"] * item["quantidade"])
    cursor.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (" + str(usuario_id) + ", 'pendente', " + str(total) + ")")
    ...
```

After:
```python
# models/pedido_model.py
class PedidoModel:
    def __init__(self, connection):
        self.conn = connection

    def inserir(self, usuario_id, total, itens):
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, StatusPedido.PENDENTE, total),
            )
            pedido_id = cur.lastrowid
            self.conn.executemany(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                [(pedido_id, i["produto_id"], i["quantidade"], i["preco_unitario"]) for i in itens],
            )
        return pedido_id

# controllers/pedido_controller.py
class PedidoController:
    def __init__(self, pedidos: PedidoModel, produtos: ProdutoModel, notificacoes: NotificationService):
        ...

    def criar(self, usuario_id, itens):
        itens_validados, total = self._reservar_estoque(itens)
        pedido_id = self.pedidos.inserir(usuario_id, total, itens_validados)
        self.notificacoes.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

# views/pedido_routes.py
@bp.post("/pedidos")
def criar_pedido():
    dados = PedidoCreateSchema.load(request.get_json())
    resultado = controllers.pedidos.criar(dados["usuario_id"], dados["itens"])
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201
```

---

## RP-04 Thin routes, controllers orchestrate

Steps: for each handler, cut it in three: (a) parse + validate input, (b) the use case, (c) build the response; (a) and (c) stay in the route, (b) moves to a controller method that receives plain values and returns plain data or raises a domain exception; side effects (notifications, cache) are called by the controller through a service.

Before (Flask route with everything):
```python
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data: return jsonify({'error': 'Dados inválidos'}), 400
    title = data.get('title')
    if not title: return jsonify({'error': 'Título é obrigatório'}), 400
    if len(title) < 3: return jsonify({'error': 'Título muito curto'}), 400
    ...
    if user_id:
        user = User.query.get(user_id)
        if not user: return jsonify({'error': 'Usuário não encontrado'}), 404
    task = Task(); task.title = title; ...
    db.session.add(task); db.session.commit()
    print(f"Task criada: {task.id}")
    return jsonify(task.to_dict()), 201
```

After:
```python
# routes/task_routes.py
@task_bp.post('/tasks')
def create_task():
    task = task_controller.create(request.get_json())
    return jsonify(task.to_dict()), 201

# controllers/task_controller.py
class TaskController:
    def create(self, payload):
        data = validate_task_payload(payload, partial=False)
        self._ensure_references_exist(data)
        task = Task.create(**data)
        logger.info("task created id=%s", task.id)
        return task
```

Express, before:
```js
app.post('/api/checkout', (req, res) => { /* 50 lines: validation, DB, payment, enrollment, audit */ });
```

After:
```js
// routes/checkoutRoutes.js
router.post('/checkout', asyncHandler(async (req, res) => {
  const input = parseCheckoutInput(req.body);
  const result = await checkoutController.checkout(input);
  res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
}));

// controllers/checkoutController.js
class CheckoutController {
  constructor({ courses, users, enrollments, payments, auditLog, paymentGateway, hasher }) { ... }
  async checkout({ name, email, password, courseId, card }) {
    const course = await this.courses.findActive(courseId);
    if (!course) throw new NotFoundError('Curso não encontrado');
    const user = await this.users.findOrCreate({ name, email, password }, this.hasher);
    const charge = await this.paymentGateway.charge(card, course.price);
    if (!charge.approved) throw new PaymentDeniedError();
    return this.enrollments.enrollWithPayment({ userId: user.id, courseId, amount: course.price, status: charge.status });
  }
}
```

---

## RP-05 Composition root and dependency injection

Steps: remove `new Database()` / `get_db()` calls from classes and modules that are not the composition root; give each model/controller a constructor (or factory) that receives what it needs; create `create_app()` / `createApp({ db })` that builds config -> db -> models -> services -> controllers -> routes -> middlewares; module-level globals become instances owned by the app (Flask: `app.extensions` or closure; Node: passed to `createApp`).

Before:
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  setupRoutes(app) { app.post('/api/checkout', (req, res) => { this.db.get(...) }) }
}
const manager = new AppManager(); manager.initDb(); manager.setupRoutes(app);
```

After:
```js
// src/app.js
function createApp({ db }) {
  const app = express();
  app.use(express.json());
  const models = buildModels(db);
  const services = buildServices(config);
  const controllers = buildControllers(models, services);
  app.use('/api', buildRoutes(controllers));
  app.use(errorHandler);
  return app;
}

// src/server.js
const db = await openDatabase(config.database.file);
await runMigrations(db);
await seed(db);
createApp({ db }).listen(config.port);
```

Python with raw sqlite3, before:
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)
```

After:
```python
# models/base.py
def get_connection():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_connection(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_connection)
```

---

## RP-06 Centralised error handling

Steps: define a small hierarchy of domain exceptions carrying a status code; controllers and models raise them; remove per-handler try/except; register one error handler per exception type plus a catch-all that logs the stack and returns a generic 500 body; keep the JSON error key the project already uses (`erro`, `error`) so clients do not break.

Python:
```python
# middlewares/error_handler.py
class AppError(Exception):
    status_code = 500
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code: self.status_code = status_code

class ValidationError(AppError): status_code = 400
class NotFoundError(AppError): status_code = 404
class AuthError(AppError): status_code = 401
class ConflictError(AppError): status_code = 409

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, "sucesso": False}), err.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("unhandled error")
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
```

Node:
```js
// middlewares/errorHandler.js
function errorHandler(err, req, res, next) {
  const status = err.statusCode || 500;
  if (status >= 500) logger.error(err);
  res.status(status).json({ error: status >= 500 ? 'Erro interno' : err.message });
}
// middlewares/asyncHandler.js
const asyncHandler = fn => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
```

---

## RP-07 Callback pyramid to async/await

Steps: wrap the driver once with promises (`run` returning `{ lastID, changes }`, `get`, `all`, `exec`); convert each handler to `async`; replace manual counters with `Promise.all` / `for...of`; a single `return` path; let errors propagate to the error middleware.

Before:
```js
this.db.get("SELECT ...", [cid], (err, course) => {
  if (err || !course) return res.status(404).send("Curso não encontrado");
  this.db.get("SELECT id FROM users WHERE email = ?", [e], (err, user) => {
    this.db.run("INSERT INTO enrollments ...", function (err) {
      let enrId = this.lastID;
      self.db.run("INSERT INTO payments ...", function (err) { ... res.json(...) });
    });
  });
});
```

After:
```js
// models/database.js
function promisify(db) {
  return {
    run: (sql, params = []) => new Promise((resolve, reject) =>
      db.run(sql, params, function (err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); })),
    get: (sql, params = []) => new Promise((resolve, reject) => db.get(sql, params, (err, row) => err ? reject(err) : resolve(row))),
    all: (sql, params = []) => new Promise((resolve, reject) => db.all(sql, params, (err, rows) => err ? reject(err) : resolve(rows))),
    exec: (sql) => new Promise((resolve, reject) => db.exec(sql, err => err ? reject(err) : resolve())),
  };
}

// controllers/checkoutController.js (excerpt)
const course = await this.courses.findActive(courseId);
if (!course) throw new NotFoundError('Curso não encontrado');
const user = (await this.users.findByEmail(email)) || (await this.users.create({ name, email, passwordHash }));
const enrollment = await this.enrollments.create(user.id, courseId);
await this.payments.create(enrollment.id, course.price, 'PAID');
return { enrollmentId: enrollment.id };
```

Fan-out with counters, before:
```js
courses.forEach(c => { db.all(..., (err, enrollments) => { enrPending--; if (enrPending === 0) res.json(report); }) });
```

After:
```js
const report = await Promise.all(courses.map(async (course) => ({
  course: course.title,
  students: await this.enrollments.listStudentsWithPayment(course.id),
})));
```

---

## RP-08 Replace N+1 with joins and aggregates

Steps: identify the loop; write one query that returns the joined rows (or one query for parents and one `WHERE id IN (...)` for children); group in memory; for counts by status use `GROUP BY` or a single `CASE` aggregate; with an ORM use `joinedload` / `selectinload` or `with_entities(func.count())`.

Before:
```python
cursor.execute("SELECT * FROM pedidos")
for row in cursor.fetchall():
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in cursor2.fetchall():
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```

After:
```python
rows = conn.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    WHERE (? IS NULL OR p.usuario_id = ?)
    ORDER BY p.id
""", (usuario_id, usuario_id)).fetchall()
pedidos = {}
for r in rows:
    pedido = pedidos.setdefault(r["id"], {"id": r["id"], ..., "itens": []})
    if r["produto_id"] is not None:
        pedido["itens"].append({...})
return list(pedidos.values())
```

Counts, before:
```python
pending = Task.query.filter_by(status='pending').count()
in_progress = Task.query.filter_by(status='in_progress').count()
done = Task.query.filter_by(status='done').count()
```

After:
```python
rows = db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
by_status = {status: 0 for status in TaskStatus.values()}
by_status.update(dict(rows))
```

Relations, before: `User.query.get(t.user_id)` inside a loop. After: `Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()` and read `t.user.name`.

---

## RP-09 Password hashing and serializer whitelist

Steps: pick the platform hasher (`werkzeug.security.generate_password_hash` / `check_password_hash`, `bcrypt`, `argon2`); hash on create/update, verify on login; re-seed documented users through the same path; serializers list the public fields explicitly and never include password, hash, tokens, keys; logs mask card numbers and never print passwords.

Before:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
...
return {"id": row["id"], "email": row["email"], "senha": row["senha"]}
```

After:
```python
from werkzeug.security import generate_password_hash, check_password_hash

class UsuarioModel:
    PUBLIC_FIELDS = ("id", "nome", "email", "tipo", "criado_em")

    def autenticar(self, email, senha):
        row = self.conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if row and check_password_hash(row["senha"], senha):
            return self.to_dict(row)
        return None

    def to_dict(self, row):
        return {campo: row[campo] for campo in self.PUBLIC_FIELDS}
```

Node, before: `let hash = badCrypto(p || "123456")` and `console.log(\`Processando cartão ${cc}\`)`.
After:
```js
const bcrypt = require('bcryptjs');
const passwordHash = await bcrypt.hash(password, 10);
logger.info('payment attempt', { card: `****${card.slice(-4)}` });
```
(When a new dependency is not acceptable, `crypto.scryptSync` with a random salt from `node:crypto` is the built-in fallback.)

---

## RP-10 Replace deprecated APIs

Steps: for each row matched from the catalog table, apply the replacement everywhere, then boot the app and confirm the warning is gone.

```python
# before
created_at = db.Column(db.DateTime, default=datetime.utcnow)
task = Task.query.get(task_id)
user = db.relationship('User', backref='tasks')
# after
from datetime import datetime, timezone
def utc_now(): return datetime.now(timezone.utc)
created_at = db.Column(db.DateTime, default=utc_now)
task = db.session.get(Task, task_id)
user = db.relationship('User', back_populates='tasks')   # and tasks = db.relationship('Task', back_populates='user') on User
```

```js
// before
const buf = new Buffer(str); const u = url.parse(req.url); res.send(404);
// after
const buf = Buffer.from(str); const u = new URL(req.url, base); res.sendStatus(404);
```

---

## RP-11 Named constants and enums

Steps: collect every literal list and threshold; put them next to the entity they describe (`models/<entity>_model.py` or a `constants` module); replace usages; when the project already defines constants somewhere (`utils/helpers.py: VALID_STATUSES`), make that the single source or move it to the model.

Before:
```python
if novo_status not in ["pendente", "aprovado", "enviado", "entregue", "cancelado"]:
...
if faturamento > 10000: desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
```

After:
```python
class StatusPedido(str, Enum):
    PENDENTE = "pendente"; APROVADO = "aprovado"; ENVIADO = "enviado"; ENTREGUE = "entregue"; CANCELADO = "cancelado"

FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))

def calcular_desconto(faturamento):
    for limite, percentual in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * percentual
    return 0
```

---

## RP-12 Structured logging

Steps: configure the standard logger once in the composition root (level from config); each module gets `logger = logging.getLogger(__name__)` / a shared `logger` object; replace `print` with the right level; never log secrets or full card numbers; the startup banner becomes `logger.info`.

```python
# before
print("ERRO ao criar produto: " + str(e))
# after
logger.exception("falha ao criar produto")
```

```js
// before
console.log(`[LOG] Salvando no cache: ${key}`);
// after
logger.debug('cache set', { key });
```

A minimal Node logger without dependencies:
```js
const levels = { error: 0, warn: 1, info: 2, debug: 3 };
const current = levels[process.env.LOG_LEVEL || 'info'];
const log = (level) => (msg, meta) => { if (levels[level] <= current) console[level === 'debug' ? 'log' : level](JSON.stringify({ level, msg, ...meta, ts: new Date().toISOString() })); };
module.exports = { error: log('error'), warn: log('warn'), info: log('info'), debug: log('debug') };
```

---

## RP-13 Guard or neutralise dangerous endpoints

Steps: create an auth middleware that checks a token from config (`X-Admin-Token` header or `Authorization: Bearer`); apply it to admin and destructive routes; when the token is not configured, respond `503` with a clear message instead of running; for "execute arbitrary SQL" endpoints keep only read-only execution on a read-only connection, or return `403` always and document it; destructive resets refuse in production.

```python
# middlewares/auth.py
def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        if not expected:
            raise AppError("Endpoint administrativo desabilitado: configure ADMIN_TOKEN", 503)
        if request.headers.get("X-Admin-Token") != expected:
            raise AuthError("Token administrativo inválido")
        return view(*args, **kwargs)
    return wrapper

# views/admin_routes.py
@admin_bp.post("/admin/query")
@require_admin
def executar_query():
    sql = (request.get_json() or {}).get("sql", "")
    return jsonify({"dados": admin_controller.consulta_somente_leitura(sql), "sucesso": True}), 200
```

```js
// middlewares/auth.js
function requireAdmin(req, res, next) {
  if (!config.adminToken) return next(new AppError('Endpoint administrativo desabilitado: configure ADMIN_TOKEN', 503));
  if (req.get('X-Admin-Token') !== config.adminToken) return next(new AppError('Token administrativo inválido', 401));
  next();
}
router.delete('/users/:id', requireAdmin, asyncHandler(userController.remove));
```

---

## RP-14 Transactions and integrity

Steps: wrap multi-statement writes in one transaction (`with conn:` in sqlite3, `BEGIN`/`COMMIT`/`ROLLBACK` through the promise wrapper, `db.session.begin()` in SQLAlchemy); validate everything before the first write; add `FOREIGN KEY ... ON DELETE CASCADE`, `UNIQUE`, `NOT NULL` to the schema and enable `PRAGMA foreign_keys = ON` on every sqlite connection; deletes remove children explicitly when cascade is not possible.

```python
def inserir_pedido(self, usuario_id, itens):
    with self.conn:
        total = 0
        for item in itens:
            produto = self.conn.execute("SELECT preco, estoque, nome FROM produtos WHERE id = ?", (item["produto_id"],)).fetchone()
            if produto is None: raise NotFoundError(f"Produto {item['produto_id']} não encontrado")
            if produto["estoque"] < item["quantidade"]: raise ValidationError(f"Estoque insuficiente para {produto['nome']}")
            total += produto["preco"] * item["quantidade"]
        pedido_id = self.conn.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)", (usuario_id, "pendente", total)).lastrowid
        for item in itens:
            self.conn.execute("INSERT INTO itens_pedido ... VALUES (?, ?, ?, ?)", (...))
            self.conn.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (item["quantidade"], item["produto_id"]))
    return pedido_id, total
```

```js
async enrollWithPayment({ userId, courseId, amount, status }) {
  await this.db.exec('BEGIN');
  try {
    const { lastID: enrollmentId } = await this.db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
    await this.db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status]);
    await this.db.exec('COMMIT');
    return { enrollmentId };
  } catch (err) { await this.db.exec('ROLLBACK'); throw err; }
}
```

Schema:
```sql
CREATE TABLE enrollments (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course_id INTEGER NOT NULL REFERENCES courses(id)
);
```

---

## RP-15 Deduplicate into shared model / validator code

Steps: find the copies (serializers, overdue maths, validation chains, query boilerplate); choose the owner layer (serialization -> model `to_dict`; domain predicate -> model method; request rules -> validator; query boilerplate -> base model helper); implement once; replace every copy; delete dead helpers that were never wired, or wire them in if they are the better implementation.

Before (repeated six times across routes):
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
        else:
            task_data['overdue'] = False
    else:
        task_data['overdue'] = False
else:
    task_data['overdue'] = False
```

After (model owns it, serializer uses it):
```python
class Task(db.Model):
    OPEN_STATUSES = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)

    def is_overdue(self):
        return bool(self.due_date and self.due_date < utc_now() and self.status in self.OPEN_STATUSES)

    def to_dict(self, include_relations=False):
        data = {..., "overdue": self.is_overdue()}
        if include_relations:
            data["user_name"] = self.user.name if self.user else None
        return data
```

Query boilerplate in raw sqlite3, before: eight functions each doing `db = get_db(); cursor = db.cursor(); cursor.execute(...); rows = cursor.fetchall(); result = []; for row in rows: result.append({...})`.
After:
```python
class BaseModel:
    def __init__(self, conn): self.conn = conn
    def fetch_all(self, sql, params=()): return [dict(r) for r in self.conn.execute(sql, params).fetchall()]
    def fetch_one(self, sql, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None
```

---

## RP-16 Validation layer

Steps: one validator (or schema) per payload, shared by create and update (`partial=True` for update); it converts types, checks ranges and enumerations and returns clean data or raises `ValidationError` with the same messages the API already returns; routes call it before the controller (or the controller calls it first); use the library already in the manifest (`marshmallow`, `pydantic`, `joi`, `zod`) when present, otherwise a plain module with functions.

Python without a library:
```python
# validators/produto_validator.py
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")

def validar_produto(dados):
    if not dados: raise ValidationError("Dados inválidos")
    for campo, msg in (("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"), ("estoque", "Estoque é obrigatório")):
        if campo not in dados: raise ValidationError(msg)
    nome = str(dados["nome"]).strip()
    if len(nome) < 2: raise ValidationError("Nome muito curto")
    if len(nome) > 200: raise ValidationError("Nome muito longo")
    try:
        preco = float(dados["preco"]); estoque = int(dados["estoque"])
    except (TypeError, ValueError):
        raise ValidationError("Preço e estoque devem ser numéricos")
    if preco < 0: raise ValidationError("Preço não pode ser negativo")
    if estoque < 0: raise ValidationError("Estoque não pode ser negativo")
    categoria = dados.get("categoria", "geral")
    if categoria not in CATEGORIAS_VALIDAS: raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))
    return {"nome": nome, "descricao": dados.get("descricao", ""), "preco": preco, "estoque": estoque, "categoria": categoria}
```

Python with marshmallow (when it is already a dependency):
```python
class TaskSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    status = fields.Str(load_default="pending", validate=validate.OneOf(TaskStatus.values()))
    priority = fields.Int(load_default=3, validate=validate.Range(min=1, max=5))
    due_date = fields.Date(allow_none=True)
    tags = fields.List(fields.Str(), load_default=list)
```

Node without a library:
```js
function parseCheckoutInput(body = {}) {
  const { usr: name, eml: email, pwd: password, c_id: courseId, card } = body;
  if (!name || !email || !courseId || !card) throw new ValidationError('Bad Request');
  if (!/^\d{13,19}$/.test(String(card))) throw new ValidationError('Cartão inválido');
  return { name, email, password, courseId: Number(courseId), card: String(card) };
}
```
