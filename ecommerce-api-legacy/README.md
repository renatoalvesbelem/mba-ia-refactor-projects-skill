# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express, refatorada para o padrão MVC a partir do boilerplate original do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe por padrão em `http://localhost:3000`. O banco SQLite é em memória e carrega o schema e os dados de seed automaticamente no boot (usuário Leonan, cursos Clean Architecture e Docker, matrícula e pagamento já existentes).

Exemplos de requisições estão em `api.http`.

## Variáveis de ambiente

Veja `.env.example`. Todas têm um valor padrão seguro apenas para desenvolvimento local; em produção, defina cada uma explicitamente.

| Variável | Uso | Default (dev) |
|----------|-----|----------------|
| `PORT` | porta HTTP do servidor | `3000` |
| `NODE_ENV` | ambiente de execução | `development` |
| `DATABASE_FILE` | caminho do arquivo SQLite (`:memory:` para banco em memória) | `:memory:` |
| `ADMIN_TOKEN` | token exigido no header `X-Admin-Token` para os endpoints administrativos | `dev-admin-token-change-me` (só quando `NODE_ENV=development`; em qualquer outro ambiente é obrigatório) |
| `LOG_LEVEL` | nível do logger (`error`, `warn`, `info`, `debug`) | `info` |

## Layout do projeto

```
src/
├── server.js              # entry point: abre o banco, roda migrate/seed, sobe o servidor
├── app.js                 # createApp({ db, config }) — raiz de composição
├── errors.js               # hierarquia de erros de domínio (AppError e subclasses)
├── logger.js               # logger estruturado com níveis, substitui console.log
├── config/
│   └── index.js            # configuração lida de variáveis de ambiente
├── models/
│   ├── database.js         # abertura do SQLite, wrapper com Promises, migrate e seed
│   ├── userModel.js
│   ├── courseModel.js
│   ├── enrollmentModel.js
│   ├── paymentModel.js
│   └── auditLogModel.js
├── controllers/
│   ├── checkoutController.js
│   ├── financialReportController.js
│   └── userController.js
├── routes/
│   ├── index.js
│   ├── checkoutRoutes.js
│   ├── adminRoutes.js
│   └── userRoutes.js
├── middlewares/
│   ├── errorHandler.js
│   ├── asyncHandler.js
│   └── auth.js              # guarda de admin via header X-Admin-Token
├── services/
│   ├── paymentGateway.js
│   └── passwordHasher.js     # scrypt + salt aleatório via node:crypto
└── validators/
    └── checkoutValidator.js
```

## Endpoints

| Método | Rota | Autenticação | Observação |
|--------|------|---------------|------------|
| POST | `/api/checkout` | nenhuma | fluxo público de compra de curso |
| GET | `/api/admin/financial-report` | header `X-Admin-Token` | antes era público; agora exige o token administrativo |
| DELETE | `/api/users/:id` | header `X-Admin-Token` | antes era público; agora exige o token administrativo |

## Decisões de contrato tomadas na refatoração

- `GET /api/admin/financial-report` e `DELETE /api/users/:id` passaram a exigir o header `X-Admin-Token` (valor igual a `ADMIN_TOKEN`). Sem o header ou com o token errado: `401`. Se `ADMIN_TOKEN` não estiver configurado no ambiente: `503`.
- `DELETE /api/users/:id` agora remove em cascata (via `ON DELETE CASCADE` no schema) as matrículas e pagamentos do usuário, em vez de deixá-los órfãos; a mensagem de sucesso foi atualizada para não mencionar mais a inconsistência que existia antes.
- Senhas de novos usuários criados pelo checkout são geradas com `scrypt` + salt aleatório (`node:crypto`); o usuário de seed (`Leonan`) é re-semeado através do mesmo mecanismo.
- O log do checkout não imprime mais o número do cartão nem a chave do gateway de pagamento; apenas os últimos 4 dígitos do cartão e o status da cobrança.
- Todas as demais respostas (checkout aprovado, checkout recusado, formato do relatório financeiro) mantêm o mesmo status code e corpo da versão original.

O relatório completo da auditoria que motivou esta refatoração está em `../reports/audit-project-2.md` (fora deste diretório, na raiz do repositório de desafios).
