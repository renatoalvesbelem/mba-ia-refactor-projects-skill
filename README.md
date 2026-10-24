# Refatoração arquitetural automatizada com uma Skill do Claude Code

Entrega do desafio "Criação de Skills — Refatoração Arquitetural Automatizada" do MBA em Engenharia de Software com IA (Full Cycle). O enunciado completo está no [repositório base](https://github.com/devfullcycle/mba-ia-refactor-projects-skill).

A ideia é simples de descrever e chata de fazer na mão: pegar três projetos legados (dois em Python/Flask e um em Node/Express), auditar os problemas de arquitetura, segurança e qualidade, e refatorar tudo para MVC sem quebrar os endpoints. A skill `refactor-arch` faz isso em três fases, parando antes de alterar qualquer arquivo para o humano aprovar o relatório.

Ferramenta usada: **Claude Code** (skill em `.claude/skills/refactor-arch/`).

Estrutura deste repositório:

```
.
├── README.md
├── code-smells-project/        # projeto 1 (Python/Flask, e-commerce) — refatorado
│   └── .claude/skills/refactor-arch/
├── ecommerce-api-legacy/       # projeto 2 (Node/Express, LMS + checkout) — refatorado
│   └── .claude/skills/refactor-arch/
├── task-manager-api/           # projeto 3 (Python/Flask, task manager) — refatorado
│   └── .claude/skills/refactor-arch/
├── reports/
│   ├── audit-project-1.md      # saída da Fase 2 em cada projeto
│   ├── audit-project-2.md
│   └── audit-project-3.md
└── logs/
    ├── project-1-run.log       # fases 1 e 3 + evidência de boot e chamadas aos endpoints
    ├── project-2-run.log
    └── project-3-run.log
```

---

## 1. Análise Manual

Antes de escrever a skill li os três projetos inteiros. A lista abaixo não é exaustiva (o relatório gerado pela skill é mais completo), mas foi o que eu precisava para saber que sinais o catálogo tinha que detectar. A escala de severidade é a do enunciado.

### 1.1 code-smells-project (Python/Flask, API de e-commerce)

Quatro arquivos na raiz (`app.py`, `controllers.py`, `models.py`, `database.py`), sem pacote, sem config, sem camada de validação. Os nomes sugerem MVC mas o conteúdo não: `models.py` tem SQL, regra de negócio e serialização; `controllers.py` tem validação, fluxo e "notificação" via `print`; `app.py` tem rotas administrativas que falam direto com o banco.

| # | Severidade | Problema | Onde | Por que importa |
|---|------------|----------|------|-----------------|
| 1 | CRITICAL | SQL injection em praticamente todas as queries, montadas por concatenação de string | `models.py:28`, `48-49`, `58-60`, `68`, `92`, `110`, `127-128`, `140`, `148-166`, `174`, `188`, `192`, `220`, `224`, `280`, `291-297` | O login (`models.py:110`) é contornável com `' OR '1'='1`. Qualquer campo de produto permite destruir o banco. Também esconde erro de tipo: um preço enviado como string vai direto para o SQL. |
| 2 | CRITICAL | Endpoint `POST /admin/query` executa SQL arbitrário vindo do body, sem autenticação; `POST /admin/reset-db` apaga todas as tabelas | `app.py:47-78` | É execução remota de comandos no banco por qualquer um que alcance a porta. |
| 3 | CRITICAL | `SECRET_KEY` hardcoded e senhas dos usuários seed em texto puro | `app.py:7`, `database.py:76-78` | Segredo versionado no repositório, igual em todos os ambientes. |
| 4 | CRITICAL | Senhas armazenadas e comparadas em texto puro; `/health` devolve `secret_key`, `debug` e caminho do banco; `GET /usuarios` devolve o campo `senha` | `models.py:110`, `127-128`; `controllers.py:285-289`; `models.py:83`, `99` | Vazamento direto de credenciais para qualquer consumidor da API. |
| 5 | HIGH | Lógica de negócio e validação dentro dos handlers (controllers gordos) | `controllers.py:24-62`, `64-96`, `188-220`, `237-255` | As regras só existem por trás do HTTP; `criar_produto` e `atualizar_produto` repetem a mesma cadeia de `if` com diferenças sutis (a validação de categoria só existe no create). |
| 6 | HIGH | Conexão SQLite em variável global de módulo com `check_same_thread=False` | `database.py:4-10` | Estado mutável compartilhado entre requisições, sem fechamento, impossível de substituir em teste. |
| 7 | HIGH | `debug=True`, `host="0.0.0.0"` e `CORS(app)` sem restrição | `app.py:8-9`, `88` | O debugger do Werkzeug exposto na rede permite executar código Python remotamente. |
| 8 | MEDIUM | N+1: listagem de pedidos abre `cursor2`/`cursor3` por pedido e por item; `criar_pedido` consulta o mesmo produto duas vezes por item; relatório faz 5 queries de contagem | `models.py:177-200`, `209-232`, `139-166`, `239-254` | Tempo de resposta cresce linearmente com o número de pedidos. |
| 9 | MEDIUM | Serialização de linhas duplicada em cinco funções | `models.py:12-21`, `31-40`, `79-86`, `95-102`, `304-313` | Qualquer campo novo precisa ser adicionado em cinco lugares. |
| 10 | MEDIUM | `except Exception as e` em todos os handlers devolvendo `str(e)` ao cliente; nenhum error handler central | `controllers.py:10-12`, `21-22`, `60-62`, ... | Vaza detalhes internos e esconde o stack trace de quem precisa dele. |
| 11 | MEDIUM | Validação incompleta: `preco`/`estoque` comparados com `< 0` sem checar tipo; `float()` dos filtros de busca sem tratamento | `controllers.py:43-46`, `118-121` | Payload com string gera 500 em vez de 400. |
| 12 | LOW | Listas e limiares mágicos inline (categorias válidas, status de pedido, faixas de desconto) | `controllers.py:52`, `242`; `models.py:257-262` | Regras de negócio espalhadas e sem nome. |
| 13 | LOW | Logging com `print`, inclusive para "enviar e-mail/SMS/push" | `controllers.py:8`, `11`, `57`, `161`, `179-182`, `208-210`, `248-250`; `app.py:56`, `83-86` | Sem nível, sem destino, dados de usuário no stdout. |
| 14 | LOW | Imports não usados (`sqlite3` em `models.py`, `os` em `database.py`) e variáveis `cursor2`/`cursor3`, parâmetro `id` sombreando o builtin | `models.py:2`, `187`, `191`; `database.py:2`; `controllers.py:14` | Ruído de leitura. |

Sobre APIs deprecated: para esta stack (Flask 3.1 + `sqlite3` da stdlib em Python 3.12) não encontrei nada que o catálogo marque como deprecated. Isso foi útil para testar se a skill sabe dizer "nenhuma" em vez de inventar.

### 1.2 ecommerce-api-legacy (Node.js/Express, LMS com checkout)

Três arquivos em `src/`. `AppManager.js` é literalmente uma God class: cria o banco em memória, define o schema, faz seed, registra as rotas e implementa checkout, relatório financeiro e exclusão de usuário dentro de callbacks aninhados. `utils.js` guarda as credenciais e um "hash" de senha caseiro.

| # | Severidade | Problema | Onde | Por que importa |
|---|------------|----------|------|-----------------|
| 1 | CRITICAL | Credenciais hardcoded: senha de banco, chave `pk_live_` do gateway de pagamento, usuário SMTP | `src/utils.js:1-7` | Segredos de produção versionados. |
| 2 | CRITICAL | God class `AppManager` com DB, schema, seed, rotas, pagamento, matrícula e auditoria | `src/AppManager.js:4-139` | Nada é testável isoladamente; qualquer mudança passa pelo mesmo arquivo. |
| 3 | CRITICAL | Número completo do cartão e chave do gateway escritos no log | `src/AppManager.js:45` | Dado de cartão em log é violação de PCI e de bom senso. |
| 4 | CRITICAL | `badCrypto` (base64 repetido 10 mil vezes, 10 caracteres) como "hash" de senha; usuário seed com senha `'123'` em texto puro; senha padrão `"123456"` quando o campo não vem | `src/utils.js:17-23`; `src/AppManager.js:18`, `68` | Reversível e previsível; contas criadas sem senha. |
| 5 | CRITICAL | `DELETE /api/users/:id` sem nenhuma autenticação e deixando matrículas e pagamentos órfãos (a própria mensagem de resposta admite) | `src/AppManager.js:131-137` | Qualquer pessoa apaga qualquer usuário e corrompe o relatório financeiro. |
| 6 | HIGH | Callback hell com até 6 níveis no checkout e contadores manuais (`coursesPending--`, `enrPending--`) para decidir quando responder no relatório | `src/AppManager.js:37-77`, `83-128` | Resposta pode ser enviada duas vezes ou nunca; erros das queries internas são ignorados. |
| 7 | HIGH | Toda a regra de negócio do checkout (buscar curso, criar usuário, "cobrar" cartão, matricular, pagar, auditar, cachear) dentro do handler da rota | `src/AppManager.js:28-78` | Impossível reaproveitar ou testar o fluxo sem subir o Express. |
| 8 | HIGH | Estado global mutável: `globalCache` e `totalRevenue` no módulo; DB instanciado no construtor (`new sqlite3.Database(':memory:')`) sem injeção | `src/utils.js:9-15`, `25`; `src/AppManager.js:7`; `src/app.js:8-10` | Acoplamento oculto, memória que só cresce, nenhuma forma de trocar o banco. |
| 9 | HIGH | Checkout insere usuário, matrícula, pagamento e auditoria em quatro `run` separados, sem transação; schema sem foreign keys | `src/AppManager.js:12-16`, `50-63`, `69-72` | Falha no meio deixa matrícula sem pagamento. |
| 10 | MEDIUM | N+1 no relatório financeiro: uma query por curso, uma por matrícula, duas por aluno | `src/AppManager.js:89-127` | Com 100 cursos e 1000 alunos são milhares de queries por request. |
| 11 | MEDIUM | `err` ignorado em vários callbacks (`audit_logs`, `enrollments`, `users`, `delete`) | `src/AppManager.js:57`, `92`, `104`, `106`, `133` | Falhas silenciosas. |
| 12 | MEDIUM | Validação ausente: `pwd` não é obrigatório embora seja usado, `card` nunca é validado, `c_id` não é convertido; aprovação de pagamento decidida por `cc.startsWith("4")` dentro do handler | `src/AppManager.js:29-35`, `46` | Regra de pagamento fake misturada com HTTP e sem contrato de entrada. |
| 13 | MEDIUM | Driver `sqlite3` usado só pela API de callbacks (estilo legado) quando o Node 20 já permite `util.promisify`/wrappers em promise | `src/AppManager.js` inteiro | É a causa raiz do item 6. |
| 14 | LOW | Nomes: `u`, `e`, `p`, `cid`, `cc`, `self`, campos `usr`/`eml`/`pwd`/`c_id` no contrato público | `src/AppManager.js:26`, `29-33` | Custo de leitura alto. |
| 15 | LOW | Números mágicos (`10000` iterações, `substring(0, 10)`, `startsWith("4")`) e `console.log` como logging | `src/utils.js:13`, `19`, `22`; `src/AppManager.js:45-46`; `src/app.js:13` | Sem nome, sem nível de log. |
| 16 | LOW | `totalRevenue` exportado e importado mas nunca usado; mensagem de resposta do delete descrevendo o bug | `src/utils.js:10`, `25`; `src/AppManager.js:2`, `135` | Código morto e texto de debug no contrato. |

### 1.3 task-manager-api (Python/Flask + SQLAlchemy, task manager)

Este é o mais interessante porque parece organizado: tem `models/`, `routes/`, `services/`, `utils/`. Só que as rotas importam `db` direto, fazem query, validam e commitam; não existe camada de controller; `utils/helpers.py` tem constantes e validadores que ninguém usa enquanto as rotas reimplementam a mesma coisa inline; e `services/notification_service.py` nunca é chamado mas carrega senha de SMTP.

| # | Severidade | Problema | Onde | Por que importa |
|---|------------|----------|------|-----------------|
| 1 | CRITICAL | `User.to_dict()` inclui o hash da senha, devolvido por `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `/login` | `models/user.py:21`; `routes/user_routes.py:33`, `85`, `129`, `209` | Vazamento de hash para todo cliente da API. |
| 2 | CRITICAL | Senhas com MD5 sem salt | `models/user.py:29`, `32` | Quebrável por rainbow table em segundos. |
| 3 | CRITICAL | `SECRET_KEY` hardcoded e credenciais SMTP (`taskmanager@gmail.com` / `senha123`) no código | `app.py:13`; `services/notification_service.py:7-10` | Segredos versionados. |
| 4 | HIGH | Regras de negócio, validação, queries e commit dentro das rotas (não há controllers); rotas importam `db` diretamente | `routes/task_routes.py:85-154`, `156-223`; `routes/user_routes.py:42-90`; `routes/report_routes.py:12-101` | A "organização" é só de pastas; a direção de dependência está invertida. |
| 5 | HIGH | `debug=True`, `0.0.0.0`, `CORS(app)` aberto e `/login` devolvendo `'fake-jwt-token-' + id` sem nenhuma rota protegida | `app.py:15`, `34`; `routes/user_routes.py:210` | Debugger exposto e autenticação de fachada. |
| 6 | HIGH | `NotificationService` guarda estado em `self.notifications` (lista que só cresce) e é código morto | `services/notification_service.py:4-11` | Estado mutável + serviço inexistente na prática. |
| 7 | MEDIUM | N+1: `User.query.get` e `Category.query.get` por task na listagem; tasks por usuário em loop no relatório; `count()` por categoria em loop | `routes/task_routes.py:41-57`; `routes/report_routes.py:53-68`, `163` | Queries proporcionais ao número de registros. |
| 8 | MEDIUM | Cálculo de `overdue` copiado seis vezes (com `if` de quatro níveis) enquanto `Task.is_overdue()` existe e não é usado | `routes/task_routes.py:30-39`, `71-80`, `284-287`; `routes/user_routes.py:171-180`; `routes/report_routes.py:33-43`, `132-135`; `models/task.py:50-60` | Duplicação clássica, qualquer mudança na regra precisa de seis edições. |
| 9 | MEDIUM | Validação duplicada entre create e update; `process_task_data`, `validate_email`, `is_valid_color` e as constantes `VALID_STATUSES`/`VALID_ROLES` em `utils/helpers.py` nunca usados; `marshmallow` instalado e não usado | `routes/task_routes.py:92-114` vs `166-183`; `utils/helpers.py:19-23`, `52-116` | Duas fontes de verdade e uma biblioteca de validação parada no `requirements.txt`. |
| 10 | MEDIUM | `except:` nu em vários handlers, com `rollback()` repetido em cada um; nenhum error handler global | `routes/task_routes.py:62`, `137`, `204`, `236`; `routes/user_routes.py:130`, `149`; `routes/report_routes.py:186`, `207`, `221` | Erros reais engolidos. |
| 11 | MEDIUM | APIs deprecated: `Model.query.get()` (LegacyAPIWarning no SQLAlchemy 2.x), `datetime.utcnow()` (DeprecationWarning no Python 3.12), `backref=` | `routes/task_routes.py:42`, `51`, `67`, `117`, `122`, `158`, `188`, `195`, `227`; `routes/user_routes.py:29`, `94`, `136`, `155`; `routes/report_routes.py:105`, `192`, `213`; `models/task.py:15-16`, `20-21`, `52`; `models/user.py:14`; `models/category.py:11` | Vai quebrar na próxima major; `utcnow` ainda gera datetimes sem timezone. |
| 12 | MEDIUM | Relatório faz 5 queries de contagem por status e 5 por prioridade, depois carrega todas as tasks para contar atrasadas em Python | `routes/report_routes.py:15-43`; `routes/task_routes.py:275-287` | Um `GROUP BY` resolve. |
| 13 | LOW | Imports não usados em quase todos os módulos (`os, sys, json, datetime` em `app.py`; `json, os, sys, time` em `task_routes.py`; `hashlib, json` em `user_routes.py`; `format_date`, `calculate_percentage`, `json` em `report_routes.py`; `os, json, sys, math, hashlib` em `helpers.py`) | `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `routes/report_routes.py:7-8`; `utils/helpers.py:3-7` | Linter vermelho, leitura enganosa. |
| 14 | LOW | Listas mágicas inline (`['pending', 'in_progress', 'done', 'cancelled']`, `['user', 'admin', 'manager']`, `< 1 or > 5`, `< 4`) repetidas nas rotas apesar das constantes existirem em `helpers.py` | `routes/task_routes.py:110`, `113`, `177`, `182`; `routes/user_routes.py:64`, `71`, `120` | Regras sem nome e sem dono. |
| 15 | LOW | `print` para log, `if x: return True else: return False`, `type(tags) == list`, `x = x + 1` | `routes/task_routes.py:149`, `153`, `219`, `234`; `models/task.py:38-48`; `models/user.py:34-38`; `routes/task_routes.py:141`, `210`; `routes/report_routes.py:37`, `61` | Legibilidade. |
| 16 | LOW | `report_routes.py` (blueprint `reports`) serve o CRUD de `/categories` | `routes/report_routes.py:157-223` | Nome mente sobre o conteúdo. |

O que eu tirei disso para a skill: os três projetos compartilham os mesmos sinais (credencial literal, query por concatenação ou callback, lógica no handler, N+1 em loop, duplicação de serialização, `print`, import morto), só que escritos em idiomas diferentes. O catálogo tinha que descrever o **sinal** e deixar o agente traduzir para a linguagem, em vez de ter uma lista por stack.

---

## 2. Construção da Skill

### 2.1 Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                            # o "prompt": fases, regras, formato de saída, gate de confirmação
└── references/
    ├── analysis-heuristics.md          # Fase 1: detecção de linguagem/framework/banco, mapa de responsabilidades, classificação da arquitetura
    ├── anti-patterns.md                # Fase 2: catálogo AP-01..AP-23 com sinais, severidade, tabela de APIs deprecated e cheat sheet de grep
    ├── report-template.md              # Fase 2: formato exato do relatório e regras de ordenação
    ├── mvc-guidelines.md               # Fase 3: camadas, direção de dependência, árvores alvo, regras de preservação de contrato
    └── refactoring-playbook.md         # Fase 3: RP-01..RP-16, cada um com passos e código antes/depois
```

Decisões que tomei e por quê:

- **`SKILL.md` curto, conhecimento nas referências.** O `SKILL.md` diz *o que* fazer em cada fase, em que ponto ler cada referência, e o formato exato dos blocos de saída (copiei o formato do enunciado). O conhecimento de domínio fica nos arquivos de referência, que são carregados sob demanda. Isso segue a ideia de *progressive disclosure* do guia da Anthropic: o agente não precisa do playbook inteiro na Fase 1.
- **IDs cruzados.** Cada anti-pattern tem um `AP-xx` e aponta para um ou mais `RP-xx` do playbook. O relatório da Fase 2 cita os dois, e o resumo da Fase 3 lista finding por finding como foi resolvido. Isso evita que a refatoração "esqueça" um achado e deixa o relatório auditável.
- **Gate obrigatório.** A Fase 2 termina com a pergunta `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e a instrução explícita de que nada pode ser criado, editado ou apagado antes de um "sim" (o `SKILL.md` manda usar `AskUserQuestion` quando disponível). As fases 1 e 2 são declaradas read-only; o único arquivo que a Fase 2 escreve é o próprio relatório.
- **Baseline antes de refatorar.** A Fase 3 começa subindo a aplicação original numa porta livre e gravando status e body de todas as rotas mapeadas na Fase 1. Depois da refatoração, repete as chamadas e compara. Sem isso "a aplicação continua funcionando" seria só uma frase.
- **Decisões de contrato explícitas.** Alguns achados não têm como ser corrigidos sem mudar comportamento (`/health` devolvendo a `SECRET_KEY`, `/admin/query` executando SQL arbitrário, `to_dict` com hash de senha). As guidelines têm uma tabela fechada do que pode mudar e como (remover o campo, exigir token administrativo, etc.); tudo fora da tabela precisa perguntar. Essas mudanças aparecem numa seção própria do relatório e do resumo final.
- **Adaptação a projetos parcialmente organizados.** Uma seção das guidelines diz o que fazer quando `models/` e `routes/` já existem: manter nomes, adicionar as camadas que faltam, afinar as rotas, consertar a direção de dependência, e usar helpers mortos como sinal de onde a duplicação deveria ter sido resolvida. Sem isso a skill tentaria reconstruir o projeto 3 do zero.

### 2.2 Catálogo de anti-patterns

São 23 entradas, distribuídas assim:

| Severidade | IDs | Por que entraram |
|------------|-----|------------------|
| CRITICAL | AP-01 credenciais hardcoded, AP-02 SQL injection, AP-03 God file/class, AP-04 exposição de dado sensível, AP-05 senha em texto puro ou hash fraco, AP-06 endpoint perigoso sem proteção | Todos apareceram em pelo menos um dos três projetos e são os que o enunciado cita como exemplo de CRITICAL. AP-04 e AP-06 entraram porque o `/health` com `secret_key` e o `/admin/query` não cabiam bem em "credencial hardcoded". |
| HIGH | AP-07 lógica no handler, AP-08 estado global mutável, AP-09 acoplamento sem DI, AP-10 callback pyramid, AP-11 defaults inseguros (debug, CORS, 0.0.0.0), AP-12 falta de transação/integridade | AP-10 existe por causa do projeto Node; os outros são as violações de MVC/SOLID que os três têm. AP-12 entrou porque o `DELETE /api/users` órfão e o `criar_pedido` sem transação são problemas de arquitetura de dados, não só de código. |
| MEDIUM | AP-13 N+1, AP-14 duplicação, AP-15 validação ausente, AP-16 exceção genérica, AP-17 side effects no handler, AP-18 APIs deprecated | AP-18 é obrigatório pelo enunciado; a tabela cobre Python, SQLAlchemy, Flask, Werkzeug, Node, Express 4/5, Java, Spring, Go e Rails, com o equivalente moderno de cada um. |
| LOW | AP-19 magic numbers, AP-20 nomes ruins, AP-21 código morto, AP-22 log com print, AP-23 construções verbosas | Tudo que aparece em volume nos três projetos mas não muda o funcionamento. |

Cada entrada tem: sinais de detecção escritos de forma "grepável" ou estrutural, uma linha de "idioms" traduzindo o sinal para Python/Node/Java, por que importa, e o `RP-xx` que resolve. No final do catálogo há um cheat sheet com os `grep` que cobrem a maior parte dos sinais textuais, para a Fase 2 começar por aí antes da leitura completa.

### 2.3 Como ficou agnóstica de tecnologia

- As heurísticas da Fase 1 são uma tabela manifesto → linguagem → onde o framework aparece (`requirements.txt`, `package.json`, `pom.xml`, `go.mod`, `Gemfile`, `composer.json`, `*.csproj`, `mix.exs`), mais os sinais de entry point, rotas e banco por ecossistema. O agente confirma o framework pelo import, não só pelo manifesto.
- O catálogo descreve sinais, não sintaxe. "Query construída com concatenação e entrada do usuário nas partes" vale para `cursor.execute("..." + id)` e para `` db.all(`... ${email}`) ``.
- As guidelines têm uma árvore alvo para Flask e outra para Express, e uma seção "outras stacks" mapeando as mesmas camadas para Spring, Go, Rails e Laravel com os nomes idiomáticos.
- O playbook alterna exemplos em Python e JavaScript propositalmente, e os passos de cada padrão são escritos sem depender da linguagem.
- A validação da Fase 3 é descrita em termos de "subir numa porta livre e chamar as rotas com curl", o que funciona para qualquer servidor HTTP.

A prova de que funcionou é a seção 3: a mesma skill, copiada sem alteração, rodou nos três projetos.

### 2.4 Desafios e como resolvi

- **Linha exata nos findings.** É fácil um agente escrever "aproximadamente linha 30" quando trabalha a partir de um `grep`. Coloquei uma regra explícita no template ("abra o arquivo e copie o número") e no `SKILL.md` ("nunca estime linhas"), além de exigir que cada arquivo seja lido por inteiro antes de julgar. Conferi por amostragem as linhas dos três relatórios contra o código original e bateram.
- **Refatorar sem quebrar o contrato.** Foi o maior risco. A solução foi tratar a lista de rotas da Fase 1 como contrato, gravar o baseline antes de mexer e ter a tabela fechada de decisões de contrato. Campos feios de request como `usr`/`eml` continuam aceitos; a tradução para nomes decentes acontece na camada de rota.
- **Projeto já parcialmente organizado.** Sem uma regra específica, a tendência natural é tratar o `task-manager-api` como monolito e reorganizar tudo, apagando nomes de pasta que já estavam certos. A seção de adaptação nas guidelines resolve isso: manter o que existe, adicionar o que falta.
- **Portas em conflito.** Como rodei os três projetos em paralelo, dois Flask na 5000 colidiam. A Fase 3 passou a exigir porta livre explícita (importar o `app` e chamar `run(port=...)`, ou variável `PORT` depois que a config é extraída).
- **Endpoints perigosos.** Apagar `/admin/query` quebraria "todos os endpoints continuam respondendo"; manter como estava mantém o CRITICAL. A regra ficou: manter a rota registrada, exigir `ADMIN_TOKEN` configurado por ambiente (503 se não configurado, 403 se errado) e restringir a leitura.
- **Segunda iteração no projeto 3.** O primeiro relatório do `task-manager-api` tinha três coisas que eu não aceitaria de um revisor humano: classificava os módulos de rota como God file CRITICAL (sendo que `models/` e `routes/` já existiam separados), tinha um finding de nomenclatura com "em todo o arquivo" no lugar de linha, e a estrutura proposta carregava `services/notification_service.py` que a própria Fase 3 ia apagar como código morto. Em vez de corrigir o relatório na mão, coloquei as três regras nas referências (regra de severidade do AP-03 no catálogo, `File:` só aceita `caminho:linha` no template, módulos mortos vão para uma lista "Removed" abaixo da árvore) e rodei as fases 1 e 2 de novo numa cópia limpa do projeto original. O relatório em `reports/audit-project-3.md` é o dessa segunda rodada, sem edição manual.
- **APIs deprecated sem nada deprecated.** No projeto 1 não há nada deprecated para Flask 3 + sqlite3. O template exige a seção mesmo vazia, com a frase "Nenhuma API deprecated encontrada para esta stack", para a skill não inventar achado para preencher a seção.

---

## 3. Resultados

Rodei a skill nos três projetos com o mesmo `SKILL.md` e as mesmas referências (as três cópias são idênticas, conferido com `diff -r`). A saída da Fase 2 de cada execução está em `reports/`, e o log completo (Fase 1, pergunta de confirmação, Fase 3, boot e todas as chamadas `curl` antes e depois) em `logs/`.

### 3.1 Resumo dos relatórios de auditoria

| Projeto | Stack detectada (Fase 1) | Arquivos | Rotas | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---------|--------------------------|----------|-------|----------|------|--------|-----|-------|
| 1. code-smells-project | Python 3.12 + Flask 3.1.1 | 4 | 19 | 6 | 5 | 5 | 4 | **20** |
| 2. ecommerce-api-legacy | Node 20 + Express 4.18.2 (4.22.1 resolvido) | 3 | 3 | 5 | 5 | 5 | 4 | **19** |
| 3. task-manager-api | Python 3.12 + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 | 15 | 22 | 4 | 8 | 7 | 5 | **24** |

Cruzando com a análise manual da seção 1: no projeto 1 a skill encontrou todos os 14 problemas que eu tinha listado (e mais seis que eu tinha agrupado ou deixado passar, como a falta de foreign keys e o acoplamento sem injeção de dependência). No projeto 2 os 16 problemas da minha lista estão cobertos pelos 19 findings (o catálogo separa, por exemplo, callback hell de acoplamento sem injeção, que eu tinha juntado). No projeto 3 os 16 estão cobertos pelos 24 (a skill abre um finding por arquivo quando o mesmo anti-pattern se repete, então o cálculo de atraso duplicado e a lógica nas rotas aparecem desdobrados). Em todos os casos o mínimo de 5 findings com pelo menos um CRITICAL foi superado com folga.

Sobre APIs deprecated: no projeto 3 a skill apontou `Query.get()` (LegacyAPIWarning do SQLAlchemy 2.x), `backref=` e `datetime.utcnow()` (DeprecationWarning do Python 3.12), com os equivalentes modernos; o boot da versão original no log mostra os warnings e o da versão refatorada não mostra nenhum. No projeto 2 classificou o uso exclusivo da API de callbacks do `sqlite3` como estilo legado e descartou explicitamente as deprecations do Express 4 e os métodos Annex B de string, porque não aparecem no código. No projeto 1 escreveu "Nenhuma API deprecated encontrada para esta stack", que era o esperado.

### 3.2 Antes e depois

**Projeto 1, code-smells-project**

```
antes                         depois
app.py                        app.py                       (create_app, composition root)
controllers.py                config/settings.py
models.py                     models/{base,produto_model,usuario_model,pedido_model,sistema_model}.py
database.py                   controllers/{produto,usuario,pedido,sistema}_controller.py
                              routes/{produto,usuario,pedido,sistema}_routes.py
                              validators/{produto,usuario,pedido}_validator.py
                              services/notificacao_service.py
                              middlewares/{error_handler,auth}.py
                              .env.example
```

Todas as queries passaram a ser parametrizadas, a conexão SQLite vive no `flask.g` por requisição com `PRAGMA foreign_keys=ON`, as senhas de seed nascem com hash do `werkzeug.security`, o `relatorio_vendas` virou uma query com `GROUP BY` e a listagem de pedidos um único `JOIN`. O envelope de erro `{"erro": ..., "sucesso": false}` é produzido por um único error handler.

**Projeto 2, ecommerce-api-legacy**

```
antes                         depois
src/app.js                    src/server.js                (entry point)
src/AppManager.js             src/app.js                   (createApp({ db, config }))
src/utils.js                  src/config/index.js
                              src/models/{database,userModel,courseModel,enrollmentModel,paymentModel,auditLogModel}.js
                              src/controllers/{checkoutController,financialReportController,userController}.js
                              src/routes/{index,checkoutRoutes,adminRoutes,userRoutes}.js
                              src/middlewares/{errorHandler,asyncHandler,auth}.js
                              src/services/{paymentGateway,passwordHasher}.js
                              src/validators/checkoutValidator.js
                              src/{errors,logger}.js
                              .env.example
```

O driver `sqlite3` foi embrulhado uma vez em promises, todos os handlers viraram `async` com um único ponto de resposta e um error middleware, o checkout grava matrícula e pagamento numa transação, o schema ganhou `NOT NULL`/`UNIQUE`/`REFERENCES ... ON DELETE CASCADE`, o relatório financeiro deixou de ser N+1 e as senhas usam `scrypt` com salt do `node:crypto` (sem dependência nova). O `package.json` aponta `main` e `start` para `src/server.js`.

**Projeto 3, task-manager-api**

```
antes                         depois
app.py                        app.py                       (create_app)
database.py                   database.py
seed.py                       seed.py
models/{task,user,category}   models/{base,task,user,category}.py
routes/{task,user,report}     routes/{task,user,category,report}_routes.py   (finas)
services/notification_service controllers/{task,user,category,report}_controller.py + schema_utils.py
utils/helpers.py              schemas/{task,user,category}_schema.py         (marshmallow)
                              config/settings.py
                              middlewares/{error_handler,auth}.py
                              .env.example
```

Aqui a skill manteve `models/` e `routes/` com os mesmos nomes, adicionou `controllers/`, `schemas/`, `config/` e `middlewares/`, tirou o CRUD de categorias de `report_routes.py`, concentrou `is_overdue` e `to_dict` no model (as seis cópias do cálculo de atraso sumiram), trocou `Query.get` por `db.session.get`, `backref` por `back_populates` e `utcnow()` por um `utc_now()` central, e removeu `utils/helpers.py` e `services/notification_service.py` (código morto; o que servia virou schema ou constante no model). O `python seed.py` continua sendo o passo antes do `python app.py`.

### 3.3 Checklist de validação

| Item | P1 | P2 | P3 |
|------|----|----|----|
| **Fase 1** | | | |
| Linguagem detectada corretamente | ✅ | ✅ | ✅ |
| Framework detectado corretamente (com versão) | ✅ | ✅ | ✅ |
| Domínio descrito corretamente | ✅ e-commerce (produtos, usuários, pedidos, itens) | ✅ LMS com checkout, matrículas, pagamentos | ✅ task manager (tasks, usuários, categorias, relatórios) |
| Número de arquivos condiz com a realidade | ✅ 4 | ✅ 3 | ✅ 15 (contando `__init__.py`) |
| **Fase 2** | | | |
| Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Findings ordenados CRITICAL → LOW | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 20 | ✅ 19 | ✅ 24 |
| Detecção de APIs deprecated incluída | ✅ seção presente, "nenhuma" | ✅ driver callback-only | ✅ 3 APIs |
| Pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** | | | |
| Estrutura de diretórios segue MVC | ✅ | ✅ | ✅ |
| Configuração extraída (sem hardcoded) | ✅ `config/settings.py` | ✅ `src/config/index.js` | ✅ `config/settings.py` |
| Models criados para abstrair dados | ✅ | ✅ | ✅ (já existiam, ganharam regras e serialização) |
| Views/Routes separadas | ✅ `routes/` | ✅ `src/routes/` | ✅ `routes/` |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ `app.py` | ✅ `src/server.js` | ✅ `app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ (e sem warnings de deprecation) |
| Endpoints originais respondem | ✅ 19/19 | ✅ 3/3 (5 chamadas) | ✅ 22/22 |

### 3.4 Logs das aplicações rodando após a refatoração

Trechos dos logs (completos em `logs/`):

Projeto 1, `python app.py` na porta 5000:

```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
GET /health -> 200 {"counts":{"pedidos":0,"produtos":10,"usuarios":3},"database":"connected","status":"ok","versao":"1.0.0"}
POST /login {"email":"admin@loja.com","senha":"admin123"} -> 200 {"dados":{"email":"admin@loja.com","id":1,"nome":"Admin","tipo":"admin"},"mensagem":"Login OK","sucesso":true}
POST /login {"email":"admin@loja.com' OR '1'='1","senha":"x"} -> 401 {"erro":"Email ou senha inválidos","sucesso":false}
POST /pedidos {"usuario_id":2,"itens":[{"produto_id":2,"quantidade":2},{"produto_id":3,"quantidade":1}]} -> 201 {"dados":{"pedido_id":1,"total":479.7},"mensagem":"Pedido criado com sucesso","sucesso":true}
POST /pedidos (999 notebooks) -> 400 {"erro":"Estoque insuficiente para Notebook Gamer","sucesso":false}
GET /relatorios/vendas -> 200 {"dados":{"faturamento_bruto":479.7,"pedidos_aprovados":1,"ticket_medio":479.7,"total_pedidos":1,...},"sucesso":true}
POST /admin/query sem token -> 401 {"erro":"Token administrativo inválido","sucesso":false}
POST /admin/query {"sql":"DELETE FROM produtos"} com token -> 400 {"erro":"Somente consultas SELECT são permitidas neste endpoint","sucesso":false}
```

Projeto 2, `npm start` na porta 3000:

```
{"level":"info","message":"Frankenstein LMS rodando na porta 3000...","ts":"2026-10-03T16:33:35.476Z"}
POST /api/checkout (Guilherme, cartão 4111...) -> 200 {"msg":"Sucesso","enrollment_id":2}
POST /api/checkout (João, cartão 5111...)      -> 400 Pagamento recusado
GET  /api/admin/financial-report sem token     -> 401 Token administrativo inválido
GET  /api/admin/financial-report com token     -> 200 [{"course":"Clean Architecture","revenue":997,"students":[{"student":"Leonan","paid":997}]},{"course":"Docker","revenue":497,"students":[{"student":"Guilherme","paid":497}]}]
DELETE /api/users/1 com token                  -> 200 Usuário deletado com sucesso.
GET  /api/admin/financial-report depois        -> 200 [{"course":"Clean Architecture","revenue":0,"students":[]}, ...]   (matrícula e pagamento removidos em cascata)
```

Projeto 3, `python seed.py && python app.py` na porta 5000:

```
Seed concluído com sucesso!  3 usuários  4 categorias  10 tasks
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
GET /tasks -> 200 [{"category_id":1,"category_name":"Backend",...,"overdue":true,...}]
GET /tasks/stats -> 200 {"cancelled":1,"completion_rate":18.18,"done":2,"in_progress":2,"overdue":2,"pending":6,"total":11}
POST /users {"name":"Ana","email":"ana@x.com","password":"abcd"} -> 201 {"active":true,"email":"ana@x.com","id":4,"name":"Ana","role":"user",...}   (sem o campo password)
POST /login {"email":"joao@email.com","password":"1234"} -> 200 {"message":"Login realizado com sucesso","token":"fake-jwt-token-1","user":{...}}
DELETE /users/4 sem token -> 401 {"error":"Token administrativo inválido"}
DELETE /users/4 com token -> 200 {"message":"Usuário deletado com sucesso"}
GET /reports/summary -> 200 {"overdue":{"count":2,"tasks":[...]},"tasks_by_status":{...},"user_productivity":[...]}
```

### 3.5 Como a skill se comportou em cada stack

- **Flask com SQL cru (projeto 1)** foi o caso mais "livro-texto": a Fase 3 seguiu a árvore alvo quase literalmente. O ponto que exigiu mais cuidado foi preservar o formato das respostas: o agente percebeu sozinho que o `/login` original devolvia menos campos que o `GET /usuarios` e separou duas listas de campos públicos no model para bater com o baseline.
- **Express com callbacks (projeto 2)** foi onde o playbook de `async/await` (RP-07) e o wrapper de promises fizeram diferença. Sem o baseline capturado antes, eu não teria confiança de que o relatório financeiro continuava idêntico depois de trocar os contadores manuais por `Promise.all`. A skill também respeitou a restrição de não adicionar dependência e usou `node:crypto` para o hash.
- **Flask com SQLAlchemy já parcialmente organizado (projeto 3)** foi o teste de adaptação. A skill não reconstruiu o projeto: manteve `models/` e `routes/`, adicionou as camadas que faltavam e usou o `marshmallow` que já estava no `requirements.txt`. Um detalhe técnico que ela resolveu bem foi a troca de `utcnow()`: aplicar `datetime.now(timezone.utc)` literalmente quebraria as comparações com `due_date` (naive, vindo de `strptime`), então o `utc_now()` central devolve naive de propósito.
- **Onde eu intervi depois de revisar o resultado.** Na primeira rodada do projeto 3 a skill tinha colocado o token administrativo em todos os `DELETE`; achei exagerado para tasks e categorias (são operações normais do domínio) e deixei o guard só em `DELETE /users/<id>`, que apaga tasks em cascata. Esse critério está na seção de decisões de contrato do relatório da segunda rodada. Também padronizei nos três projetos um token administrativo padrão apenas quando o ambiente é `development`, para que tudo responda com `npm start`/`python app.py` sem `.env`, continuando obrigatório em qualquer outro ambiente. E removi uma configuração SMTP que ficou órfã no projeto 3 depois que o serviço de notificação morto foi apagado. Essas revisões estão refletidas nos READMEs dos projetos e no final dos logs.
- **Tempo.** Cada execução completa (três fases, com baseline e validação) levou entre 14 e 20 minutos. A maior parte do tempo vai na Fase 3; as fases 1 e 2 juntas ficam em torno de 3 a 4 minutos.

---

## 4. Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude --version`).
- Python 3.12+ para os projetos 1 e 3, Node 20+ para o projeto 2.
- `curl` (a Fase 3 usa para validar os endpoints).

