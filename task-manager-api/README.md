# task-manager-api

API de Task Manager em Python/Flask. O projeto foi reorganizado para o padrão MVC a partir de uma base com camadas parciais (`models/`, `routes/`, `services/`, `utils/`), mantendo os nomes de pastas já existentes e adicionando as camadas que faltavam (`config/`, `controllers/`, `middlewares/`, `schemas/`).

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe por padrão em `http://127.0.0.1:5000`. O `seed.py` popula o banco SQLite (`tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias. Os usuários de exemplo continuam os mesmos:

| Email | Senha | Role |
|-------|-------|------|
| joao@email.com | 1234 | admin |
| maria@email.com | abcd | user |
| pedro@email.com | pass | manager |

## Estrutura do projeto

```
task-manager-api/
├── app.py                 # composition root: cria a app, registra config/db/rotas/erros
├── database.py             # instância do SQLAlchemy (db)
├── config/
│   └── settings.py         # leitura de variáveis de ambiente (nenhum segredo hardcoded)
├── models/
│   ├── base.py              # utc_now() e utilitários compartilhados
│   ├── task.py               # entidade Task + regras (is_overdue, status/prioridade)
│   ├── user.py                # entidade User + hashing de senha (werkzeug)
│   └── category.py            # entidade Category + contagem agregada de tasks
├── schemas/                 # validação de entrada com marshmallow (reusada por create/update)
│   ├── task_schema.py
│   ├── user_schema.py
│   └── category_schema.py
├── controllers/               # orquestram os casos de uso (regra de negócio, sem HTTP)
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── category_controller.py
│   ├── report_controller.py
│   └── schema_utils.py
├── routes/                    # bind HTTP -> controller (rotas finas)
│   ├── task_routes.py
│   ├── user_routes.py
│   ├── category_routes.py      # separado de report_routes.py (antes servia /categories)
│   └── report_routes.py
├── middlewares/
│   ├── error_handler.py        # exceções de domínio + handlers centralizados
│   └── auth.py                  # guard de admin (X-Admin-Token) para DELETE /users/<id>
├── seed.py
├── .env.example
└── requirements.txt
```

## Variáveis de ambiente

Todas lidas em `config/settings.py`, com defaults seguros para desenvolvimento local (ver `.env.example`):

| Variável | Default | Descrição |
|----------|---------|-----------|
| `SECRET_KEY` | `dev-only-change-me` | chave de sessão do Flask |
| `FLASK_DEBUG` | `0` | `1` liga o modo debug |
| `HOST` | `127.0.0.1` | host de bind do servidor |
| `PORT` | `5000` | porta do servidor |
| `DATABASE_URL` | `sqlite:///tasks.db` | URI do banco (SQLAlchemy) |
| `CORS_ORIGINS` | `*` | origens permitidas pelo CORS |
| `ADMIN_TOKEN` | `dev-admin-token-change-me` só quando `APP_ENV=development` | token exigido no header `X-Admin-Token` para `DELETE /users/<id>`. Fora de desenvolvimento é obrigatório configurar; sem valor a rota responde `503`. |
| `APP_ENV` | `development` | nome do ambiente |

## Mudanças de contrato em relação à versão anterior

- Respostas que serializam um usuário (`GET /users`, `GET /users/<id>`, `POST /users`, `PUT /users/<id>`, `POST /login`) **não retornam mais o campo `password`** (o hash da senha).
- `DELETE /users/<id>` (apaga o usuário e todas as tasks dele) agora exige o header `X-Admin-Token` com o valor de `ADMIN_TOKEN`. Sem o header ou com um valor errado: `401`. Sem `ADMIN_TOKEN` configurado no servidor: `503`. `DELETE /tasks/<id>` e `DELETE /categories/<id>` continuam públicos como antes, por serem operações normais do domínio.
- `services/notification_service.py` e `utils/helpers.py` foram removidos: o primeiro nunca era chamado e carregava credenciais SMTP; o segundo só tinha funções e constantes que as rotas reimplementavam inline (o que era útil foi absorvido por `models/` e `schemas/`).
- O hash de senha interno passou de MD5 para `werkzeug.security` (PBKDF2); os usuários da seed continuam acessando `/login` com as mesmas senhas documentadas acima.
- Os objetos de task retornados por `POST /tasks`, `PUT /tasks/<id>`, `GET /tasks/search` e pela lista aninhada em `GET /users/<id>` agora sempre incluem o campo `overdue` (antes só aparecia em `GET /tasks` e `GET /tasks/<id>`), unificando a serialização que antes divergia entre endpoints.
- `DELETE /categories/<id>` não deixa mais tasks com uma `category_id` órfã: a foreign key agora limpa (`SET NULL`) o vínculo automaticamente.
