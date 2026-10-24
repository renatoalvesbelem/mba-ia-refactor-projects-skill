================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v20) + Express 4.18.2 (4.22.1 resolvido)
Files:   3 analyzed | ~180 lines of code
Date:    2026-10-03

## Summary
CRITICAL: 5 | HIGH: 5 | MEDIUM: 5 | LOW: 4

## Findings

### #1 [CRITICAL] God file / God class (AP-03)
File: src/AppManager.js:1-141
Description: A classe `AppManager` concentra tudo: o construtor cria a própria conexão SQLite (linha 7), `initDb` cria o schema e insere os seeds (linhas 10-23), e `setupRoutes` contém a implementação completa das três rotas HTTP — parsing, validação, acesso a dados, regras de negócio e serialização — para 5 entidades diferentes (users, courses, enrollments, payments, audit_logs) dentro de um único método (linhas 25-138).
Impact: Nada pode ser testado isoladamente; qualquer mudança em uma rota ou entidade obriga a mexer no mesmo arquivo de 141 linhas, aumentando o risco de conflito e de regressão.
Recommendation: Dividir por camada e por entidade, movendo cada responsabilidade para `models/`, `controllers/` e `routes/`. Ver RP-03.

### #2 [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: src/utils.js:2-5
Description: O objeto `config` grava em texto puro `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"`, `dbUser` e `smtpUser` diretamente no código-fonte versionado.
Impact: Qualquer pessoa com acesso ao repositório tem as credenciais de produção; trocar uma chave vazada exige um novo deploy, e o mesmo valor acaba vazando para todos os ambientes.
Recommendation: Extrair tudo para um módulo de configuração lido de variáveis de ambiente, com defaults seguros apenas para desenvolvimento local, e criar um `.env.example`. Ver RP-01.

### #3 [CRITICAL] Plaintext or weak password storage (AP-05)
File: src/utils.js:17-23 (função `badCrypto`), src/AppManager.js:68-69 (uso no checkout)
Description: `badCrypto` (utils.js:17-23) concatena 10000 vezes os 2 primeiros caracteres de um base64 da senha e corta o resultado em 10 caracteres — não é uma função de hash criptográfico, perde quase toda a entropia da senha original e é usada para gerar a senha de todo novo usuário criado durante o checkout (AppManager.js:68-69).
Impact: Um vazamento do banco expõe senhas em um formato trivialmente reversível/colidível, muito mais fraco que MD5/SHA1.
Recommendation: Substituir por hashing com salt aleatório (scrypt via `node:crypto`, já que nenhuma dependência nova deve ser adicionada). Ver RP-09.

### #4 [CRITICAL] Sensitive data exposure in responses or logs (AP-04)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` imprime o número completo do cartão informado pelo cliente e a chave secreta do gateway de pagamento em texto puro no log do processo, a cada chamada de checkout.
Impact: Qualquer pessoa com acesso aos logs (ou a uma ferramenta de observabilidade) obtém números de cartão e a chave de pagamento — violação direta de PCI e de segredo de produção.
Recommendation: Remover a chave do log e mascarar o cartão (ex.: últimos 4 dígitos). Ver RP-09 e RP-12.

### #5 [CRITICAL] Unprotected dangerous endpoint (AP-06)
File: src/AppManager.js:80-129, 131-137
Description: `GET /api/admin/financial-report` (linha 80) expõe faturamento e dados pessoais (nome e email) de todos os alunos de todos os cursos sem nenhuma verificação de autenticação, apesar do prefixo `/admin/`; `DELETE /api/users/:id` (linha 131) apaga permanentemente um usuário sem qualquer guarda de autorização.
Impact: Qualquer pessoa que alcance o host consegue ler o relatório financeiro completo ou apagar qualquer usuário do sistema.
Recommendation: Proteger ambas as rotas com um middleware de autenticação administrativa baseado em token de configuração. Ver RP-13.

### #6 [HIGH] Tight coupling / no dependency injection (AP-09)
File: src/AppManager.js:5-8, src/app.js:8-10
Description: O construtor de `AppManager` instancia diretamente `new sqlite3.Database(':memory:')` (linha 7); `app.js` cria `new AppManager()` e chama `initDb()`/`setupRoutes()` em sequência (linhas 8-10) sem nenhum ponto de injeção de dependência.
Impact: Impossível rodar um teste unitário sem um banco SQLite real, e trocar a infraestrutura de armazenamento exige editar a classe por dentro.
Recommendation: Criar uma raiz de composição (`createApp({ db })`) que recebe o banco já aberto e monta models/controllers/rotas a partir dele. Ver RP-05.