### Rodar a skill

A skill está copiada dentro de cada projeto, então basta entrar na pasta e invocar:

```bash
cd code-smells-project
claude "/refactor-arch"
```

```bash
cd ../ecommerce-api-legacy
claude "/refactor-arch"
```

```bash
cd ../task-manager-api
claude "/refactor-arch"
```

A Fase 1 imprime o resumo da stack, a Fase 2 imprime o relatório (e salva em `reports/audit-report.md` dentro do projeto, ou no caminho que você pedir) e para na pergunta `Proceed with refactoring (Phase 3)? [y/n]`. Só depois do `y` a Fase 3 altera arquivos. Para reproduzir esta entrega eu pedi para salvar os relatórios em `reports/audit-project-{1,2,3}.md` na raiz do repositório.

Se quiser rodar em outro projeto, copie a pasta `.claude/skills/refactor-arch/` para dentro dele. Não há nada específico dos três projetos dentro da skill.

### Validar que a refatoração funcionou

Projeto 1 (Flask, SQLite em arquivo):

```bash
cd code-smells-project && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python app.py
```

```bash
curl -s localhost:5000/health && curl -s localhost:5000/produtos | head -c 300
```

Projeto 2 (Express, SQLite em memória):

```bash
cd ecommerce-api-legacy && npm install && npm start
```

```bash
curl -s -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' -d '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
```

Projeto 3 (Flask + SQLAlchemy):

```bash
cd task-manager-api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python seed.py && .venv/bin/python app.py
```

```bash
curl -s localhost:5000/tasks | head -c 300 && curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' -d '{"email":"joao@email.com","password":"1234"}'
```

Cada projeto tem um `.env.example` com as variáveis que a configuração lê; sem `.env` os defaults de desenvolvimento são usados. Os endpoints administrativos (`/admin/*` no projeto 1, relatório financeiro e exclusão de usuário no projeto 2, exclusão de usuário no projeto 3) exigem o header `X-Admin-Token`; em ambiente de desenvolvimento o valor padrão é `dev-admin-token-change-me`, em qualquer outro ambiente `ADMIN_TOKEN` precisa ser configurado ou a rota responde `503`.

Os logs completos de cada execução (boot da aplicação refatorada e todas as chamadas de validação, antes e depois) estão em `logs/project-{1,2,3}-run.log`.
