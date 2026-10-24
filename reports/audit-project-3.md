================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.12 + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1)
Files:   15 analyzed | ~1160 lines of code
Date:    2026-10-03

## Summary
CRITICAL: 4 | HIGH: 8 | MEDIUM: 7 | LOW: 5

## Findings

### #1 [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:13
File: services/notification_service.py:9-10
Description: A chave de sessão do Flask está hardcoded em texto puro (`app.config['SECRET_KEY'] = 'super-secret-key-123'`) e as credenciais de e-mail do SMTP (`email_user`, `email_password = 'senha123'`) também estão escritas diretamente no construtor de `NotificationService`.
Impact: Qualquer pessoa com acesso ao repositório tem a chave de assinatura de sessão e a senha da conta de e-mail da aplicação; trocar qualquer um dos dois exige novo deploy, e o mesmo valor vaza para todos os ambientes (dev, staging, produção).
Recommendation: Mover ambos para variáveis de ambiente lidas por um módulo `config/`, com valores de exemplo em `.env.example` e nenhuma credencial real no código-fonte. Ver RP-01.

### #2 [CRITICAL] Sensitive data exposure in responses or logs (AP-04)
File: models/user.py:16-25
Description: `User.to_dict()` inclui o campo `password` (o hash) na resposta (linha 21: `'password': self.password`). Esse método é chamado por `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login`, então o hash da senha trafega em toda resposta que serializa um usuário.
Impact: Qualquer consumidor da API (ou um log de requisição/resposta) recebe o hash da senha de qualquer usuário, o que facilita ataques offline de força bruta contra o hash exposto.
Recommendation: Remover o campo `password` da serialização pública e, se necessário internamente, usar um serializer separado "whitelist" que nunca inclua esse campo. Ver RP-09.

### #3 [CRITICAL] Plaintext or weak password storage (AP-05)
File: models/user.py:27-32
Description: `set_password` grava a senha como `hashlib.md5(pwd.encode()).hexdigest()` (linha 29), sem salt, e `check_password` (linha 31-32) compara o hash MD5 recalculado com o armazenado.
Impact: MD5 sem salt é quebrado por força bruta/rainbow tables em segundos; um vazamento do banco de dados (`tasks.db`) expõe efetivamente as senhas de todos os usuários cadastrados.
Recommendation: Trocar para um algoritmo de hash de senha moderno com salt embutido (`werkzeug.security.generate_password_hash`/`check_password_hash`, `bcrypt` ou `argon2`), re-hasheando os usuários de seed. Ver RP-09.

### #4 [CRITICAL] Unprotected dangerous endpoint (AP-06)
File: routes/user_routes.py:134-151
Description: `DELETE /users/<user_id>` apaga em cascata todas as tasks do usuário (linhas 140-142, um laço que deleta cada `Task` antes de deletar o `User`) sem qualquer verificação de autenticação ou autorização — qualquer chamador anônimo pode apagar um usuário e todo o seu histórico de tasks.
Impact: Destruição remota e irreversível de dados (usuário + todas as suas tasks) por qualquer pessoa que alcance o host, sem necessidade de credenciais.
Recommendation: Exigir um token de administrador apenas nesta rota destrutiva (guard de autenticação vindo da configuração), mantendo as demais rotas de delete (`/tasks/<id>`, `/categories/<id>`) como operações de domínio comuns. Ver RP-13.

### #5 [HIGH] God file / God class (AP-03)
File: routes/task_routes.py:1-299
Description: Um único módulo de rotas concentra parsing/validação de request, regras de negócio (cálculo de atraso, faixas de prioridade, normalização de tags), acesso a dados (`Task.query`, `User.query.get`, `Category.query.get`) e serialização manual para a entidade Task, em 299 linhas.
Impact: Nada pode ser testado isoladamente da camada HTTP; qualquer mudança de regra de negócio da Task obriga a editar o mesmo arquivo que define as rotas, aumentando o risco de conflitos e regressões.
Severity rule: Classificado como HIGH, e não CRITICAL, porque o projeto já separa `models/` (acesso a dados/schema) e `routes/` (HTTP) em módulos próprios — a concentração de responsabilidades acontece dentro da camada de rotas, não entre banco de dados e HTTP no mesmo arquivo.
Recommendation: Extrair a lógica para `controllers/task_controller.py` (regras e orquestração) e deixar `routes/task_routes.py` apenas vinculando HTTP ao controller. Ver RP-03.

