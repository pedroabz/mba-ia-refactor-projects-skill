# Plano de teste manual — code-smells-project

Roteiro para validar a aplicação refatorada à mão, sem suíte automatizada.
Cada caso aponta o achado da auditoria (`reports/audit-project-1.md`) que ele
verifica, para que uma falha diga imediatamente qual correção regrediu.

**Como usar:** execute as suítes na ordem. S5 a S10 dependem do estado criado por
suítes anteriores — a coluna *Pré-condição* diz quando. Registre o resultado na
tabela do fim.

---

## 0. Preparação

### Terminal 1 — servidor

```bash
cd code-smells-project
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

rm -f loja.db                      # banco limpo: os IDs do roteiro dependem disso
export SECRET_KEY=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))")
.venv/bin/python app.py
```

Esperado no boot: três linhas de log JSON (`schema verificado`,
`carga inicial aplicada`, `aplicacao montada`), `Debug mode: off`, servidor em
`http://127.0.0.1:5001`. **Nenhum traceback.**

### Terminal 2 — cliente

```bash
BASE=http://127.0.0.1:5001

# Resposta + status em uma linha. O -S mostra erro do curl em vez de corpo vazio.
req() { curl -sS -w '\n[%{http_code}]\n' "$@"; }

# Extrai o token do login
tok() { python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])'; }

ADMIN=$(curl -s -X POST $BASE/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' | tok)
CLIENTE=$(curl -s -X POST $BASE/login -H 'Content-Type: application/json' \
  -d '{"email":"joao@email.com","senha":"123456"}' | tok)

echo "admin: ${#ADMIN} chars | cliente: ${#CLIENTE} chars"   # ambos > 30
```

`AH="Authorization: Bearer $ADMIN"` e `CH="Authorization: Bearer $CLIENTE"` são
usados abaixo:

```bash
AH="Authorization: Bearer $ADMIN"
CH="Authorization: Bearer $CLIENTE"
JSON='Content-Type: application/json'
```

### Estado inicial (seed)

| Tabela | Conteúdo |
|---|---|
| produtos | 10 itens, IDs 1–10. Estoques: 1=10, 2=50, 3=30, 4=15, 5=25, 6=8, 7=20, 8=40, 9=35, 10=100 |
| usuarios | 1=Admin (`admin@loja.com`/`admin123`, tipo `admin`), 2=João (`joao@email.com`/`123456`), 3=Maria (`maria@email.com`/`senha123`) |
| pedidos, itens_pedido | vazios |

---

## S1 — Boot e configuração (SEC-01, SEC-06, LAY-06)

| ID | Pré-condição | Ação | Esperado |
|---|---|---|---|
| S1.1 | — | `unset SECRET_KEY; python app.py` | Não sobe. `Erro de configuração: Variavel de ambiente obrigatoria ausente: SECRET_KEY...`, exit code 1 |
| S1.2 | — | `SECRET_KEY=x DEBUG=true HOST=0.0.0.0 python app.py` | Não sobe. Erro citando o console interativo do Werkzeug |
| S1.3 | — | `SECRET_KEY=x DEBUG=true HOST=127.0.0.1 python app.py` | Sobe, `Debug mode: on` (aceitável só em loopback) |
| S1.4 | servidor no ar | `grep -rn "minha-chave-super-secreta" src/ app.py` | Nenhum resultado |
| S1.5 | servidor no ar | `req $BASE/` | 200, `mensagem`, `versao`, mapa de `endpoints` |
| S1.6 | servidor no ar | `req $BASE/health` | 200 com `status`, `database`, `counts` (produtos 10, usuarios 3, pedidos 0), `versao`. **Sem** `secret_key`, `debug`, `db_path`, `ambiente` |

> Retome o servidor do passo 0 (chave gerada, DEBUG off) antes de seguir.

---

## S2 — Catálogo público (DAT-05, DAT-06, API-03)

