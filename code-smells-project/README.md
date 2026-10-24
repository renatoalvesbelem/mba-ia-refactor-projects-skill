# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`. O projeto segue o padrão MVC: rotas finas (`routes/`), controllers que orquestram os casos de uso (`controllers/`), models com acesso a dados e regras de domínio (`models/`), validação de entrada isolada (`validators/`), notificações como serviço (`services/`) e configuração/erros centralizados (`config/`, `middlewares/`).

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://0.0.0.0:5000` por padrão. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (as senhas de seed já nascem com hash).

## Estrutura do projeto

```
code-smells-project/
├── app.py                     # composition root: cria a app, registra config/db/rotas
├── config/
│   └── settings.py            # leitura de variáveis de ambiente
├── models/
│   ├── base.py                 # conexão por requisição, schema e seed
│   ├── produto_model.py
│   ├── usuario_model.py
│   ├── pedido_model.py
│   └── sistema_model.py
├── controllers/
│   ├── produto_controller.py
│   ├── usuario_controller.py
│   ├── pedido_controller.py
│   └── sistema_controller.py
├── routes/
│   ├── produto_routes.py
│   ├── usuario_routes.py
│   ├── pedido_routes.py
│   └── sistema_routes.py
├── validators/
│   ├── produto_validator.py
│   ├── usuario_validator.py
│   └── pedido_validator.py
├── services/
│   └── notificacao_service.py  # notificações de pedido (log estruturado)
├── middlewares/
│   ├── error_handler.py        # exceções de domínio + handler central
│   └── auth.py                 # guard de token para rotas administrativas
└── .env.example
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SECRET_KEY` | `dev-only-change-me` | Chave de assinatura do Flask. Defina um valor real fora do ambiente local. |
| `FLASK_DEBUG` | `0` | `1` liga o modo debug do Flask (nunca usar `1` em produção). |
| `HOST` | `0.0.0.0` | Host de bind do servidor. |
| `PORT` | `5000` | Porta de bind do servidor. |
| `DATABASE_PATH` | `loja.db` | Caminho do arquivo SQLite. |
| `CORS_ORIGINS` | `*` | Origens permitidas pelo CORS. |
| `ADMIN_TOKEN` | `dev-admin-token-change-me` só quando `APP_ENV=development` | Token exigido no header `X-Admin-Token` pelas rotas `/admin/*`. Fora de desenvolvimento é obrigatório configurar; sem valor essas rotas respondem `503`. |
| `APP_ENV` | `development` | Quando `production`, `/admin/reset-db` é recusado com `403`. |

Copie `.env.example` para `.env` (ou exporte as variáveis) para customizar.

## Rotas administrativas

- `POST /admin/reset-db`: exige `X-Admin-Token` igual a `ADMIN_TOKEN` e é recusada quando `APP_ENV=production`.
- `POST /admin/query`: exige `X-Admin-Token` e aceita apenas instruções `SELECT` (execução de SQL arbitrário foi removida por segurança).

## Decisões de contrato em relação à versão original

- `GET /usuarios` e `GET /usuarios/<id>` não retornam mais o campo `senha`.
- `GET /health` não retorna mais `secret_key`, `debug`, `db_path` nem `ambiente`.
- Senhas são armazenadas com hash (`werkzeug.security`) e comparadas por hash no login.
- `POST /admin/query` aceita somente `SELECT` e exige token administrativo.
- `POST /admin/reset-db` exige token administrativo e é bloqueada em `APP_ENV=production`.
- Todas as respostas de erro passam a incluir `sucesso: false` ao lado de `erro`, mesmo quando a versão original omitia essa chave.
- `atualizar_produto` (PUT) passa a validar o tamanho do nome (2 a 200 caracteres), igual ao `criar_produto`.

Nenhuma outra rota, status code ou formato de resposta foi alterado.
