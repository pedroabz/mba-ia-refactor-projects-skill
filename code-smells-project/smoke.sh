#!/usr/bin/env bash
# Sobe a aplicacao, exercita os endpoints principais e derruba o servidor.
#
#   ./smoke.sh            # porta 5001
#   ./smoke.sh 5005       # outra porta
#
# Sai com codigo 0 se tudo passou, 1 na primeira falha.
set -uo pipefail

PORT="${1:-5001}"
BASE="http://127.0.0.1:${PORT}"
cd "$(cd "$(dirname "$0")" && pwd)" || exit 1

falhas=0

verifica() { # verifica <descricao> <esperado> <obtido>
  if [ "$2" = "$3" ]; then
    printf '  ok    %s\n' "$1"
  else
    printf '  FALHA %s (esperado %s, obtido %s)\n' "$1" "$2" "$3"
    falhas=$((falhas + 1))
  fi
}

status() { # status <metodo> <rota> [corpo-json] [token]
  local metodo="$1" rota="$2" corpo="${3:-}" token="${4:-}"
  local args=(-sS -o /tmp/smoke-body.json -w '%{http_code}' -X "$metodo" "${BASE}${rota}")
  [ -n "$corpo" ] && args+=(-H 'Content-Type: application/json' -d "$corpo")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer ${token}")
  curl "${args[@]}"
}

echo "==> 1/5 ambiente"
if [ ! -x .venv/bin/python ]; then
  echo "    criando .venv"
  python3 -m venv .venv || exit 1
fi
.venv/bin/pip install -q -r requirements.txt || exit 1
.venv/bin/python -c "import flask, flask_cors, itsdangerous, werkzeug" || exit 1
echo "    dependencias ok"

echo "==> 2/5 porta ${PORT}"
if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "    porta ocupada:"
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN | sed 's/^/      /'
  echo "    libere com: lsof -ti:${PORT} -sTCP:LISTEN | xargs kill"
  exit 1
fi
echo "    livre"

echo "==> 3/5 subindo o servidor"
export SECRET_KEY="${SECRET_KEY:-$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')}"
PORT="${PORT}" HOST=127.0.0.1 .venv/bin/python app.py > /tmp/smoke-server.log 2>&1 &
servidor=$!
trap 'kill ${servidor} 2>/dev/null' EXIT

# As tentativas recusadas enquanto o servidor sobe vao para o log, nao para o terminal.
if ! curl -sS --retry 40 --retry-delay 1 --retry-connrefused \
     -o /dev/null "${BASE}/health" 2>>/tmp/smoke-server.log; then
  echo "    servidor nao respondeu. log:"
  sed 's/^/      /' /tmp/smoke-server.log
  exit 1
fi
echo "    no ar em ${BASE} (log: /tmp/smoke-server.log)"

echo "==> 4/5 endpoints"
verifica "GET  /health"                200 "$(status GET /health)"
verifica "GET  /produtos"              200 "$(status GET /produtos)"
verifica "GET  /produtos/1"            200 "$(status GET /produtos/1)"
verifica "GET  /produtos/9999"         404 "$(status GET /produtos/9999)"
verifica "GET  /usuarios sem token"    401 "$(status GET /usuarios)"

TOKEN=$(curl -sS -X POST "${BASE}/login" -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])' 2>/dev/null)
if [ -z "${TOKEN}" ]; then
  echo "  FALHA login do admin nao devolveu token"
  falhas=$((falhas + 1))
else
  printf '  ok    POST /login devolveu token (%s caracteres)\n' "${#TOKEN}"
fi

verifica "GET  /usuarios com token"    200 "$(status GET /usuarios '' "${TOKEN}")"
verifica "GET  /relatorios/vendas"     200 "$(status GET /relatorios/vendas '' "${TOKEN}")"
verifica "POST /pedidos"               201 "$(status POST /pedidos '{"usuario_id":2,"itens":[{"produto_id":2,"quantidade":2}]}' "${TOKEN}")"
verifica "GET  /pedidos"               200 "$(status GET /pedidos '' "${TOKEN}")"
verifica "POST /admin/query removido"  404 "$(status POST /admin/query '{"sql":"SELECT 1"}' "${TOKEN}")"
verifica "POST /login com injecao"     401 "$(status POST /login '{"email":"joao@email.com","senha":"'"'"' OR '"'"'1'"'"'='"'"'1"}')"

senha_exposta=$(curl -sS "${BASE}/usuarios" -H "Authorization: Bearer ${TOKEN}" | grep -c '"senha"')
verifica "senha fora da resposta"      0 "${senha_exposta}"

echo "==> 5/5 resultado"
if [ "${falhas}" -eq 0 ]; then
  echo "    tudo passou"
  exit 0
fi
echo "    ${falhas} falha(s)"
exit 1