| ID | Ação | Esperado |
|---|---|---|
| S2.1 | `req $BASE/produtos` | 200, `dados` com 10 itens, `total: 10`, `limit: 50`, `offset: 0`. Nenhum campo além de id/nome/descricao/preco/estoque/categoria/ativo/criado_em |
| S2.2 | `req "$BASE/produtos?limit=3"` | 200, 3 itens, `total: 10`, `limit: 3` |
| S2.3 | `req "$BASE/produtos?limit=3&offset=9"` | 200, 1 item (id 10), `offset: 9` |
| S2.4 | `req "$BASE/produtos?limit=99999"` | 200, `limit: 200` (teto do servidor, não o pedido do cliente) |
| S2.5 | `req "$BASE/produtos?limit=-5"` | 200, `limit: 1` |
| S2.6 | `req $BASE/produtos/1` | 200, Notebook Gamer |
| S2.7 | `req $BASE/produtos/9999` | 404, `{"erro":"Produto não encontrado","sucesso":false}` |
| S2.8 | `req "$BASE/produtos/busca?q=mouse"` | 200, 1 item (Mouse Wireless), `total: 1` |
| S2.9 | `req "$BASE/produtos/busca?categoria=informatica&preco_min=100&preco_max=1000"` | 200, `total: 4` — ids 3, 5, 7, 9 (os de informática entre 100 e 1000) |
| S2.10 | `req "$BASE/produtos/busca?q="` | 200, 10 itens (termo vazio não filtra) |
| S2.11 | `req "$BASE/produtos/busca?preco_min=abc"` | **400** `preco_min deve ser um número` (antes era 500 com texto de exceção) |

---

## S3 — Cadastro e autenticação (SEC-04, API-03, API-05)

| ID | Ação | Esperado |
|---|---|---|
| S3.1 | `req -X POST $BASE/usuarios -H "$JSON" -d '{"nome":"Novo","email":"novo@email.com","senha":"segredo123"}'` | 201, `dados.id` = 4 |
| S3.2 | `req -X POST $BASE/usuarios -H "$JSON" -d '{"nome":"Dup","email":"joao@email.com","senha":"senha123"}'` | **409** `Email já cadastrado` |
| S3.3 | `req -X POST $BASE/usuarios -H "$JSON" -d '{"nome":"Sem Email","senha":"x"}'` | 400 `Nome, email e senha são obrigatórios` |
| S3.4 | `req -X POST $BASE/usuarios -H "$JSON" -d '{"nome":"Mail Ruim","email":"nao-eh-email","senha":"senha123"}'` | **400** `Email inválido` |
| S3.5 | `req -X POST $BASE/usuarios -H "$JSON" -d '{"nome":"Senha Curta","email":"curta@email.com","senha":"123"}'` | **400** `Senha deve ter ao menos 6 caracteres` |
| S3.6 | `req -X POST $BASE/login -H "$JSON" -d '{"email":"novo@email.com","senha":"segredo123"}'` | 200, `dados` (id/nome/email/tipo), `mensagem: "Login OK"`, **`token`**. Sem `senha` |
| S3.7 | `req -X POST $BASE/login -H "$JSON" -d '{"email":"novo@email.com","senha":"errada"}'` | 401 `Email ou senha inválidos` |
| S3.8 | `req -X POST $BASE/login -H "$JSON" -d '{"email":"","senha":""}'` | 400 `Email e senha são obrigatórios` |
| S3.9 | `req -X POST $BASE/login -H "$JSON" -d '{"email":"nao-existe@email.com","senha":"qualquer"}'` | 401 — mesma mensagem de S3.7 (não revela se o email existe) |
| S3.10 | `req $BASE/usuarios -H "Authorization: Bearer token-falso"` | 401 `Autenticação necessária` |
| S3.11 | Reinicie com `TOKEN_TTL_SECONDS=2`, faça login, espere 3 s, use o token | 401 (token expirado) |

---

## S4 — Autorização (SEC-05)

Rotas administrativas. Repita cada linha **sem header**, depois com `-H "$CH"`:

