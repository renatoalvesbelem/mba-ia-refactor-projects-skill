================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.12 + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-10-03

## Summary
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4

## Findings

### #1 [CRITICAL] God file / God class (AP-03)
File: models.py:1-315 (especialmente 133-169, 235-273)
Description: models.py concentra acesso a dados via SQL cru e regras de negócio para quatro entidades (produtos, usuarios, pedidos, itens_pedido) no mesmo arquivo: criar_pedido (133-169) valida estoque, calcula total e grava pedido/itens/baixa de estoque; relatorio_vendas (235-273) calcula desconto e ticket médio. Nenhuma dessas responsabilidades está isolada em uma camada própria.
Impact: Nenhuma regra pode ser testada isoladamente do SQLite; qualquer mudança em uma entidade arrisca quebrar outra; o arquivo já passa de 300 linhas misturando camadas.
Recommendation: Dividir por entidade e por camada (um módulo de modelo por agregado, controllers separados). Ver RP-03.

### #2 [CRITICAL] Unprotected dangerous endpoint (AP-06)
File: app.py:47-57, 59-78
Description: POST /admin/reset-db (app.py:47-57) apaga todas as linhas de itens_pedido, pedidos, produtos e usuarios sem nenhuma verificação de autenticação. POST /admin/query (app.py:59-78) recebe uma string SQL arbitrária do corpo da requisição (dados.get("sql")) e executa diretamente com cursor.execute(query), sem autenticação nem validação.
Impact: Qualquer pessoa que alcance o host destrói a base inteira ou executa qualquer comando SQL (leitura, escrita ou exclusão) sem autorização alguma — é o pior risco do projeto.
Recommendation: Remover a execução de SQL arbitrário do contrato e proteger operações administrativas destrutivas com um guard de autenticação vindo da config. Ver RP-13.

### #3 [CRITICAL] SQL injection (string-built queries) (AP-02)
File: models.py:28, 48-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 291-297
Description: Praticamente toda consulta em models.py é montada concatenando strings com valores vindos diretamente da requisição (str(id), nome, descricao, categoria, email, senha, termo de busca etc.), incluindo a consulta de login (109-111: "... WHERE email = '" + email + "' AND senha = '" + senha + "'").
Impact: Permite bypass de login (ex.: email' OR '1'='1), exfiltração ou destruição de dados e quebra de tipos (um preço como string vai direto para o SQL).
Recommendation: Trocar toda concatenação por queries parametrizadas (?) do próprio sqlite3. Ver RP-02.

### #4 [CRITICAL] Plaintext or weak password storage (AP-05)
File: models.py:105-120, 122-131; database.py:75-79
Description: login_usuario (models.py:105-120) compara a senha recebida diretamente com o valor salvo no banco; criar_usuario (122-131) insere a senha exatamente como recebida, sem hash; os usuários de seed em database.py:75-79 já nascem com senhas em texto puro ("admin123", "123456", "senha123").
Impact: Um vazamento do arquivo loja.db expõe a senha real de todos os usuários; não há como revogar ou auditar.
Recommendation: Aplicar hash (werkzeug.security.generate_password_hash / check_password_hash, já disponível via Flask) na criação e no login. Ver RP-09.

### #5 [CRITICAL] Hardcoded credentials and secrets (AP-01)
File: app.py:7
Description: app.config["SECRET_KEY"] = "minha-chave-super-secreta-123" está escrita diretamente no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório tem a chave de sessão/assinatura da aplicação; trocar a chave exige um deploy manual do código.
Recommendation: Ler a chave de uma variável de ambiente com valor seguro apenas para desenvolvimento local. Ver RP-01.

### #6 [CRITICAL] Sensitive data exposure in responses or logs (AP-04)
File: models.py:72-87 (campo "senha" na linha 83), models.py:89-103 (campo "senha" na linha 99); controllers.py:264-292 (secret_key na linha 289, debug na linha 288)
Description: get_todos_usuarios e get_usuario_por_id devolvem o campo "senha" para qualquer chamador de GET /usuarios e GET /usuarios/<id>; health_check devolve secret_key, debug e db_path no corpo de uma resposta pública.
Impact: Vaza credenciais e informações internas da infraestrutura (chave de assinatura, caminho do banco, modo debug) para qualquer cliente da API.
Recommendation: Serializar usuário com uma whitelist de campos (sem senha) e remover dados sensíveis do /health. Ver RP-09.

### #7 [HIGH] Tight coupling / no dependency injection (AP-09)
File: controllers.py:1-3; app.py:4, 49, 66
Description: controllers.py importa diretamente database.get_db (linha 3) e models; app.py também importa get_db e o usa diretamente dentro das rotas /admin/reset-db (linha 49) e /admin/query (linha 66), pulando completamente a camada de controller/model.
Impact: Nenhuma dessas rotas pode ser testada sem um SQLite real; trocar o armazenamento ou isolar um teste exige editar cada consumidor.
Recommendation: Centralizar o acesso a dados nos models e compor a aplicação a partir de um composition root único. Ver RP-05.

