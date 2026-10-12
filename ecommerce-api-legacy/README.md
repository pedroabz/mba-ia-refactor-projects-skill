# ecommerce-api-legacy

API de matrícula em cursos online com checkout pago, em Node.js/Express. Entrada do desafio
`refactor-arch`, agora refatorada para MVC.

## Como rodar

```bash
npm install
cp .env.example .env     # opcional em desenvolvimento; obrigatório em produção
npm start
```

A aplicação sobe em `http://127.0.0.1:3100` — 3100 e não 3000 porque a porta 3000 é
disputada por quase todo servidor de desenvolvimento e por containers que a publicam.
`PORT` sobrescreve. O banco SQLite é em memória por padrão
(`DATABASE_FILE=:memory:`), então o schema e os seeds são recriados a cada boot e nada
sobrevive a um restart. Exemplos de requisições estão em `api.http`.

Nenhuma variável de ambiente é obrigatória em desenvolvimento. Em produção
(`NODE_ENV=production`) a aplicação **se recusa a subir** sem `AUTH_TOKEN_SECRET` e sem um
adaptador de pagamento real — ver `.env.example`.

## Estrutura

```
src/
├── config/         configuração a partir do ambiente (único módulo que lê process.env)
├── domain/         vocabulário e tipos de erro do domínio
├── infra/          conexão, schema/seeds, logger
├── models/         persistência por entidade, sem HTTP
├── services/       casos de uso, integrações e a fronteira transacional
├── controllers/    fluxo da aplicação: valida, orquestra, escolhe o status
├── routes/         superfície de entrada: caminho → controller, e os schemas de request
├── middlewares/    autenticação, rate limit, validação, log, erros
└── app.js          composition root
```

Dependências apontam para dentro: `routes → controllers → services → models → persistência`.
Nenhum módulo abaixo de `routes/` importa Express, e nenhum módulo acima de `models/`
escreve SQL.

## Autenticação

As rotas administrativas exigem um token Bearer com papel `admin`. Obtenha um em
`POST /api/auth/login`. Em desenvolvimento, os seeds criam:

| e-mail | papel | senha (de `.env.example`) |
|---|---|---|
| `leonan@fullcycle.com.br` | `student` | `SEED_STUDENT_PASSWORD` |
| `admin@fullcycle.com.br` | `admin` | `SEED_ADMIN_PASSWORD` |

Senhas são armazenadas com `scrypt` (salt por usuário, custo configurável). Seeding é
recusado em produção.

## Endpoints

| Método | Caminho | Acesso | Resposta |
|---|---|---|---|
| `POST` | `/api/auth/login` | público | `200 {token, expiresInSeconds, role}` |
| `POST` | `/api/checkout` | público | `201 {enrollmentId, courseId, amount, status}` |
| `GET` | `/api/admin/financial-report` | `admin` | `200 [{course, revenue, students}]` |
| `DELETE` | `/api/users/:id` | `admin` | `204` |

### Convenção de resposta

Sucesso devolve o recurso (ou uma coleção). Falha devolve sempre JSON na mesma forma:

```json
{ "error": { "code": "validation_error", "message": "...", "details": { "email": "..." } } }
```

`code` é o identificador estável para o cliente ramificar; `message` é para humanos e pode
mudar. Status usados: `400` validação, `401` sem credencial, `403` papel insuficiente,
`402` pagamento recusado pelo provedor, `404` recurso inexistente, `429` rate limit.

### Checkout

Aceita os nomes canônicos `name`, `email`, `password`, `courseId`, `cardNumber`. Os nomes
abreviados originais (`usr`, `eml`, `pwd`, `c_id`, `card`) continuam aceitos como **aliases
depreciados** — o uso é registrado em log com nível `warn`. `password` é obrigatório: não há
mais senha padrão para checkouts sem o campo.

### Relatório financeiro

Paginado por cursos: `?limit=&offset=`, com default `REPORT_DEFAULT_PAGE_SIZE` e máximo
`REPORT_MAX_PAGE_SIZE` impostos pelo servidor. O total e a página vão nos headers
`X-Total-Count`, `X-Page-Limit` e `X-Page-Offset`; o corpo continua sendo o array de cursos.

Os limites são assimétricos de propósito: `limit` acima do máximo é **reduzido** ao máximo
(pedir tudo é um pedido legítimo, que o servidor limita), enquanto `limit` menor que 1 é
**recusado** com `400` — uma página vazia por pedido explícito não significa nada.

A receita é somada pelo banco e conta apenas pagamentos `PAID`, portanto é independente de
quantos alunos a resposta traz. A lista de alunos de cada curso é limitada a
`REPORT_MAX_STUDENTS_PER_COURSE`; quando há truncamento, uma linha de log `warn` registra
quantas matrículas existiam e quantas entraram.

### Remoção de usuário

Remover um usuário **anonimiza** a conta (nome, e-mail e hash de senha são apagados e
`deleted_at` é marcado) em vez de apagar a linha. Matrículas e pagamentos são registros
financeiros e continuam vinculados a uma linha válida; no relatório o aluno passa a aparecer
como `Conta removida`. O schema declara chaves estrangeiras `ON DELETE RESTRICT` e a conexão
habilita `PRAGMA foreign_keys`, então o banco recusa qualquer deleção que deixaria esses
registros órfãos.

## Limitações conhecidas

- **O gateway de pagamento é um stub.** `PAYMENT_DRIVER=stub` aprova qualquer cartão que
  comece com `4`, sem contatar provedor algum — é a regra original do código legado,
  isolada atrás de uma interface em `services/payment.gateway.js`. Produção se recusa a
  usá-la. Um adaptador real precisa validar o cartão, chamar o provedor e manter o PAN fora
  da aplicação.
- **Rate limiting é em processo**, portanto por instância: com várias réplicas o limite
  efetivo é multiplicado pelo número de réplicas. Um store compartilhado (Redis) é a
  resposta para produção.
- **Sem migrations.** O schema é criado no boot; evoluí-lo exige editar `infra/schema.js`.
- **Sem testes automatizados** no projeto.
- **A trilha de auditoria é somente-escrita**: `audit_logs` é gravada dentro da transação de
  checkout, mas nenhum endpoint a lê ainda.