| ID | Ação | Sem token | Como cliente |
|---|---|---|---|
| S4.1 | `req $BASE/usuarios` | 401 | 403 |
| S4.2 | `req $BASE/usuarios/2` | 401 | 403 |
| S4.3 | `req $BASE/pedidos` | 401 | 403 |
| S4.4 | `req $BASE/relatorios/vendas` | 401 | 403 |
| S4.5 | `req -X POST $BASE/produtos -H "$JSON" -d '{}'` | 401 | 403 |
| S4.6 | `req -X PUT $BASE/produtos/1 -H "$JSON" -d '{}'` | 401 | 403 |
| S4.7 | `req -X DELETE $BASE/produtos/1` | 401 | 403 |
| S4.8 | `req -X PUT $BASE/pedidos/1/status -H "$JSON" -d '{"status":"aprovado"}'` | 401 | 403 |
| S4.9 | `req -X POST $BASE/admin/reset-db` | 401 | 403 |
| S4.10 | `req -X POST $BASE/pedidos -H "$JSON" -d '{"usuario_id":2,"itens":[{"produto_id":1,"quantidade":1}]}'` | 401 | 201 (é o próprio usuário) |

Posse de recurso e endpoint removido:

| ID | Ação | Esperado |
|---|---|---|
| S4.11 | `req $BASE/pedidos/usuario/2 -H "$CH"` | 200 (João é o usuário 2) |
| S4.12 | `req $BASE/pedidos/usuario/3 -H "$CH"` | **403** `Não é possível ver pedidos de outro usuário` |
| S4.13 | `req $BASE/pedidos/usuario/3 -H "$AH"` | 200 (admin vê qualquer um) |
| S4.14 | `req -X POST $BASE/pedidos -H "$CH" -H "$JSON" -d '{"usuario_id":3,"itens":[{"produto_id":1,"quantidade":1}]}'` | **403** `Não é possível criar pedido para outro usuário` |
| S4.15 | `req -X POST $BASE/admin/query -H "$AH" -H "$JSON" -d '{"sql":"SELECT 1"}'` | **404** `Rota não encontrada` — endpoint removido, inclusive para admin |
| S4.16 | `req $BASE/usuarios -H "$AH"` | 200, 4 usuários. **Nenhum** campo `senha` ou `senha_hash` |

---

## S5 — Checkout (DAT-02, API-03, LAY-02)

Pré-condição: S4.10 criou o pedido 1 (produto 1, qtd 1 → estoque de 1 passou a 9).

| ID | Ação | Esperado |
|---|---|---|
| S5.1 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":2,"itens":[{"produto_id":2,"quantidade":2},{"produto_id":3,"quantidade":1}]}'` | 201, `dados.pedido_id` = 2, `dados.total` = **479.7** |
| S5.2 | `req $BASE/produtos/2` e `req $BASE/produtos/3` | estoques 48 e 29 (debitados) |
| S5.3 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":2,"itens":[]}'` | 400 `Pedido deve ter pelo menos 1 item` |
| S5.4 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"itens":[{"produto_id":2,"quantidade":1}]}'` | 400 `Usuario ID é obrigatório` |
| S5.5 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":2,"itens":[{"produto_id":9999,"quantidade":1}]}'` | 400 `Produto 9999 não encontrado` |
| S5.6 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":2,"itens":[{"produto_id":6,"quantidade":999}]}'` | 400 `Estoque insuficiente para Cadeira Gamer` |
| S5.7 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":99999,"itens":[{"produto_id":2,"quantidade":1}]}'` | **400** `Usuário não encontrado` (antes gravava pedido órfão) |
| S5.8 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":2,"itens":[{"produto_id":2,"quantidade":-5}]}'` + `req $BASE/produtos/2` | **400**; estoque **continua 48** (antes a quantidade negativa aumentava o estoque) |
| S5.9 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":2,"itens":[{"produto_id":2}]}'` | **400** `Item 1: quantidade é obrigatória` (antes: 500 com escrita parcial) |
| S5.10 | `req -X POST $BASE/pedidos -H "$AH" -H "$JSON" -d '{"usuario_id":2,"itens":[{"produto_id":"2; DROP TABLE produtos","quantidade":1}]}'` | **400** (tipo inválido), e `req $BASE/produtos` segue 200 com 10 itens |
| S5.11 | `req $BASE/pedidos -H "$AH"` | 200, 2 pedidos, cada um com `itens` preenchidos e `produto_nome` correto, `total`/`limit`/`offset` presentes |
| S5.12 | Observe o log do servidor durante S5.1 | Linhas JSON `pedido criado` e `notificacao nao enviada (stub)`. **Não** deve aparecer `ENVIANDO EMAIL` |

