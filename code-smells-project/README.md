# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`,
refatorada para MVC (Models · Views/Routes · Controllers) com services,
middlewares e configuração por ambiente.

## Como rodar

### Tudo de uma vez

```bash
cd code-smells-project
./smoke.sh
```

O script cria a venv se não existir, instala as dependências, confere se a porta
está livre, sobe o servidor, verifica 13 endpoints (incluindo 401 sem token,
injeção no login recusada e `senha` fora da resposta) e derruba o servidor no
fim. Sai com código 0 se tudo passou. Use `./smoke.sh 5005` para outra porta.

### Passo a passo

Os comandos usam `.venv/bin/python` explicitamente — assim funcionam sem depender
de você ter ativado a venv.

**1. Dependências** (uma vez só)

```bash
cd code-smells-project
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**2. Subir o servidor**

```bash
export SECRET_KEY=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))")
.venv/bin/python app.py
```

Está pronto quando aparecer `Running on http://127.0.0.1:5001`. O banco SQLite
(`loja.db`) é criado no primeiro boot, já com produtos e usuários de exemplo.

> A porta padrão é **5001**, não 5000: no macOS o AirPlay Receiver ocupa a 5000.
> Para usar outra, `PORT=8080 .venv/bin/python app.py`.

**3. Testar**

```bash
curl -sS http://127.0.0.1:5001/health

TOKEN=$(curl -sS -X POST http://127.0.0.1:5001/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

curl -sS http://127.0.0.1:5001/produtos
curl -sS http://127.0.0.1:5001/usuarios -H "Authorization: Bearer $TOKEN"
```

**4. Parar**

```bash
lsof -ti:5001 -sTCP:LISTEN | xargs kill     # ou Ctrl+C no terminal do servidor
```

Em produção, sirva por WSGI em vez de `app.run` (`app.py` expõe `app` em nível de
módulo):

```bash
pip install gunicorn   # não vem em requirements.txt
gunicorn "app:app"
```

### Variáveis de ambiente

A aplicação lê **apenas variáveis de ambiente** — não existe carregamento
automático de arquivo `.env`. `.env.example` documenta os nomes e os padrões; para
usá-lo como fonte, exporte o conteúdo antes de subir:

```bash
cp .env.example .env     # preencha SECRET_KEY
set -a; source .env; set +a
python app.py
```

`SECRET_KEY` é a única obrigatória; as demais têm padrões seguros para
desenvolvimento (`DEBUG=false`, `HOST=127.0.0.1`, CORS restrito a
`http://localhost:3000`). `DEBUG=true` junto de um `HOST` público é recusado no
boot: essa combinação expõe o console interativo do Werkzeug.

## Autenticação

`POST /login` devolve um token assinado, com validade, que deve ser enviado nas
rotas protegidas:

```bash
TOKEN=$(curl -sS -X POST http://127.0.0.1:5001/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

curl -sS http://127.0.0.1:5001/usuarios -H "Authorization: Bearer $TOKEN"
```

O token vale 1 hora (`TOKEN_TTL_SECONDS`). Se algo falhar aqui, veja
"Armadilhas conhecidas" acima.

As senhas do seed são de desenvolvimento e ficam gravadas com hash
(`werkzeug.security`), nunca em texto puro.

## Endpoints

| Método | Rota | Acesso |
|---|---|---|
| GET | `/` | público |
| GET | `/health` | público |
| GET | `/produtos` | público |
| GET | `/produtos/busca` | público |
| GET | `/produtos/<id>` | público |
| POST | `/usuarios` | público (cadastro) |
| POST | `/login` | público (com limite de requisições) |
| POST | `/pedidos` | autenticado (próprio usuário, ou admin) |
| GET | `/pedidos/usuario/<id>` | autenticado (próprio usuário, ou admin) |
| POST · PUT · DELETE | `/produtos`, `/produtos/<id>` | admin |
| GET | `/usuarios`, `/usuarios/<id>` | admin |
| GET | `/pedidos` | admin |
| PUT | `/pedidos/<id>/status` | admin |
| GET | `/relatorios/vendas` | admin |
| POST | `/admin/reset-db` | admin (com limite de requisições) |

Listagens aceitam `?limit=` e `?offset=` (padrão 50, máximo 200) e devolvem
`total`, `limit` e `offset` junto de `dados`.

Respostas de sucesso: `{"sucesso": true, "dados": ..., "mensagem": ...}`.
Respostas de erro: `{"sucesso": false, "erro": "...", "detalhes": ...}`,
produzidas pelo handler de erro central.

`POST /admin/query`, que executava SQL arbitrário enviado pelo cliente, **foi
removido** — não existe versão segura desse endpoint.

## Estrutura

```
src/
├── config/        configuração lida do ambiente e setup de logging
├── infra/         conexão com o banco (uma por requisição) e criação de schema
├── models/        persistência e invariantes por entidade
├── services/      regras entre entidades e integrações (auth, pedido, relatório, notificação)
├── controllers/   fluxo de aplicação de cada caso de uso
├── views/         rotas, validação de entrada e serialização
├── middlewares/   erro centralizado, autenticação, limite de requisições, log
├── errors.py      hierarquia de erros (status + mensagem segura ao cliente)
└── app.py         composition root (create_app)
app.py             ponto de entrada do processo
```

Direção das dependências: `views → controllers → services → models → infra`,
com `config`, `errors` e `middlewares` disponíveis a quem precisa. Três
invariantes verificáveis por `grep`: nenhum model importa `flask`, nenhum
controller contém SQL, e só o composition root (`src/app.py`) importa
`infra/database`.

## Testes

Não há suíte automatizada. A validação é manual e está roteirizada em
[`docs/manual-test-plan.md`](docs/manual-test-plan.md): 104 casos em 12 suítes,
cada um apontando o achado da auditoria que verifica
(`../reports/audit-project-1.md`).

O contrato dos endpoints antes da refatoração está em
`.refactor-arch/baseline.json`, e o resultado do replay depois dela em
`.refactor-arch/replay.json` — úteis para conferir que uma mudança futura não
altera resposta sem intenção.

## Banco de dados

O schema declara chaves estrangeiras (`ON DELETE CASCADE` em `itens_pedido`,
`RESTRICT` nas referências a `produtos` e `usuarios`) e a aplicação ativa
`PRAGMA foreign_keys = ON` em cada conexão.

Exclusão de produto é **lógica** (`ativo = 0`): o produto sai do catálogo e o
histórico de pedidos continua legível.

Não há migrations: o schema é criado por `CREATE TABLE IF NOT EXISTS` no boot.
Um `loja.db` criado pela versão anterior do projeto **não** é atualizado — apague
o arquivo para que ele seja recriado no formato atual.