### #8 [HIGH] Global mutable state (AP-08)
File: database.py:4, 8-10
Description: db_connection é uma variável global de módulo (linha 4), reatribuída dentro de get_db via global db_connection (linha 8) e conectada com check_same_thread=False (linha 10) para contornar o fato de ser uma conexão única compartilhada entre requisições.
Impact: Acoplamento oculto entre requisições concorrentes, condições de corrida em escrita e impossibilidade de isolar testes com uma conexão própria.
Recommendation: Escopar a conexão por requisição/injeção em vez de um singleton de módulo. Ver RP-05.

### #9 [HIGH] Business logic inside route handlers (fat controllers) (AP-07)
File: controllers.py:24-62, 64-96, 188-220
Description: criar_produto, atualizar_produto e criar_pedido validam entrada, aplicam regras (lista de categorias válidas, cálculo de total) e chamam o acesso a dados, tudo na mesma função de mais de 30 linhas.
Impact: As regras só existem atreladas ao HTTP, não podem ser reaproveitadas por um job ou CLI, e cada handler reimplementa validação de forma ligeiramente diferente.
Recommendation: Extrair validação e orquestração para um controller fino que delega a um model/serviço. Ver RP-04 e RP-16.

### #10 [HIGH] Missing transaction and data integrity (AP-12)
File: models.py:133-169; database.py:15-53
Description: criar_pedido (133-169) faz múltiplos INSERT/UPDATE (pedido, itens, baixa de estoque) com um único commit no final, sem BEGIN/transação explícita nem rollback em caso de falha parcial; o schema em database.py (15-53) não declara nenhuma foreign key nem UNIQUE (ex.: usuarios.email sem UNIQUE, itens_pedido.pedido_id sem FK para pedidos).
Impact: Uma falha no meio do fluxo deixa pedido criado sem itens ou estoque baixado sem pedido associado; e-mails duplicados e registros órfãos corrompem relatórios.
Recommendation: Envolver a sequência em uma transação e declarar as constraints que o domínio exige. Ver RP-14.

### #11 [HIGH] Insecure runtime defaults (AP-11)
File: app.py:8, 9, 88
Description: app.config["DEBUG"] = True (linha 8), CORS(app) sem restrição de origem (linha 9) e app.run(host="0.0.0.0", port=5000, debug=True) (linha 88) expõem o debugger do Werkzeug publicamente e liberam qualquer origem via CORS.
Impact: O debugger do Werkzeug com debug=True permite execução remota de código; CORS aberto facilita ataques de origem cruzada.
Recommendation: Ler debug, host, porta e origens permitidas da configuração, desligados por padrão fora do ambiente local. Ver RP-01.

### #12 [MEDIUM] N+1 queries (AP-13)
File: models.py:187-199, 219-231
Description: get_pedidos_usuario e get_todos_pedidos abrem um cursor2 para buscar itens_pedido por pedido e, dentro desse laço, abrem um cursor3 para buscar o nome do produto por item — uma consulta por pedido mais uma por item.
Impact: O tempo de resposta cresce linearmente com o número de pedidos e itens; o banco é acionado dezenas de vezes para montar uma única resposta.
Recommendation: Substituir por JOINs entre pedidos, itens_pedido e produtos. Ver RP-08.

### #13 [MEDIUM] Duplicated code (AP-14)
File: models.py:9-21 e 302-313; models.py:176-199 e 211-231; controllers.py:28-46 e 72-90
Description: get_todos_produtos e buscar_produtos repetem o mesmo bloco de serialização linha a linha; get_pedidos_usuario e get_todos_pedidos repetem a mesma montagem de itens por pedido; criar_produto e atualizar_produto repetem a mesma cadeia de validação de nome/preço/estoque.
Impact: Qualquer correção de regra ou de serialização precisa ser replicada em vários lugares, e as cópias já divergem (atualizar_produto não repete a checagem de tamanho do nome que criar_produto tem).
Recommendation: Extrair um serializador de produto/pedido e um validador reutilizável. Ver RP-15.

### #14 [MEDIUM] Missing or inconsistent input validation (AP-15)
File: controllers.py:43-46, 87-90, 118-121
Description: preco e estoque são comparados com < 0 sem checar o tipo (podem vir como string do JSON); atualizar_produto (87-90) não repete a validação de tamanho do nome presente em criar_produto (47-50); buscar_produtos converte preco_min/preco_max com float() (118-121) sem tratar exceção de conversão.
Impact: Entradas inválidas geram 500 em vez de 400, ou são persistidas sem checagem, e abrem mais superfície para os problemas de tipo que alimentam o AP-02.
Recommendation: Centralizar as regras de validação em um único validador usado por create e update. Ver RP-16.

### #15 [MEDIUM] Generic exception handling and error leakage (AP-16)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292; app.py:77-78
Description: Todas as funções de controllers.py e a rota /admin/query capturam except Exception as e e devolvem str(e) direto no corpo da resposta, repetindo o mesmo bloco try/except em cada handler.
Impact: Mensagens internas (nome de coluna, caminho de arquivo, mensagem do driver SQLite) vazam para o cliente; não existe diferenciação entre erro de validação e erro interno.
Recommendation: Centralizar em um error handler único que loga o detalhe e devolve uma mensagem genérica ao cliente. Ver RP-06.