---

## S6 — Status do pedido e devolução de estoque (LAY-02, API-05)

| ID | Ação | Esperado |
|---|---|---|
| S6.1 | `req -X PUT $BASE/pedidos/2/status -H "$AH" -H "$JSON" -d '{"status":"aprovado"}'` | 200 `Status atualizado` |
| S6.2 | `req -X PUT $BASE/pedidos/2/status -H "$AH" -H "$JSON" -d '{"status":"invalido"}'` | 400 `Status inválido` |
| S6.3 | `req -X PUT $BASE/pedidos/999999/status -H "$AH" -H "$JSON" -d '{"status":"aprovado"}'` | **404** `Pedido não encontrado` (antes respondia 200 para escrita que não ocorreu) |
| S6.4 | `req $BASE/produtos/2` (anote o estoque: 48) → `req -X PUT $BASE/pedidos/2/status -H "$AH" -H "$JSON" -d '{"status":"cancelado"}'` → `req $BASE/produtos/2` | 200 no cancelamento; estoque volta a **50** (as 2 unidades do pedido 2) |
| S6.5 | Repita o cancelamento do pedido 2 e cheque o estoque | 200, estoque **continua 50** — cancelar duas vezes não devolve estoque duas vezes |
| S6.6 | Log do servidor durante S6.4 | `status do pedido atualizado` com `estoque_devolvido: true` |

---

## S7 — Relatório de vendas (LAY-03, QUA-03)

Pré-condição: pedidos 1 (5999.99) e 2 (479.7, cancelado) existem.

| ID | Ação | Esperado |
|---|---|---|
| S7.1 | `req $BASE/relatorios/vendas -H "$AH"` | 200. `total_pedidos: 2`, `faturamento_bruto: 6479.69`, `pedidos_aprovados: 0`, `pedidos_cancelados: 1`, `pedidos_pendentes: 1` |
| S7.2 | Confira a faixa de desconto em S7.1 | Faturamento entre 5000 e 10000 → `desconto_aplicavel: 323.98` (5%) e `faturamento_liquido: 6155.71` |
| S7.3 | Crie um pedido de 1 unidade do produto 1 e repita | Faturamento > 10000 → desconto de **10%** |
| S7.4 | `req $BASE/relatorios/vendas` (sem token) | 401 |

---

## S8 — Segurança: injeção e exposição (SEC-02, SEC-03, SEC-04)

| ID | Ação | Esperado |
|---|---|---|
| S8.1 | `req -X POST $BASE/login -H "$JSON" -d '{"email":"joao@email.com","senha":"'"'"' OR '"'"'1'"'"'='"'"'1"}'` | **401** — não autentica (antes era bypass de autenticação) |
| S8.2 | `req -X POST $BASE/login -H "$JSON" -d "{\"email\":\"' OR 1=1 --\",\"senha\":\"x\"}"` | 401 |
| S8.3 | `req --get --data-urlencode "q='; DROP TABLE produtos; --" $BASE/produtos/busca` | 200, `dados: []`; em seguida `req $BASE/produtos` → 200 com 10 itens (tabela intacta) |
| S8.4 | `req -X POST $BASE/produtos -H "$AH" -H "$JSON" -d '{"nome":"Camiseta O'"'"'Brien","descricao":"aspa '"'"' no meio","preco":59.9,"estoque":5,"categoria":"vestuario"}'` | **201** (antes: 500 — a apóstrofe quebrava o INSERT). `req $BASE/produtos/11` devolve o nome literal |
| S8.5 | `req $BASE/usuarios/2 -H "$AH"` | 200 sem `senha`/`senha_hash` |
| S8.6 | `sqlite3 loja.db "SELECT email, senha_hash FROM usuarios WHERE id=2"` | Hash com prefixo `pbkdf2:` ou `scrypt:`; **não** contém `123456` |
| S8.7 | `sqlite3 loja.db "PRAGMA table_info(usuarios)"` | Existe `senha_hash`; **não** existe `senha` |
| S8.8 | Log do servidor durante os logins | `login aceito`/`login recusado` com `usuario_id`. **Nenhum** email ou senha no log |