### #6 [HIGH] God file / God class (AP-03)
File: routes/report_routes.py:1-223
Description: O mesmo blueprint (`report_bp`) mistura geração de relatórios agregados (`summary_report`, `user_report`, com laços de agregação e cálculo de percentuais) com o CRUD completo de Categorias (`get_categories`, `create_category`, `update_category`, `delete_category`), dois domínios distintos no mesmo arquivo de 223 linhas.
Impact: O módulo de "reports" cresce a cada novo relatório e a cada nova regra de categoria ao mesmo tempo; um teste de regressão em categorias precisa carregar todo o módulo de relatórios.
Severity rule: HIGH pelo mesmo motivo do achado #5 — `models/` e `routes/` já existem como camadas separadas; o problema é a concentração de dois domínios dentro da mesma camada de rotas.
Recommendation: Separar em `controllers/report_controller.py` e `controllers/category_controller.py`, cada um com sua própria rota dedicada. Ver RP-03.

### #7 [HIGH] Tight coupling / no dependency injection (AP-09)
File: routes/task_routes.py:2
File: routes/user_routes.py:2
File: routes/report_routes.py:2
File: app.py:1-34
Description: As três blueprints importam o objeto concreto `db` diretamente de `database.py` (`from database import db`) e chamam `db.session`/`Model.query` dentro dos próprios handlers. `app.py` cria a aplicação, o banco e as rotas todos no escopo do módulo (linhas 9-31), sem uma função factory (`create_app()`), e já chama `db.create_all()` no import do módulo (linhas 30-31).
Impact: Não é possível subir a aplicação com um banco de testes diferente ou um dublê (mock/stub) sem reescrever os módulos de rota; qualquer teste de unidade acaba precisando de um banco SQLite real.
Recommendation: Introduzir uma função `create_app()` como composition root, que recebe a configuração e injeta `db`/sessão nos controllers; rotas passam a depender de uma interface, não do objeto `db` global. Ver RP-05.

### #8 [HIGH] Missing transaction and data integrity (AP-12)
File: routes/report_routes.py:211-223
File: models/task.py:13-14
Description: `delete_category` apaga a `Category` sem tratar as `Task` que referenciam `category_id` (nenhuma atualização para `NULL`, nenhum `ON DELETE` configurado na coluna `models/task.py:14`); o resultado é um `category_id` órfão apontando para uma categoria que não existe mais. O mesmo padrão de ausência de `ondelete`/cascade no nível de schema aparece em `user_id` (linha 13).
Impact: Relatórios e buscas por categoria passam a referenciar IDs inexistentes silenciosamente (sem erro), corrompendo estatísticas (`/reports/summary`, `/categories`) sem que ninguém perceba.
Recommendation: Resolver a integridade no schema (constraint `ondelete='SET NULL'` ou `'CASCADE'` nas colunas de FK do model `Task`) em vez de depender de limpeza manual espalhada pelas rotas. Ver RP-14.

