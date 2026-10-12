# task-manager-api

API de Task Manager em Python/Flask, usada como entrada do desafio `refactor-arch`.
O projeto foi refatorado para o padrão MVC: as regras de negócio vivem nos models e
services, os controllers concentram o fluxo de cada caso de uso, e as rotas apenas
declaram o contrato e delegam.

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# SECRET_KEY é obrigatória e não tem default — gere uma:
python -c "import secrets; print(secrets.token_urlsafe(48))"
# cole o valor em SECRET_KEY no .env

python seed.py      # aplica as migrations e popula o banco
python wsgi.py      # sobe a aplicação
```

A aplicação sobe em `http://127.0.0.1:5000` (loopback, não `0.0.0.0`). O `seed.py`
roda `flask db upgrade` e popula o SQLite (`tasks.db`) com usuários, categorias e
tasks de exemplo — **rode-o antes do primeiro boot**.

Em produção, um servidor WSGI importa a aplicação diretamente e `app.run` nunca é
chamado:

```bash
gunicorn wsgi:app
```

## Configuração

Toda configuração vem do ambiente, lida em `src/config/settings.py` e documentada em
`.env.example`. Não há nenhum valor de configuração literal no código da aplicação.

`SECRET_KEY` é obrigatória e **não tem default**: a aplicação se recusa a subir sem
ela, porque um default conhecido assinaria sessões de forma previsível. A aplicação
também se recusa a subir com `DEBUG=true` em um `HOST` que não seja loopback — o
debugger do Werkzeug executa código arbitrário enviado pelo navegador.

## Schema do banco

O schema é versionado com Alembic via Flask-Migrate:

```bash
export FLASK_APP=wsgi.py
flask db upgrade                      # aplica as migrations pendentes
flask db migrate -m "descrição"       # gera uma migration a partir dos models
```

## Autenticação

`POST /login` devolve um token assinado (com expiração). Envie-o nas demais chamadas:

```bash
TOKEN=$(curl -s -X POST localhost:5000/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"joao@email.com","password":"1234"}' | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')

curl -s localhost:5000/tasks -H "Authorization: Bearer $TOKEN"
```

Modelo de acesso (deny by default):

| Acesso | Endpoints |
|---|---|
| Público | `GET /`, `GET /health`, `POST /login`, `POST /users` (cadastro) |
| Autenticado | todas as rotas de `/tasks`, `GET /categories` |
| Próprio usuário ou privilegiado | `GET`/`PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>` |
| `admin` ou `manager` | `GET /users`, `GET /reports/summary`, escrita em `/categories` |
| `admin` | `DELETE /users/<id>`, alteração de `role` |

## Paginação

As coleções aceitam `?limit=&offset=`, com default e máximo definidos na
configuração. A resposta continua sendo um array JSON; o total da coleção vem no
header `X-Total-Count`. `GET /categories` não é paginado de propósito: é uma tabela
de classificação, limitada por natureza.

## Estrutura

```
src/
├── config/        configuração vinda do ambiente e logging
├── models/        entidades, invariantes e acesso a dados
├── routes/        superfície de entrada: path -> guard -> controller
├── controllers/   fluxo de cada caso de uso
├── services/      regras que cruzam entidades (relatórios)
├── schemas/       validação de entrada (marshmallow)
├── serializers/   formato das respostas
├── middlewares/   auth, rate limit, tratamento central de erros
├── utils/         funções puras, sem conhecimento de domínio
└── app.py         composition root (create_app)
```

A direção das dependências aponta para o domínio: `routes -> controllers ->
services -> models`. Um model é importável e testável sem subir o servidor.

## Erros

Todas as respostas de erro têm o formato `{"error": "<mensagem>"}`, com um
`"details"` opcional contendo os erros por campo em falhas de validação. O
tratamento é centralizado em `src/middlewares/error_handler.py`; nenhum handler tem
`try/except` próprio.