### #16 [MEDIUM] Cross-cutting side effects inside handlers (AP-17)
File: controllers.py:208-210, 247-250
Description: criar_pedido dispara três print simulando envio de e-mail/SMS/push (208-210) dentro do próprio handler de criação; atualizar_status_pedido imprime notificações de aprovação/cancelamento (247-250) misturadas com a troca de status.
Impact: O handler acumula motivos de mudança que não têm relação com "criar pedido"; a notificação não pode ser desligada em teste nem reaproveitada por outro fluxo.
Recommendation: Mover para um serviço de notificação chamado pelo controller. Ver RP-04 e RP-12.

### #17 [LOW] Magic numbers and inline literal lists (AP-19)
File: controllers.py:47, 49, 52, 242; models.py:257-262
Description: Limites de tamanho de nome (47: < 2, 49: > 200), a lista categorias_validas (52) e a lista de status válidos (242) estão escritos inline nos handlers; os percentuais e limites de desconto (10000/0.1, 5000/0.05, 1000/0.02) estão hardcoded em relatorio_vendas (257-262).
Impact: Mudar uma regra de negócio exige caçar o valor espalhado pelo código; cópias da mesma lista podem divergir.
Recommendation: Mover para constantes nomeadas na camada de modelo. Ver RP-11.

### #18 [LOW] Poor naming (AP-20)
File: models.py:187, 191, 219, 223; controllers.py:14, 64, 98
Description: Cursores numerados cursor2/cursor3 (models.py:187,191,219,223) por falta de escopo próprio; parâmetros de rota nomeados id (controllers.py:14, 64, 98) sombreiam o builtin id do Python.
Impact: Dificulta leitura e aumenta a chance de reutilizar a variável errada.
Recommendation: Renomear para nomes de domínio (produto_id, pedido_id) ao extrair as camadas. Ver RP-15.

### #19 [LOW] Dead code and unused imports (AP-21)
File: models.py:2; database.py:2
Description: models.py importa sqlite3 (linha 2) mas nunca usa o módulo diretamente (todo acesso passa por database.get_db()); database.py importa os (linha 2) e nunca o referencia no arquivo.
Impact: Sinaliza dependência que não existe de fato e confunde quem lê o arquivo.
Recommendation: Remover os imports não utilizados.

### #20 [LOW] Print-based logging (AP-22)
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250; app.py:56, 83-86
Description: Toda mensagem operacional (listagem, criação, erro, login, notificações, banner de boot) usa print em vez de um logger configurado.
Impact: Sem níveis, sem timestamp, sem como silenciar em teste, e dados de usuário (e-mail, id) acabam concatenados direto no stdout.
Recommendation: Substituir por um logger de módulo padrão. Ver RP-12.

## Deprecated APIs
| API | File:line | Status | Modern equivalent |
|-----|-----------|--------|-------------------|
| — | — | — | — |

Nenhuma API deprecated encontrada para esta stack. Verificado: o projeto usa Python 3.12 + Flask 3.1.1 + sqlite3 cru, sem SQLAlchemy, sem datetime.utcnow()/adapters de data do sqlite3 (o schema usa CURRENT_TIMESTAMP como TEXT, nunca passa datetime do Python para o driver), sem asyncio, sem logging.warn(), sem flask.before_first_request/JSONEncoder/escape, sem werkzeug.urls legado. A importação do app com `python -W error::DeprecationWarning -c "import app"` não emitiu nenhum warning.

## Proposed target structure
```
code-smells-project/
├── app.py
├── config/
│   └── __init__.py
├── database/
│   └── __init__.py
├── models/
│   ├── __init__.py
│   ├── produto.py
│   ├── usuario.py
│   └── pedido.py
├── controllers/
│   ├── __init__.py
│   ├── produto_controller.py
│   ├── usuario_controller.py
│   ├── pedido_controller.py
│   └── sistema_controller.py
├── routes/
│   ├── __init__.py
│   ├── produto_routes.py
│   ├── usuario_routes.py
│   ├── pedido_routes.py
│   └── sistema_routes.py
├── middlewares/
│   └── error_handler.py
├── .env.example
└── README.md
```

## Contract decisions preview
- POST /admin/query será removido do contrato público: executa SQL arbitrário vindo da requisição (AP-06, CRITICAL) e não existe forma segura de preservar esse comportamento.
- POST /admin/reset-db será mantido como rota, mas passa a exigir um token de administração lido da configuração (ADMIN_TOKEN via variável de ambiente), já que o projeto não possui nenhum sistema de autenticação/sessão para um guard mais sofisticado.
- GET /usuarios e GET /usuarios/<id> deixam de devolver o campo "senha" (AP-04).
- GET /health deixa de devolver secret_key e debug (AP-04).
- Senhas passam a ser armazenadas com hash (werkzeug.security) na criação de usuário e verificadas por hash no login (AP-05); o contrato de entrada/saída dos endpoints não muda, exceto pela remoção do campo "senha" das respostas.

================================
Total: 20 findings
================================