### #7 [HIGH] Business logic inside route handlers (fat controllers) (AP-07)
File: src/AppManager.js:28-78
Description: O handler de `POST /api/checkout` tem 50 linhas que fazem parsing do body, validação, duas consultas aninhadas, a decisão de aprovação do pagamento, três inserções sequenciais no banco e o registro de cache — tudo dentro do próprio callback da rota Express.
Impact: As regras de checkout só podem ser exercitadas via HTTP, não podem ser reaproveitadas por um job ou teste, e qualquer ajuste de regra mexe no mesmo bloco de código que trata requisição/resposta.
Recommendation: Extrair a lógica para um controller que recebe dados já validados e devolve dados simples; a rota vira apenas parsing + chamada + serialização. Ver RP-04 e RP-16.

### #8 [HIGH] Global mutable state (AP-08)
File: src/utils.js:9-10, 12-15
Description: `globalCache` e `totalRevenue` (linhas 9-10) são variáveis de nível de módulo, mutáveis em tempo de execução; `logAndCache` (linhas 12-15) escreve diretamente em `globalCache` a cada chamada, sem qualquer escopo por requisição.
Impact: Estado compartilhado entre requisições concorrentes, cresce indefinidamente em memória, impossível de isolar em testes e fonte de condições de corrida.
Recommendation: Eliminar o cache global; se um cache for necessário, injetá-lo como dependência com escopo controlado. Ver RP-05 e RP-12.

### #9 [HIGH] Unstructured asynchronous flow (callback pyramid) (AP-10)
File: src/AppManager.js:26, 37-77 (checkout), 83-128 (financial-report)
Description: O checkout aninha callbacks em até 6 níveis e usa `const self = this` (linha 26) para contornar o `this` alterado por `function(err) { this.lastID }` (linhas 50, 54, 57); o relatório financeiro usa contadores manuais de pendência (`coursesPending`, `enrPending`, linhas 86, 93, 97-98, 117-122) para decidir quando finalmente chamar `res.json`.
Impact: Respostas duplicadas ou requisições que nunca respondem caso um branch esqueça de chamar `res`, erros engolidos silenciosamente, e fluxo praticamente impossível de acompanhar lendo o código.
Recommendation: Promisificar o driver SQLite e reescrever os handlers com `async/await`, com um único caminho de retorno. Ver RP-07.

### #10 [HIGH] Missing transaction and data integrity (AP-12)
File: src/AppManager.js:12-16 (schema), 50-62 (checkout), 131-137 (delete)
Description: O schema não define nenhuma `FOREIGN KEY`, `UNIQUE` ou `NOT NULL` (linhas 12-16); o checkout insere `enrollment`, `payment` e `audit_log` em três comandos sequenciais sem transação, podendo deixar uma matrícula sem pagamento se uma etapa falhar no meio (linhas 50-62); `DELETE /api/users/:id` remove o usuário mas deixa matrículas e pagamentos órfãos — fato que a própria mensagem de resposta da API reconhece: "mas as matrículas e pagamentos ficaram sujos no banco" (linha 135).
Impact: Escritas parciais em caso de erro, registros órfãos que corrompem o relatório financeiro, e nenhuma garantia de unicidade de email.
Recommendation: Envolver as escritas relacionadas em uma transação e adicionar as constraints que o domínio exige. Ver RP-14.

### #11 [MEDIUM] N+1 queries (AP-13)
File: src/AppManager.js:89-127
Description: Para cada curso é disparada uma query de matrículas (linha 92); para cada matrícula, mais duas queries (usuário na linha 104, pagamento na linha 106) — o relatório financeiro executa da ordem de `cursos × matrículas × 2` consultas ao invés de agregações no banco.
Impact: O tempo de resposta cresce linearmente com a quantidade de dados; com poucas dezenas de matrículas o endpoint já faz centenas de idas ao banco.
Recommendation: Substituir por uma consulta com JOIN (ou poucas consultas agregadas por `GROUP BY`) e montar o relatório em memória a partir do resultado único. Ver RP-08.

### #12 [MEDIUM] Missing or inconsistent input validation (AP-15)
File: src/AppManager.js:29-35, 132
Description: A validação do checkout (linha 35) exige `usr`, `eml`, `c_id` e `card`, mas não valida `pwd` (que cai silenciosamente para `"123456"` na linha 68) nem o tipo/formato de `c_id` ou `card`; `DELETE /api/users/:id` (linha 132) usa `req.params.id` diretamente em uma query sem checar se é um número válido nem se o usuário existe antes de responder sucesso.
Impact: Entradas inválidas geram comportamento inesperado em vez de um 400 claro, e um id não numérico silenciosamente não apaga nada mas ainda responde como se tivesse apagado.
Recommendation: Criar uma camada de validação compartilhada entre as rotas que usam o mesmo payload. Ver RP-16.