---

## S9 — Fronteira HTTP (API-02, API-04, API-05)

| ID | Ação | Esperado |
|---|---|---|
| S9.1 | `req $BASE/rota-que-nao-existe` | 404 **em JSON**: `{"erro":"Rota não encontrada","sucesso":false}` (antes: página HTML) |
| S9.2 | `req -X DELETE $BASE/health` | 405 `Método não permitido`, em JSON |
| S9.3 | `python -c "print('{\"nome\":\"' + 'x'*120000 + '\"}')" > /tmp/grande.json`<br>`req -X POST $BASE/produtos -H "$AH" -H "$JSON" --data-binary @/tmp/grande.json` | **413** `Corpo da requisição muito grande` |
| S9.4 | `for i in $(seq 1 25); do curl -s -o /dev/null -w "%{http_code} " -X POST $BASE/login -H "$JSON" -d '{"email":"x@y.com","senha":"errada"}'; done; echo` | Primeiros ~20 em 401, depois **429** |
| S9.5 | `curl -s -i -H "Origin: http://localhost:3000" $BASE/produtos \| grep -i access-control-allow-origin` | Header presente com a origem permitida |
| S9.6 | `curl -s -i -H "Origin: http://evil.com" $BASE/produtos \| grep -i access-control-allow-origin` | **Nenhum** header (origem não autorizada) |
| S9.7 | `req -X POST $BASE/produtos -H "$AH" -H "$JSON" -d '{"nome":"Teste","preco":"abc","estoque":1}'` | **400** `Preço deve ser um número` (antes: 500 com texto de exceção) |
| S9.8 | `req -X POST $BASE/produtos -H "$AH" -H "$JSON" -d 'nao-eh-json'` | 400, corpo JSON com `sucesso:false` — nunca traceback nem nome de tabela |
| S9.9 | Compare erros de S2.7, S3.3 e S5.3 | Todos com a mesma forma: `{"erro": "...", "sucesso": false}` |

---

## S10 — Validação unificada e integridade (QUA-01, DAT-03, DAT-04)