### #9 [HIGH] Business logic inside route handlers (fat controllers) (AP-07)
File: routes/task_routes.py:85-154
File: routes/task_routes.py:156-223
Description: `create_task` e `update_task` combinam, na própria função de rota, validação de tamanho de título, lista de status válidos, faixa de prioridade, parsing de data e normalização de tags, além da persistência (`db.session.add/commit`) — tudo isso é regra de negócio da entidade Task reimplementada na camada HTTP em vez de reaproveitar `Task.validate_status`/`Task.validate_priority` (achado #16/#22, nunca chamados).
Impact: As mesmas regras de negócio só podem ser exercidas via HTTP; um job em lote ou um script de importação não consegue reutilizar a validação, e qualquer ajuste de regra precisa ser replicado manualmente em cada handler.
Recommendation: Mover as regras para `controllers/task_controller.py` e para os métodos do model `Task`, deixando a rota apenas repassar o payload validado. Ver RP-04 e RP-16.

### #10 [HIGH] Business logic inside route handlers (fat controllers) (AP-07)
File: routes/user_routes.py:42-90
File: routes/user_routes.py:92-132
Description: `create_user` e `update_user` fazem validação de e-mail por regex, checagem de tamanho mínimo de senha, whitelist de `role` e checagem de unicidade de e-mail (`User.query.filter_by(email=...).first()`) diretamente no handler, antes de chamar `set_password` e persistir.
Impact: As regras de cadastro de usuário (e-mail válido, senha mínima, roles permitidas) só existem dentro da camada HTTP, tornando impossível reaproveitá-las em um script administrativo de criação de usuários sem duplicar o código.
Recommendation: Extrair para `controllers/user_controller.py`, delegando a validação de formato a um schema/validador reutilizável. Ver RP-04 e RP-16.

### #11 [HIGH] Business logic inside route handlers (fat controllers) (AP-07)
File: routes/report_routes.py:12-101
File: routes/report_routes.py:103-155
Description: `summary_report` e `user_report` calculam, dentro do handler, contagens por status, por prioridade, lista de atrasados com dias de atraso, atividade dos últimos 7 dias e produtividade por usuário — toda a lógica de agregação de relatório vive na rota, sem nenhum model ou controller de relatório.
Impact: Qualquer novo relatório exige copiar esse bloco de agregação inteiro; não há como testar o cálculo de "completion_rate" ou "overdue" sem subir a aplicação Flask inteira.
Recommendation: Mover a lógica de agregação para `controllers/report_controller.py` (ou um model agregador), deixando a rota apenas invocar o controller e serializar o resultado. Ver RP-04.

### #12 [HIGH] Insecure runtime defaults (AP-11)
File: app.py:15
File: app.py:34
Description: `CORS(app)` é aplicado sem restrição de origem (linha 15) e o servidor sobe com `debug=True, host='0.0.0.0', port=5000` (linha 34), expondo o host publicamente com o debugger do Werkzeug ativo.
Impact: CORS aberto para qualquer origem combinado com cookies/sessão facilita ataques CSRF; o debugger do Werkzeug em produção pode permitir execução remota de código caso o PIN do debugger seja descoberto ou desabilitado.
Recommendation: Ler `debug` e as origens permitidas de `config/`, com `debug=False` por padrão fora do ambiente local. Ver RP-01 e RP-06.

### #13 [MEDIUM] N+1 queries (AP-13)
File: routes/task_routes.py:41-57
Description: Dentro do laço `for t in tasks:` (linha 16) que lista todas as tasks, o handler executa `User.query.get(t.user_id)` (linha 42) e `Category.query.get(t.category_id)` (linha 51) para cada task individualmente, em vez de usar `join`/eager loading.
Impact: `GET /tasks` dispara até duas queries extras por task retornada; com centenas de tasks a listagem fica lenta e o banco é consultado centenas de vezes para uma única requisição.
Recommendation: Usar `db.session.query(Task).join(User).join(Category)` ou `joinedload`/`selectinload` para carregar os relacionamentos em uma única consulta. Ver RP-08.

### #14 [MEDIUM] N+1 queries (AP-13)
File: routes/report_routes.py:19-28, 55-67, 163
Description: `summary_report` executa cinco `count()` separados para status (linhas 19-22) e cinco para prioridade (linhas 24-28) em vez de um `GROUP BY`; o laço de produtividade por usuário (linha 55, `for u in users:`) consulta `Task.query.filter_by(user_id=u.id).all()` por usuário (linha 56); `get_categories` consulta `Task.query.filter_by(category_id=c.id).count()` dentro do laço `for c in categories:` (linha 163).
Impact: Cada chamada a `/reports/summary` e `/categories` multiplica o número de consultas pelo número de usuários/categorias/status, degradando a resposta conforme a base cresce.
Recommendation: Substituir por consultas agregadas com `GROUP BY`/`func.count()` em uma única query por relatório. Ver RP-08.

### #15 [MEDIUM] Duplicated code (AP-14)
File: routes/task_routes.py:30-39, 71-80, 283-287
File: routes/user_routes.py:171-180
File: routes/report_routes.py:34-37, 132-135
Description: O cálculo "task está atrasada" (`due_date` no passado e status diferente de `done`/`cancelled`) é reimplementado manualmente em seis pontos diferentes do código, embora `Task.is_overdue()` (`models/task.py:50-60`) já exista pronto para isso e nunca seja chamado.
Impact: Qualquer ajuste na regra de atraso (por exemplo, adicionar um novo status que também conta como "fechado") precisa ser replicado em seis lugares; já há risco de divergência, pois as implementações não são idênticas em nome de variável nem estrutura.
Recommendation: Remover as reimplementações e chamar `task.is_overdue()` em todos os pontos. Ver RP-15.

### #16 [MEDIUM] Duplicated code (AP-14)
File: routes/task_routes.py:110-114, 177-183
Description: A validação de `status` (lista `['pending', 'in_progress', 'done', 'cancelled']`) e de `priority` (`priority < 1 or priority > 5`) é escrita por extenso tanto em `create_task` quanto em `update_task`, embora `Task.validate_status`/`Task.validate_priority` (`models/task.py:38-48`) existam com a mesma finalidade e nunca sejam chamados.
Impact: As duas cópias já divergem sutilmente (uma retorna 400 com mensagens diferentes); uma nova regra de prioridade exigiria editar os dois handlers e ainda um terceiro lugar (o model) que ninguém usa.
Recommendation: Centralizar a validação nos métodos do model ou em um validador reutilizável chamado pelo controller. Ver RP-15.

### #17 [MEDIUM] Missing or inconsistent input validation (AP-15)
File: routes/task_routes.py:261, 264
File: requirements.txt:4
Description: Em `search_tasks`, `int(priority)` (linha 261) e `int(user_id)` (linha 264) convertem parâmetros de query string sem `try/except`; um valor não numérico gera `ValueError` não tratado (500 em vez de 400). Além disso, `marshmallow` está listado em `requirements.txt:4` mas não é importado em nenhum arquivo do projeto.
Impact: Uma busca com `?priority=abc` quebra o endpoint com erro interno; a biblioteca de validação declarada como dependência não está, de fato, protegendo nenhuma entrada da API.
Recommendation: Validar e tratar erros de conversão antes do filtro, e adotar `marshmallow` (já instalado) como camada de validação de schema usada pelos controllers. Ver RP-16.

### #18 [MEDIUM] Generic exception handling and error leakage (AP-16)
File: routes/task_routes.py:62, 137, 204, 236
File: routes/user_routes.py:130, 149
File: routes/report_routes.py:186, 207, 221
File: utils/helpers.py:46, 49, 88
Description: Blocos `except:` genéricos (sem tipo de exceção) engolem qualquer erro e retornam uma mensagem fixa de 500, sem logging estruturado nem handler de erro central registrado na aplicação.
Impact: Erros de programação (bug de tipo, atributo inexistente) ficam indistinguíveis de falhas esperadas de banco; depurar um problema em produção exige reproduzir o cenário manualmente, pois a causa real nunca é registrada.
Recommendation: Substituir por tipos de exceção específicos e registrar um error handler central (`@app.errorhandler`) que logue a stack trace e devolva uma resposta padronizada. Ver RP-06.

### #19 [MEDIUM] Deprecated API usage (AP-18)
File: models/task.py:20-21
File: routes/task_routes.py:67, 117, 122, 158, 188, 195, 227
Description: O projeto usa `Query.get()` (ex.: `Task.query.get(task_id)`) e `backref=` em `db.relationship` (`models/task.py:20-21`), ambos legados desde SQLAlchemy 2.0, além de `datetime.utcnow()` espalhado pelo código (ver tabela de Deprecated APIs abaixo), que emite `DeprecationWarning` no Python 3.12 instalado neste ambiente (`flask==3.0.0`, `flask-sqlalchemy==3.1.1`).
Impact: Essas chamadas continuam funcionando hoje, mas quebram na próxima major do SQLAlchemy/Python; `datetime.utcnow()` também gera datetimes "naive" (sem timezone), o que pode causar bugs sutis de comparação de datas.
Recommendation: Migrar para `db.session.get(Model, id)`, `back_populates=` e `datetime.now(timezone.utc)`. Ver RP-10.

### #20 [LOW] Magic numbers and inline literal lists (AP-19)
File: routes/task_routes.py:110, 177
File: routes/user_routes.py:71, 120
File: models/task.py:39, 46
Description: As listas `['pending', 'in_progress', 'done', 'cancelled']` e `['user', 'admin', 'manager']` são escritas por extenso em múltiplos pontos, assim como o intervalo de prioridade `1` a `5`, apesar de `VALID_STATUSES`, `VALID_ROLES` já existirem prontos em `utils/helpers.py:110-111` e serem ignorados por todas as rotas.
Impact: Adicionar um novo status ou role exige caçar todas as ocorrências manualmente; qualquer lista esquecida gera comportamento inconsistente entre endpoints.
Recommendation: Definir essas constantes uma única vez na camada de model e importá-las onde forem necessárias. Ver RP-11.

### #21 [LOW] Poor naming (AP-20)
File: routes/task_routes.py:16
File: routes/user_routes.py:14
File: routes/report_routes.py:10, 33, 55, 59, 119, 157, 161, 167, 190, 211
Description: Variáveis de laço de uma letra (`t`, `u`, `c`) aparecem em todas as rotas; em `summary_report` as variáveis de contagem por prioridade são `p1`..`p5` (`routes/report_routes.py:24-28`); e o blueprint `report_bp` (linha 10) é nomeado "reports" mas também serve as rotas de `/categories` (linhas 157, 167, 190, 211), um domínio diferente.
Impact: A leitura do código exige inferir o que `t`/`u`/`c`/`p3` representam a cada uso; o nome do blueprint engana quem procura as rotas de categoria esperando encontrá-las em um módulo "categories".
Recommendation: Renomear para nomes de domínio (`task`, `user`, `category`) e separar o blueprint de categorias do de relatórios. Ver RP-03 e RP-15.

### #22 [LOW] Dead code and unused imports (AP-21)
File: app.py:7
File: routes/task_routes.py:7
File: routes/user_routes.py:6
File: routes/report_routes.py:7-8
File: utils/helpers.py:3-6, 19-23, 25-29, 31-34, 36-41, 43-50, 52-55, 57-108
File: services/notification_service.py:1-48
File: models/task.py:38-48, 50-60
Description: `app.py:7` importa `os, sys, json` sem uso; `routes/task_routes.py:7` importa `json, os, sys, time` sem uso; `routes/user_routes.py:6` importa `hashlib, json` sem uso; `routes/report_routes.py:7` importa `format_date, calculate_percentage` de `utils/helpers.py` mas nunca os chama. O próprio `utils/helpers.py` importa `os, json, sys, math` sem uso (linhas 3-6) e define sete funções (`validate_email`, `sanitize_string`, `generate_id`, `log_action`, `parse_date`, `is_valid_color`, `process_task_data`) que nenhum outro módulo chama. `services/notification_service.py` inteiro nunca é importado nem instanciado em lugar nenhum do projeto. `Task.validate_status`/`validate_priority`/`is_overdue` (`models/task.py:38-60`) também nunca são chamados pelas rotas, que reimplementam a mesma lógica (ver #15/#16).
Impact: Um desenvolvedor novo perde tempo lendo código morto achando que ele está em uso; a dependência `flask_sqlalchemy`/`smtplib` de `notification_service.py` nunca é exercitada, então um bug ali nunca seria percebido em produção.
Recommendation: Remover os módulos e imports não utilizados (`services/notification_service.py`, `utils/helpers.py` e os imports órfãos), ou religar os métodos do model onde a lógica duplicada vive hoje. Ver RP-15.

### #23 [LOW] Print-based logging (AP-22)
File: routes/task_routes.py:149, 153, 219, 234
File: routes/user_routes.py:83, 89, 147
File: services/notification_service.py:21, 24
File: utils/helpers.py:39, 41
File: seed.py:93-96
Description: Mensagens operacionais ("Task criada", "Usuário deletado", erros de commit) são emitidas com `print(` em vez de um logger configurado, sem nível, timestamp ou destino configurável.
Impact: Não é possível silenciar esses logs em teste nem redirecioná-los para um coletor central; dados de negócio (título da task, nome do usuário) acabam apenas no stdout do processo.
Recommendation: Substituir por `logging.getLogger(__name__)` com níveis apropriados (`info`, `error`). Ver RP-12.

### #24 [LOW] Verbose or deeply nested constructs (AP-23)
File: models/task.py:38-43, 50-60
File: utils/helpers.py:103
File: routes/task_routes.py:141, 210
Description: `Task.validate_status` (linhas 38-43) usa `if cond: return True else: return False` em vez de retornar a condição diretamente; `Task.is_overdue` (linhas 50-60) encadeia quatro níveis de `if` aninhado para um booleano só; `type(tags) == list` (em vez de `isinstance`) aparece em `utils/helpers.py:103` e `routes/task_routes.py:141, 210`.
Impact: Cada nível extra de aninhamento aumenta o custo de leitura e revisão sem adicionar nenhuma regra nova; `type() ==` quebra silenciosamente para subclasses de `list`.
Recommendation: Simplificar para retorno direto da expressão booleana e trocar `type() ==` por `isinstance()`. Ver RP-15.

## Deprecated APIs
| API | File:line | Status | Modern equivalent |
|-----|-----------|--------|-------------------|
| `Model.query.get(id)` / `Query.get()` | routes/task_routes.py:67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155; routes/report_routes.py:105, 192, 213 | Legado desde SQLAlchemy 2.0 (LegacyAPIWarning) | `db.session.get(Model, id)` |
| `db.relationship(..., backref=...)` | models/task.py:20-21 | Legado desde SQLAlchemy 2.0 (ainda funciona) | `back_populates=` nos dois lados do relacionamento |
| `datetime.utcnow()` | models/task.py:15-16, 52; models/user.py:14; models/category.py:11; routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; routes/report_routes.py:35, 42, 45, 71, 133; services/notification_service.py:35; utils/helpers.py:38; seed.py:66-67, 69-70, 74 | DeprecationWarning desde Python 3.12 | `datetime.now(timezone.utc)` |

## Proposed target structure
```
task-manager-api/
├── app.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── task.py
│   └── category.py
├── controllers/
│   ├── __init__.py
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── category_controller.py
│   └── report_controller.py
├── routes/
│   ├── __init__.py
│   ├── task_routes.py
│   ├── user_routes.py
│   ├── category_routes.py
│   └── report_routes.py
├── middlewares/
│   ├── __init__.py
│   ├── error_handler.py
│   └── auth_guard.py
├── database.py
├── seed.py
├── requirements.txt
├── .env.example
└── README.md
```

### Removed
- `services/` (incluindo `services/notification_service.py`) — serviço de envio de e-mail nunca importado nem instanciado em nenhum ponto do projeto (AP-21, achado #22).
- `utils/helpers.py` — funções auxiliares (`validate_email`, `sanitize_string`, `generate_id`, `log_action`, `parse_date`, `is_valid_color`, `process_task_data`) nunca chamadas, e `format_date`/`calculate_percentage` importadas em `routes/report_routes.py:7` mas nunca usadas (AP-21, achado #22). As constantes `VALID_STATUSES`/`VALID_ROLES` migram para dentro dos models antes do arquivo ser removido.

## Contract decisions preview
- Remover o campo `password` da serialização de usuário (`User.to_dict`): nenhuma resposta (`GET/POST/PUT /users`, `POST /login`) voltará a incluir o hash da senha (resolve o achado #2).
- Exigir token de administrador apenas em `DELETE /users/<id>` (operação destrutiva que apaga o usuário e faz cascata sobre suas tasks); `DELETE /tasks/<id>` e `DELETE /categories/<id>` permanecem públicas, como operações de domínio comuns, com a integridade referencial resolvida no schema (constraint de FK) em vez de checagem de permissão (resolve o achado #4, complementa o achado #8).
- Trocar o algoritmo de hash de senha de MD5 para um algoritmo moderno com salt (ex.: `werkzeug.security`); os usuários de seed serão re-hasheados com o novo algoritmo, então hashes antigos não serão mais válidos após a migração (resolve o achado #3).

================================
Total: 24 findings
================================