### #13 [MEDIUM] Generic exception handling and error leakage (AP-16)
File: src/AppManager.js:57, 92, 104, 106, 133-136
Description: Vários callbacks recebem `err` e nunca o verificam antes de prosseguir: a linha 57 segue para responder sucesso mesmo que o `INSERT` em `audit_logs` falhe; as linhas 92, 104 e 106 usam o resultado da query sem checar erro; o `DELETE` de usuário (linhas 133-136) ignora `err` completamente e sempre responde como se a operação tivesse funcionado.
Impact: Falhas reais de banco são mascaradas como sucesso para o cliente, dificultando diagnóstico e corrompendo a consistência percebida da API.
Recommendation: Centralizar o tratamento de erro em um middleware único, propagando exceções em vez de ignorá-las. Ver RP-06.

### #14 [MEDIUM] Cross-cutting side effects inside handlers (AP-17)
File: src/AppManager.js:59, src/utils.js:12-15
Description: A chamada a `logAndCache` (AppManager.js:59) mistura um efeito colateral de cache dentro do handler de checkout; `logAndCache` (utils.js:12-15) por sua vez mistura log via `console.log` com gravação em estado global, sem nenhuma camada de serviço isolável.
Impact: O handler acumula motivos para mudar além do fluxo principal, e o efeito colateral não pode ser desligado em teste nem falha de forma isolada.
Recommendation: Mover para um serviço de log/cache invocado pelo controller, não pela rota. Ver RP-04 e RP-12.