| ID | Ação | Esperado |
|---|---|---|
| S10.1 | `req -X POST $BASE/produtos -H "$AH" -H "$JSON" -d '{"nome":"Y","preco":1,"estoque":1}'` | 400 `Nome muito curto` |
| S10.2 | `req -X PUT $BASE/produtos/11 -H "$AH" -H "$JSON" -d '{"nome":"Y","preco":1,"estoque":1}'` | **400** `Nome muito curto` — a atualização aplica a mesma regra da criação (antes: 200) |
| S10.3 | `req -X PUT $BASE/produtos/11 -H "$AH" -H "$JSON" -d '{"nome":"Camiseta Nova","preco":1,"estoque":1,"categoria":"inexistente"}'` | **400** `Categoria inválida. Válidas: [...]` (antes: 200) |
| S10.4 | `req -X PUT $BASE/produtos/11 -H "$AH" -H "$JSON" -d '{"nome":"Camiseta Nova","preco":69.9,"estoque":7,"categoria":"vestuario"}'` | 200 `Produto atualizado`; `req $BASE/produtos/11` reflete os novos valores |
| S10.5 | `req -X DELETE $BASE/produtos/2 -H "$AH"` | 200 `Produto deletado` |
| S10.6 | `req $BASE/produtos/2` | 404 — saiu do catálogo |
| S10.7 | `req $BASE/produtos` | Produto 2 ausente da lista; `total` decrementado |
| S10.8 | `req $BASE/pedidos -H "$AH"` | O pedido 2 ainda mostra `"produto_nome": "Mouse Wireless"` — **nunca** `"Desconhecido"` (exclusão lógica preservou o histórico) |
| S10.9 | `req -X DELETE $BASE/produtos/9999 -H "$AH"` | 404 `Produto não encontrado` |
| S10.10 | `sqlite3 loja.db ".schema itens_pedido"` | Declara `REFERENCES pedidos(id) ON DELETE CASCADE` e `REFERENCES produtos(id) ON DELETE RESTRICT` |
| S10.11 | `sqlite3 loja.db "SELECT ativo FROM produtos WHERE id=2"` | `0` — a coluna agora é usada (antes era sempre 1) |
| S10.12 | **Intrusivo, 1 linha.** Em `src/infra/database.py`, dentro de `connect`, depois do `PRAGMA foreign_keys`, adicione `connection.set_trace_callback(print)`. Reinicie, crie 3 pedidos, limpe o terminal e rode `req $BASE/pedidos -H "$AH"` | O terminal mostra **3** SELECTs (autenticação, listagem com JOIN, contagem), o mesmo número com 3 ou 300 pedidos — não `1 + pedidos + itens`. **Remova a linha ao final** |

---

## S11 — Rollback transacional (DAT-02) — teste intrusivo

Verifica o achado de maior severidade em integridade de dados. **Exige alteração
temporária de código**; reverta ao final.

1. Anote o estado: `req $BASE/pedidos -H "$AH"` (veja `total`) e
   `req $BASE/produtos/3` (veja o estoque).
2. Em `src/models/produto_model.py`, no início de `ajustar_estoque`, insira:
   ```python
   raise RuntimeError("falha simulada")
   ```
3. Reinicie o servidor e tente um pedido com **dois** itens:
   ```bash
   req -X POST $BASE/pedidos -H "$AH" -H "$JSON" \
     -d '{"usuario_id":2,"itens":[{"produto_id":3,"quantidade":1},{"produto_id":4,"quantidade":1}]}'
   ```
4. Esperado:
   - resposta **500** com corpo `{"erro":"Erro interno","sucesso":false}` — sem
     traceback, sem nome de tabela;
   - log do servidor com `transacao desfeita` e `erro nao tratado`;
   - `req $BASE/pedidos -H "$AH"` → `total` **inalterado** (nenhum pedido parcial);
   - `req $BASE/produtos/3` → estoque **inalterado**.
5. Faça uma escrita qualquer em seguida
   (`req -X POST $BASE/produtos -H "$AH" -H "$JSON" -d '{"nome":"Depois","preco":1,"estoque":1}'`)
   e confira novamente `req $BASE/pedidos -H "$AH"`: o `total` segue inalterado.
   **Este é o ponto central** — na versão anterior, a transação abandonada ficava
   pendente na conexão global e era efetivada pelo commit da requisição seguinte.
6. Remova o `raise`, reinicie, e confirme que o mesmo pedido agora responde 201.

---

## S12 — Verificações diretas no banco e no código

