# Refactor Arch

## Análise Manual
### Projeto code-smells-project

***Severidade Critical***
- key exposta sem nenhum tipo de mitigador em um arquivo versionado do projeto (deveria no mínimo ser um .env não commitado ou um keyvault ou similar). Pior ainda, ela é exposta no endpoint de healthcheck
- Rota "/admin/query" não está protegida de SQL Injection.
- SQL Injection possível em praticamente todo o models.py
- Senha em texto puro (sem hash ou algum mecânismo de segurança)

***Severidade MEDIUM***
- Não há arquivo de configuração. Mudar o modo debug por exemplo exige uma alteração no arquivo app.py, que tem outras responsabilidades
- Sistema não está preparado para rodar em produção (app.run(host="0.0.0.0", port=5000, debug=True))
- Controllers tem muita responsabilidade. Deviam cuidar só da parte de interface (qual código HTTP, autenticação, etc.). Regras de negócio deveriam estar em services.

***Severidade LOW***
- Um arquivo controllers para todas as entidades. Extremamente confuso.
- Em get_pedidos_usuario (arquivo models.py). Os nomes das variáveis cursor1, cursor2 e cursor3 são genéticos e não dizem o que foi buscado.

### Projeto ecommerce-api-legacy

***Severidade Critical***
- Senha do admin_master commitada em arquivo versionado. Deveria estar em um keyvault ou no mínimo em um env não commitado (ainda altamente arriscado)
- Senhas armazenadas sem grande segurança com bad_crypto. Ataque ao sistema é muito fácil.
- Múltiplas ações no banco de dados sem uma transação. Possibilidade de inconsistência na base de dados (exemplo /api/checkout')
- PaymentgatewayKey exposta como log no console.
- Número do cartão exposto como log!
- Deletes mantém entidades com referência a entidade deletada.
- Rotas de admin sem quaisquer autenticação, entregando dados sensíveis a qulaquer um.

***Severidade MEDIUM***
- Arquivo AppManager faz tudo. Não há qualquer organização no projeto (exemplo, controller, services, repositories, infra, etc).
- Não existe rate limiting, limite de tamanho de body, CORS, middleware de validação, etc.

***Severidade LOW***
- Rotas confusas e difíceis de entender com alta complexidade idiomática.
- Diversos select *. As boas práticas ditam que devemos apenas buscar colunas que de fato vamos usar (para ficarmos future proof com relação a estrutura que pode mudar e também para economizar recursos).
- Péssima nomenclatura. O contrato da API usa usr, eml, pwd, c_id, card (:29-33) mapeados para u, e, p, cid, cc — e e ocupa o nome convencional da variável de erro. Junta com o self = this 

### Projeto task-manager-api

***Severidade Critical***
- NotificationService com usuário e senha hardcoded, exposto em arquivo versionado e commitado no repositório.
-SECRET_KEY hardcoded em app.py:13 ('super-secret-key-123').

***Severidade MEDIUM***
- validate_email em helpers.py deixa passar emaiils inválido (só valida ter dois blocos de texto separados por @)
- Lógica de "task atrasada" reimplementada 6 vezes, com o método do model existindo e nunca sendo chamado.

***Severidade LOW***
- created_at em diversos arquivos do projeto usa um método deprecated (datetime.utcnow). 
- no arquivo task.py a lib json é importada e nunca usada
- No arquivo helpers.py há diversos exemplos de libs importadas e não usadas
## Construção da Skill
Fase 1: Escrita manual da skill baseada nas instruções do projeto.
Contendo assim o que cada etapa do fluxo deveria fazer e o que era esperado.
Foram usadas técnicas de prompts engeneering como few shot e chain of thought para organizer o trabalho.
Fase 2: Formulação de um plano para chegar a versão final da skill.
- Como adicionar os arquivos de referência e quais estratégias usar para que não fiquem grandes demais e sejam ignoradas pelos agented de IA? -> Nesse caso a estratégia foi dividir certos pontos que precisam de mais detalhamento em arquivos de referência + deep analysis (feito para anti patterns e refactoring playbook). O agente identifica o problema e então toma a ação carregando só o necessário. -> Nenhum arquivo de referência deveria ter mais de 200 linhas.
- Refatorar a skill para um linguagem mais clara, sem ambiguidade e já referenciando os reference files. Foi usado a IA para pontuar quais são as falhas da skill frente as instruções para que as mudanças pudessem ser feitas com clareza e intencionalidade.

## Resultados

### Projeto code-smells-project

25 achados, todos endereçados. Relatório completo em
[`reports/audit-project-1.md`](reports/audit-project-1.md).

**Por tipo**

| Família | Achados | Transformações aplicadas |
|---|---|---|
| `SEC` segurança | 6 | segredo para o ambiente, queries parametrizadas, hash de senha, serializador sem credencial, autenticação por token com papel, debug/CORS corrigidos |
| `LAY` camadas | 6 | 3 god files divididos em MVC + services, regras movidas para o dono, conexão por requisição, `app.py` só compõe |
| `DAT` dados | 4 | transação com rollback, chaves estrangeiras + exclusão lógica, N+1 virou um JOIN, paginação |
| `API` contrato | 4 | error handler central, validação na fronteira, cadeia de middleware, envelope único |
| `QUA` qualidade | 5 | validação com dono único, constantes nomeadas, código morto removido, `logging` no lugar de `print` |
| `DEP` deprecated | 0 | nenhuma API deprecada — verificado contra Python 3.14 / Flask 3.1.1 |

**Por severidade:** CRITICAL 7 · HIGH 7 · MEDIUM 7 · LOW 4

**Estrutura final**

```
code-smells-project/
├── app.py                  ponto de entrada (26 linhas; antes: 88 com config + rotas + SQL)
└── src/
    ├── app.py              composition root
    ├── config/             configuração do ambiente + logging
    ├── infra/              conexão por requisição + schema com FKs
    ├── models/             persistência por entidade (produto, usuario, pedido, manutenção)
    ├── services/           auth, pedido (checkout), relatório, notificação
    ├── controllers/        fluxo HTTP por caso de uso
    ├── views/              rotas, validação, serialização
    ├── middlewares/        erro central, autenticação, rate limit, log
    └── errors.py           hierarquia de erros
```

`controllers.py` (292 linhas), `models.py` (314) e `database.py` (86) foram
removidos. 29 módulos, maior arquivo com 208 linhas.

**Validação:** os 48 endpoints foram gravados antes da refatoração e repetidos
depois — 16 respostas idênticas e 32 com mudanças intencionais declaradas (senha
fora da resposta, 401/403 nas rotas protegidas, `/admin/query` removido, 404 onde
antes havia 200 falso). Mais 65 verificações de comportamento (bypass de login,
rollback, N+1, 413, 429) e um plano manual de 104 casos em
`code-smells-project/docs/manual-test-plan.md`.

**Pendências conhecidas:** sem suíte automatizada, sem migrations, rotação da
`SECRET_KEY` antiga pendente (está no histórico do git), rate limit só em processo
único e notificações ainda são um stub nomeado como tal.

### Projeto ecommerce-api-legacy

24 achados, 22 endereçados por completo e 2 parcialmente. Relatório completo em
[`reports/audit-project-2.md`](reports/audit-project-2.md).

**Por tipo**

| Família | Achados | Transformações aplicadas |
|---|---|---|
| `SEC` segurança | 4 | segredos para o ambiente (exigidos em produção, aleatórios por processo fora dela), PAN e chave do gateway fora do log, `scrypt` com salt por usuário no lugar do hash caseiro, login + guarda por papel |
| `LAY` camadas | 5 | `AppManager` dividido em config/infra/models/services/controllers/routes/middlewares, regra de pagamento atrás de uma porta, conexão criada no composition root e injetada, rotas declaradas na camada de entrada |
| `DAT` dados | 6 | transação única com rollback, chaves estrangeiras + remoção por anonimização, N+1 de `1 + C + 2E` virou 5 queries constantes, paginação com clamp no servidor, colunas explícitas no lugar de `SELECT *` |
| `API` contrato | 5 | error handler central, schemas na fronteira, cadeia de middleware com rate limit, envelope de erro único, `async`/`await` no lugar dos contadores manuais |
| `QUA` qualidade | 4 | cache global e acumulador mortos removidos, vocabulário de status com um dono, nomes de domínio (abreviações mantidas como aliases depreciados), logger estruturado |
| `DEP` deprecated | 0 | nenhuma API deprecada — verificado contra Node 24, Express 4.22.1 e sqlite3 5.1.7 |

**Por severidade:** CRITICAL 6 · HIGH 7 · MEDIUM 6 · LOW 5

**Estrutura final**

```
ecommerce-api-legacy/
├── .env.example
├── docs/manual-test-plan.md
└── src/
    ├── app.js             composition root (compõe e nada mais)
    ├── config/            ambiente + carregador mínimo de .env
    ├── domain/            constantes de domínio + hierarquia de erros
    ├── infra/             conexão com transação e FKs, schema/seeds, logger
    ├── models/            persistência por entidade + read model do relatório
    ├── services/          checkout (fronteira transacional), relatório, auth, porta de pagamento
    ├── controllers/       fluxo HTTP por caso de uso
    ├── routes/            caminho → controller + schemas de request
    └── middlewares/       erro central, autenticação, rate limit, validação, log, headers
```

`AppManager.js` (141 linhas, acumulando DDL, rotas, SQL de 5 tabelas, regra de
pagamento e serialização) e `utils.js` (25, com config, cache global e o hash
caseiro) foram removidos. 30 módulos, maior arquivo com 180 linhas.

Invariantes verificáveis por `grep`: nenhum módulo fora de `routes/` e `app.js`
importa Express, nenhum fora de `infra/` importa `sqlite3`, não há SQL acima de
`models/` e nenhum `req`/`res` em `models/` ou `services/`.

**Validação:** os 13 passos do contrato foram gravados antes da refatoração e
repetidos depois — 1 resposta idêntica, 12 mudanças intencionais declaradas em
`tools/declared/ecommerce-api-legacy.json` e **0 divergências não declaradas**.
Mais 17 verificações da superfície nova (402, 401, 403, validações, paginação),
7 verificações internas (rollback deixa 0 matrículas/0 pagamentos, o banco recusa
deleção que orfanaria pagamentos, 5 queries tanto com 2 quanto com 20 cursos, 7/7
hashes distintos), determinismo byte-a-byte em 3 execuções independentes — que a
versão anterior não tinha — e um plano manual de 89 casos em
[`ecommerce-api-legacy/docs/manual-test-plan.md`](ecommerce-api-legacy/docs/manual-test-plan.md).

O achado mais grave confirmado em execução: um único POST anônimo com `card` como
número JSON derrubava o processo (`TypeError` dentro de um callback do driver, fora
do alcance do Express). Depois da refatoração o mesmo request responde 400 e o
servidor continua no ar.

**Pendências conhecidas:** o gateway de pagamento segue sendo um stub — a regra
`card.startsWith("4")` não foi reescrita, só isolada atrás de uma porta que
produção se recusa a usar; a trilha de auditoria é somente-escrita; rate limit só
em processo único; sem migrations; sem suíte automatizada; e a rotação da chave
`pk_live_` commitada continua pendente, porque ela está no histórico do git.

### Projeto task-manager-api

25 achados, 24 endereçados e 1 parcial. Relatório completo em
[`reports/audit-project-3.md`](reports/audit-project-3.md).

**Por tipo**

| Família | Achados | Transformações aplicadas |
|---|---|---|
| `SEC` segurança | 5 | `SECRET_KEY` e credenciais do notificador para o ambiente, hash de senha fora de toda resposta, PBKDF2 com salt (`werkzeug.security`), token assinado com papéis, console de debug do Werkzeug fora do alcance do cliente |
| `LAY` camadas | 5 | 3 módulos de rotas divididos em routes/controllers/services/models/serializers, regras movidas para o dono, `services/` e `utils/` que existiam sem nenhum call site adotados ou removidos, config e middlewares criados |
| `DAT` dados | 4 | integridade no delete, N+1 eliminado, paginação com clamp e `X-Total-Count`, mais um achado fora do catálogo (`DAT-X`) |
| `API` contrato | 4 | error handler central, validação com `marshmallow` — declarada no `requirements.txt` e nunca importada —, cadeia de middleware com rate limit, forma canônica única da task |
| `QUA` qualidade | 5 | regra de "task atrasada" reunida no método do model que existia e nunca era chamado (estava reimplementada 6 vezes), código morto removido, constantes nomeadas, `logging` no lugar de `print` |
| `DEP` deprecated | 2 | `datetime.utcnow()` em 18 sites concentrado em `utils/clock.py`, e a API legada do SQLAlchemy 1.x (`Query.get()` em 16 sites, `Model.query` em 57) migrada para `db.session` |

**Por severidade:** CRITICAL 6 · HIGH 3 · MEDIUM 11 · LOW 5

> `DAT-03` foi **rebaixado de HIGH para MEDIUM durante a Fase 3**, depois de uma
> sonda ao vivo contradizer o impacto que a auditoria havia afirmado. A afirmação
> original e a correção estão as duas registradas no achado. Na direção oposta,
> `DAT-01` e `DAT-02` foram investigados e **não** viraram achados: a sessão do
> Flask-SQLAlchemy já é uma transação única com `session.remove()` por requisição,
> e reportar fronteira transacional ausente ali seria o falso positivo mais comum
> da família.

**Estrutura final**

```
task-manager-api/
├── wsgi.py                 ponto de entrada (WSGI importa a app; app.run nunca é chamado)
├── seed.py                 aplica as migrations e popula o banco
├── migrations/             Alembic via Flask-Migrate (o único dos 3 projetos com migrations)
└── src/
    ├── app.py              composition root
    ├── config/             configuração do ambiente + logging
    ├── models/             entidades e invariantes (task, user, category)
    ├── services/           relatório
    ├── controllers/        fluxo HTTP por caso de uso + paginação
    ├── routes/             blueprints: caminho → controller
    ├── schemas/            validação de entrada com marshmallow
    ├── serializers/        forma de saída
    ├── middlewares/        erro central, autenticação, rate limit
    └── utils/              clock (fonte única de tempo) e números
```

`app.py` (raiz), `database.py`, os 3 modelos, os 3 módulos de rotas e o
`notification_service` original foram removidos. 46 módulos, maior arquivo com
295 linhas.

**Validação:** 77 chamadas gravadas antes da refatoração e repetidas depois — 39
idênticas, 38 com mudanças intencionais declaradas (hash de senha fora da
resposta, `details` por campo nas falhas de validação, forma canônica da task,
entrada mal tipada virando 400 em JSON no lugar de uma página HTML de 20 KB do
debugger) e **0 divergências não explicadas**. Mais 24/24 verificações de correção
(`.refactor-arch/verify_fixes.py`), que é o que um replay não mostra: um endpoint
que continua funcionando não é prova de que agora está protegido.

**Pendências conhecidas:** `QUA-04` ficou parcial — `cat_id` segue sendo o nome do
parâmetro em `/categories/<cat_id>`, porque renomeá-lo quebraria um contrato
público por um ganho de legibilidade LOW. E uma recomendação foi deliberadamente
**não** seguida: `MIN_PASSWORD_LENGTH` permanece 4, porque aumentá-lo rejeitaria
credenciais que a API hoje aceita — decisão de operação, não de refatoração.
Sem suíte automatizada.

### Logs das aplicações rodando após a refatoração

`ecommerce-api-legacy` — três linhas no boot e nada mais até chegar uma
requisição. Todo `console.log` foi substituído por log estruturado com nível e
timestamp, e nenhuma linha carrega PAN ou chave de gateway (o cartão aparece
mascarado como `****4444`):

```json
{"ts":"2026-10-11T22:58:14.971Z","level":"warn","msg":"using the stub payment gateway","env":"development"}
{"ts":"2026-10-11T22:58:15.021Z","level":"info","msg":"seeded development fixtures","users":2,"courses":2,"enrollments":1}
{"ts":"2026-10-11T22:58:15.027Z","level":"info","msg":"listening","host":"127.0.0.1","port":3100,"env":"development","database":":memory:","paymentDriver":"stub"}
{"ts":"…","level":"info","msg":"checkout completed","enrollmentId":2,"courseId":2,"userId":3,"userCreated":true}
{"ts":"…","level":"info","msg":"request","method":"POST","path":"/api/checkout","status":201,"durationMs":78,"userId":null}
```

`task-manager-api` — `Debug mode: off` e loopback, que eram dois dos achados
(`.refactor-arch/server-final.log`):

```
2026-10-11 18:23:29,985 INFO  src.app | application composed (debug=False, database=sqlite:///…/tasks.db)
 * Debug mode: off
 * Running on http://127.0.0.1:5000
2026-10-11 18:23:30,017 INFO  werkzeug | 127.0.0.1 - - "GET /health HTTP/1.1" 200 -
2026-10-11 18:23:36,255 INFO  src.controllers.auth_controller | login accepted user=1
```

### Observações entre stacks

A skill rodou nas três sem nenhuma adaptação, e o que mudou foi a *distância até o
alvo*, não o alvo:

- **O ponto de partida define o trabalho.** `ecommerce-api-legacy` era um monolito
  de 3 arquivos sem nenhuma camada: tudo foi criado do zero. `task-manager-api`
  estava parcialmente em camadas — com `services/` e `utils/` presentes e nunca
  chamados — e ali o trabalho foi adotar ou remover as abstrações abandonadas, não
  escrever novas. `code-smells-project` ficava no meio.
- **O default do driver decide achados de transação.** O mesmo código "sem
  transação" é bug no `sqlite3` do Node (autocommit por statement) e não é achado
  no Flask-SQLAlchemy (sessão única com rollback por requisição). Sem checar o
  driver, a família `DAT` produz o falso positivo mais caro do catálogo — foi o que
  separou o `DAT-01` de `ecommerce-api-legacy` (CRITICAL, confirmado com rollback
  ao vivo) do `DAT-01` descartado em `task-manager-api`.
- **`DEP` só existe contra uma versão fixada.** Zero achados no projeto Node
  (`Buffer.from` e `express.json()` são as formas correntes) e dois no projeto com
  ORM, um deles dependendo de qual interpretador roda, já que o projeto não fixa
  versão de Python. Reportar "nenhum, verificado contra X" é resultado; silêncio não é.
- **Validar exige evidência diferente por stack.** O contrato HTTP se grava igual
  nos três, mas o que um replay não alcança muda: no Node foi a exceção dentro de
  callback do driver que mata o processo; no Flask foi o console interativo do
  Werkzeug sendo servido ao cliente. Os dois só apareceram porque a captura da
  baseline é feita contra a aplicação rodando, antes de qualquer alteração.
- **A linguagem do código permanece.** Os três relatórios usam o vocabulário do
  próprio projeto (`pedidos`, `enrollments`, `tasks`), o que mantém cada achado
  localizável no fonte.

## Como Executar

### A skill

Dentro do diretório do projeto a auditar, invoque `/refactor-arch`. São três fases
sequenciais, cada uma esperando confirmação antes de seguir:

1. **Análise** — imprime linguagem, framework, dependências, domínio, arquitetura,
   número de arquivos e tabelas. Para aqui se o projeto não for server-side.
2. **Auditoria** — escreve `reports/audit-project-<N>.md` com os achados
   classificados por severidade. Nenhum arquivo do projeto é alterado nesta fase.
3. **Refatoração** — reestrutura para MVC e valida o resultado contra o contrato
   dos endpoints gravado antes das mudanças.

### A aplicação refatorada (code-smells-project)

```bash
cd code-smells-project
python3 -m venv .venv            # .venv/ está no .gitignore
.venv/bin/pip install -r requirements.txt

# SECRET_KEY é obrigatória — a aplicação se recusa a subir sem ela
export SECRET_KEY=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))")
.venv/bin/python app.py
```

Sobe em `http://127.0.0.1:5001`. A porta padrão é 5001. Use `PORT=` para escolher outra.

As rotas de escrita e as administrativas exigem token:

```bash
BASE=http://127.0.0.1:5001

TOKEN=$(curl -sS -X POST $BASE/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

curl $BASE/produtos                                  # público
curl $BASE/usuarios -H "Authorization: Bearer $TOKEN" # admin
```

Detalhes de endpoints, variáveis de ambiente e banco em
[`code-smells-project/README.md`](code-smells-project/README.md).

Resultado dos testes em code-smells-project/docs/manual-test-plan.md
Alguns prints:
code-smells-project/prints-tests

Há também uma pasta para teste das rotas no app Bruno (similar a insomnia e postman) /Users/pedroazeredo/Documents/Repos/MBA/desafios/mba-ia-refactor-projects-skill/code-smells-project/bruno
A maior parte dos prints na pasta de evidências foi feita nesse app

### A aplicação refatorada (ecommerce-api-legacy)

```bash
cd ecommerce-api-legacy
npm install

npm start
```

Sobe em `http://127.0.0.1:3000`. Nenhuma variável de ambiente é obrigatória em
desenvolvimento — fora de produção os segredos são gerados aleatoriamente por
processo, em vez de caírem em um default conhecido. Se a porta 3000 estiver
ocupada (um `docker run -p 3000:…` basta), use `PORT=3100 npm start`.

O banco é SQLite **em memória**: o schema e os seeds são recriados a cada boot e
nada sobrevive a um restart. Como o segredo do token também é novo a cada
processo, reiniciar invalida os tokens já emitidos.

As rotas administrativas exigem token com papel `admin`:

```bash
TOKEN=$(curl -s -X POST localhost:3000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@fullcycle.com.br","password":"dev-admin-password"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

# público: cria usuário, matrícula e pagamento em uma transação
curl -s -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' \
  -d '{"name":"Guilherme","email":"gui@fullcycle.com.br","password":"senhaforte","courseId":2,"cardNumber":"4111222233334444"}'

# admin
curl -s localhost:3000/api/admin/financial-report -H "Authorization: Bearer $TOKEN"
```

Em produção a aplicação **se recusa a subir** sem `AUTH_TOKEN_SECRET` e com o
gateway de pagamento em modo stub. Detalhes de endpoints, contrato de erro e
limitações em
[`ecommerce-api-legacy/README.md`](ecommerce-api-legacy/README.md).

### A aplicação refatorada (task-manager-api)

```bash
cd task-manager-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# SECRET_KEY é obrigatória e não tem default — gere uma e cole no .env:
python -c "import secrets; print(secrets.token_urlsafe(48))"

python seed.py      # aplica as migrations (Alembic) e popula o banco
python wsgi.py
```

Sobe em `http://127.0.0.1:5000`. Rode o `seed.py` antes do primeiro boot: é ele
que aplica as migrations. Em produção, um servidor WSGI importa a aplicação e
`app.run` nunca é chamado (`gunicorn wsgi:app`).

```bash
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"joao@email.com","password":"1234"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')

curl -s localhost:5000/tasks -H "Authorization: Bearer $TOKEN"
```

Detalhes de endpoints, modelo de acesso e migrations em
[`task-manager-api/README.md`](task-manager-api/README.md).

### Como validar que a refatoração funcionou

Nos três projetos a validação é a mesma ideia: gravar o contrato dos endpoints
**antes** de qualquer alteração e repeti-lo depois, de modo que "os endpoints
continuam respondendo" seja uma medição e não uma afirmação. Toda divergência é
ou uma regressão ou uma mudança declarada por escrito — nunca uma surpresa.

```bash
# ecommerce-api-legacy — ferramenta compartilhada em tools/
python3 tools/contract_check.py capture tools/specs/ecommerce-api-legacy.after.json \
  http://127.0.0.1:3000 /tmp/replay.json
python3 tools/contract_check.py compare tools/baselines/ecommerce-api-legacy.before.json \
  /tmp/replay.json tools/declared/ecommerce-api-legacy.json
# esperado: 12 declared change(s), 0 undeclared — e exit code 0

# task-manager-api — scripts próprios, gravados junto da baseline
python .refactor-arch/classify.py .refactor-arch/baseline.json \
  .refactor-arch/replay-final.json
# esperado: UNEXPLAINED: 0
python .refactor-arch/verify_fixes.py      # exige a aplicação no ar — 24/24
```

Um `compare` que acusa divergência **não declarada** é o único resultado que
reprova a refatoração. Para o que um replay não alcança — rollback de transação,
contagem de queries, guardas de acesso, rate limit — cada projeto tem um plano
manual roteirizado:
[`code-smells-project/docs/manual-test-plan.md`](code-smells-project/docs/manual-test-plan.md)
(104 casos) e
[`ecommerce-api-legacy/docs/manual-test-plan.md`](ecommerce-api-legacy/docs/manual-test-plan.md)
(89 casos), ambos com cada caso apontando o achado que verifica.