### #15 [MEDIUM] Deprecated API usage (AP-18)
File: src/AppManager.js:12-21, 37, 40, 50, 54, 57, 69, 83, 92, 104, 106, 133
Description: Toda a camada de acesso a dados do projeto usa diretamente a API baseada em callbacks do pacote `sqlite3` dentro dos handlers HTTP, em vez de uma API baseada em Promises.
Impact: Não é uma remoção formal, mas é o estilo legado listado no catálogo de deprecação; força o padrão de callback pyramid (achado #9) e dificulta a migração para drivers mais modernos.
Recommendation: Ver RP-10 (e RP-07 para o wrapper de promises).

### #16 [LOW] Poor naming (AP-20)
File: src/AppManager.js:29-33, src/utils.js:12, 17
Description: Variáveis internas de uma ou duas letras (`u`, `e`, `p`, `cid`, `cc`, linhas 29-33) escondem o que cada valor representa; `logAndCache` (utils.js:12) mistura duas responsabilidades no próprio nome; `badCrypto` (utils.js:17) já declara no nome que a implementação é ruim.
Impact: Custo de leitura maior e premissas erradas em revisões de código.
Recommendation: Renomear os identificadores internos ao extrair as camadas. Os nomes de campo do contrato público (`usr`, `eml`, `pwd`, `c_id`, `card`) permanecem inalterados por serem parte do contrato. Ver RP-03/RP-15.

### #17 [LOW] Magic numbers and inline literal lists (AP-19)
File: src/AppManager.js:46, 68; src/utils.js:19
Description: `cc.startsWith("4")` (AppManager.js:46) usa o literal `"4"` para decidir aprovação do cartão sem nenhuma constante nomeada; `"123456"` (AppManager.js:68) é uma senha padrão embutida no código; o laço de `badCrypto` repete 10000 vezes (utils.js:19) um número mágico sem explicação.
Impact: Mudar a regra de aprovação ou a senha padrão exige caçar o literal no meio do código.
Recommendation: Extrair para constantes nomeadas junto da entidade/serviço correspondente. Ver RP-11.

### #18 [LOW] Dead code and unused imports (AP-21)
File: src/utils.js:10, 25; src/AppManager.js:2
Description: `totalRevenue` é declarada e exportada (utils.js:10 e 25) e importada em `AppManager.js:2`, mas nunca é lida ou atualizada em nenhum lugar do projeto.
Impact: Confunde quem lê o código, sugerindo um cálculo de faturamento que não existe.
Recommendation: Remover a variável morta. Ver RP-15.

### #19 [LOW] Print-based logging (AP-22)
File: src/utils.js:13; src/AppManager.js:45; src/app.js:13
Description: `console.log` é usado como log operacional em três pontos: gravação de cache (utils.js:13), log sensível de pagamento (AppManager.js:45) e banner de start (app.js:13) — sem níveis, timestamps ou possibilidade de silenciar em teste.
Impact: Nenhum controle sobre o que é logado em produção; dados sensíveis acabam no stdout (ver achado #4).
Recommendation: Substituir por um logger estruturado mínimo com níveis. Ver RP-12.

## Deprecated APIs
| API | File:line | Status | Modern equivalent |
|-----|-----------|--------|-------------------|
| callback-only `sqlite3` package driving request handlers | src/AppManager.js:12-21, 37, 40, 50, 54, 57, 69, 83, 92, 104, 106, 133 | estilo legado (não removido, mas desencorajado no catálogo) | `node:sqlite` (Node 22+), `better-sqlite3`, ou wrapper com `util.promisify` |

Verificado contra o restante da tabela de APIs deprecadas: **Express 4** (`res.send(statusCode)`, `res.json(obj, status)`, `app.del()`, `req.param()`, `res.sendfile()`, `bodyParser.json()`) **não se aplica** — o projeto já usa `express.json()` nativo (app.js:6), não há nenhum `res.send()` com código numérico, nem uso de `app.del()`/`req.param()`/`bodyParser`. **Annex B string methods** (`substr()`, `escape()`/`unescape()`) **não se aplica** — o código usa `substring()` (utils.js:20, 22), que já é a forma moderna, e não usa `escape`/`unescape`. `new Buffer(...)` também não é usado — já usa `Buffer.from()` (utils.js:20).

## Proposed target structure
```
ecommerce-api-legacy/
├── src/
│   ├── server.js                 # entry point: abre o DB, roda migrate/seed, createApp(...).listen(...)
│   ├── app.js                    # createApp({ db }) — composition root
│   ├── errors.js                 # AppError e subclasses (ValidationError, NotFoundError, PaymentDeniedError, AuthError)
│   ├── logger.js                 # logger mínimo com níveis, substitui console.log
│   ├── config/
│   │   └── index.js               # process.env com defaults seguros para dev local
│   ├── models/
│   │   ├── database.js            # abre o sqlite3, promisifica run/get/all/exec, migrate(db), seed(db)
│   │   ├── userModel.js
│   │   ├── courseModel.js
│   │   ├── enrollmentModel.js
│   │   ├── paymentModel.js
│   │   └── auditLogModel.js
│   ├── controllers/
│   │   ├── checkoutController.js
│   │   ├── financialReportController.js
│   │   └── userController.js
│   ├── routes/
│   │   ├── index.js               # monta os sub-roteadores sob /api
│   │   ├── checkoutRoutes.js
│   │   ├── adminRoutes.js
│   │   └── userRoutes.js
│   ├── middlewares/
│   │   ├── errorHandler.js
│   │   ├── asyncHandler.js
│   │   └── auth.js                # requireAdmin (X-Admin-Token)
│   ├── services/
│   │   ├── paymentGateway.js
│   │   └── passwordHasher.js      # scrypt + salt via node:crypto
│   └── validators/
│       └── checkoutValidator.js
├── .env.example
├── api.http
├── package.json
└── README.md
```

## Contract decisions preview
- `GET /api/admin/financial-report` passa a exigir o header `X-Admin-Token` igual ao valor de `ADMIN_TOKEN`; sem header ou com token incorreto responde `401`; se `ADMIN_TOKEN` não estiver configurado no ambiente, responde `503`. (resolve #5)
- `DELETE /api/users/:id` passa a exigir o mesmo header `X-Admin-Token`; a exclusão passa a remover, em uma única transação, os `enrollments` e `payments` do usuário junto com o registro em `users`, em vez de deixar órfãos; a mensagem de sucesso deixa de mencionar sujeira no banco. (resolve #5 e parte do #10)
- Senhas passam a ser armazenadas com `scrypt` + salt aleatório (`node:crypto`); o usuário seed "Leonan" é re-semeado através do mesmo hashing, preservando o fluxo de checkout documentado em `api.http`/README. (resolve #3)
- O log do checkout deixa de imprimir o número do cartão e a chave do gateway; passa a logar apenas o status da cobrança e os últimos 4 dígitos do cartão. (resolve #4)
- Credenciais, porta, chave do gateway e admin token passam a vir de variáveis de ambiente, com defaults seguros apenas para desenvolvimento local. (resolve #2)
- Todas as demais respostas (checkout aprovado, checkout recusado, formato do relatório financeiro) mantêm status code e formato idênticos aos atuais.

================================
Total: 19 findings
================================