| ID | Ação | Esperado |
|---|---|---|
| S12.1 | `sqlite3 loja.db ".schema"` | FKs e índices declarados; `usuarios.email` com `UNIQUE`; `itens_pedido.quantidade` com `CHECK (quantidade > 0)` |
| S12.2 | Observe qualquer linha do log do servidor | JSON com `ts`, `level`, `logger` e `msg` — estruturado e filtrável. Rode com `LOG_LEVEL=WARNING` e confirme que as linhas `INFO` desaparecem |
| S12.3 | `grep -rn "' +\|\" +\|+ str(" src/ \| grep -iE "select\|insert\|update\|delete"` | Nenhum resultado — nenhuma consulta montada por concatenação |
| S12.4 | `grep -rnE "(^\|[^A-Za-z_])print\(" src/ app.py` | Só duas linhas: a menção em comentário em `notification_service.py` e `app.py:16`, que escreve o erro de configuração em `stderr` antes de o logging existir. Nenhum `print` em caminho de requisição — todo log passa por `logging` |
| S12.5 | `grep -rn "flask" src/models/` | Nenhum resultado — models não conhecem o framework |
| S12.6 | `grep -rniE "select \|cursor\|execute\(" src/controllers/` | Nenhum resultado — controllers não contêm SQL |
| S12.7 | `grep -rn "infra.database" src/ \| grep -v "^src/infra"` | Apenas `src/app.py` — só o composition root conhece a conexão |
| S12.8 | `python -c "from src.services.relatorio_service import desconto_por_faturamento as d; print(d(20000), d(6000), d(2000), d(100))"` | `2000.0 300.0 40.0 0` — a política de desconto roda sem Flask e sem banco |

---

## Matriz achado → caso

| Achado | Casos |
|---|---|
| SEC-05 controle de acesso | S4.1–S4.16 |
| SEC-03 injeção de SQL | S8.1–S8.4, S5.10, S12.3 |
| SEC-04 senha em texto puro | S8.6, S8.7, S3.6–S3.9 |
| SEC-02 exposição de dados | S4.16, S8.5, S8.8, S1.6 |
| SEC-01 segredo no código | S1.4, S1.6 |
| SEC-06 debug/CORS | S1.2, S1.3, S9.5, S9.6 |
| LAY-01 god files | S12.5–S12.7 (estrutura), todo o plano (comportamento) |
| LAY-02 regra no controller | S5.12, S6.4, S6.6 |
| LAY-03 regra no model | S12.8, S7.1–S7.3 |
| LAY-04 estado global | S11 passo 5 |
| LAY-05 bypass de camada | S12.6, S12.7, S4.15 |
| LAY-06 configuração no código | S1.1–S1.3 |
| DAT-02 estado parcial | S11 |
| DAT-03 integridade | S5.7, S10.5–S10.11, S12.1 |
| DAT-04 N+1 | S10.12 |
| DAT-05 paginação | S2.1–S2.5 |
| QUA-01 validação duplicada | S10.1–S10.4 |
| API-02 erro vazado | S9.1, S9.7–S9.9, S11 passo 4 |
| API-03 validação na fronteira | S2.11, S3.3–S3.5, S5.8–S5.10, S9.7 |
| API-04 middleware | S9.3–S9.6 |
| API-05 contrato | S6.3, S9.9, S3.2 |
| QUA-05 logging | S12.4, S5.12 |

Não cobertos por este plano (ver *Deferred* no relatório da Fase 3): rotação da
`SECRET_KEY`, migrações de schema, revogação de token, limitador compartilhado
entre workers, envio real de notificações.

---

## Registro de execução

| Suíte | Casos | Passou | Falhou | Observações |
|---|---|---|---|---|
| S1 Boot e configuração | 6 | | | |
| S2 Catálogo público | 11 | | | |
| S3 Cadastro e autenticação | 11 | | | |
| S4 Autorização | 16 | | | |
| S5 Checkout | 12 | | | |
| S6 Status e estoque | 6 | | | |
| S7 Relatório | 4 | | | |
| S8 Injeção e exposição | 8 | | | |
| S9 Fronteira HTTP | 9 | | | |
| S10 Validação e integridade | 12 | | | |
| S11 Rollback (intrusivo) | 1 | | | |
| S12 Banco e código | 8 | | | |
| **Total** | **104** | | | |

Executado por: ______________  Data: ______________
Commit: ______________  Versão: 1.0.0

### Ao terminar

```bash
rm -f loja.db        # descarta o banco de teste
git diff --stat      # confirme que S11 foi revertido
```
