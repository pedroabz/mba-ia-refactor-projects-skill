"""Persistencia da entidade pedido e dos seus itens.

As listagens trazem pedido e itens em uma unica consulta com JOIN — antes eram
`1 + P + I` consultas por resposta. A paginacao e aplicada aos pedidos por
subconsulta, nao as linhas do JOIN, para que uma pagina nao seja cortada no meio
de um pedido.
"""

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"

STATUS_VALIDOS = (
    STATUS_PENDENTE,
    STATUS_APROVADO,
    STATUS_ENVIADO,
    STATUS_ENTREGUE,
    STATUS_CANCELADO,
)

_SELECT_COM_ITENS = """
    SELECT  p.id            AS pedido_id,
            p.usuario_id    AS usuario_id,
            p.status        AS status,
            p.total         AS total,
            p.criado_em     AS criado_em,
            i.id            AS item_id,
            i.produto_id    AS produto_id,
            i.quantidade    AS quantidade,
            i.preco_unitario AS preco_unitario,
            pr.nome         AS produto_nome
      FROM pedidos p
      LEFT JOIN itens_pedido i ON i.pedido_id = p.id
      LEFT JOIN produtos pr    ON pr.id = i.produto_id
     WHERE p.id IN ({subconsulta})
     ORDER BY p.id, i.id
"""


class PedidoModel:
    def __init__(self, db):
        self._db = db

    # ---- leitura -------------------------------------------------------

    def listar_com_itens(self, limit, offset=0):
        sql = _SELECT_COM_ITENS.format(
            subconsulta="SELECT id FROM pedidos ORDER BY id LIMIT ? OFFSET ?"
        )
        return self._db.connection().execute(sql, (limit, offset)).fetchall()

    def listar_do_usuario_com_itens(self, usuario_id, limit, offset=0):
        sql = _SELECT_COM_ITENS.format(
            subconsulta="SELECT id FROM pedidos WHERE usuario_id = ? "
                        "ORDER BY id LIMIT ? OFFSET ?"
        )
        return self._db.connection().execute(sql, (usuario_id, limit, offset)).fetchall()

    def contar(self):
        return self._db.connection().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]

    def contar_do_usuario(self, usuario_id):
        return self._db.connection().execute(
            "SELECT COUNT(*) FROM pedidos WHERE usuario_id = ?", (usuario_id,)
        ).fetchone()[0]

    def buscar_por_id(self, pedido_id):
        return self._db.connection().execute(
            "SELECT id, usuario_id, status, total, criado_em FROM pedidos WHERE id = ?",
            (pedido_id,),
        ).fetchone()

    def itens_do_pedido(self, pedido_id):
        return self._db.connection().execute(
            "SELECT produto_id, quantidade, preco_unitario FROM itens_pedido "
            "WHERE pedido_id = ? ORDER BY id",
            (pedido_id,),
        ).fetchall()

    # ---- agregacoes: a contagem e a soma ficam no banco ----------------

    def faturamento_total(self):
        return self._db.connection().execute(
            "SELECT COALESCE(SUM(total), 0) FROM pedidos"
        ).fetchone()[0]

    def contagem_por_status(self):
        rows = self._db.connection().execute(
            "SELECT status, COUNT(*) FROM pedidos GROUP BY status"
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    # ---- escrita -------------------------------------------------------

    def criar(self, usuario_id, total, status=STATUS_PENDENTE):
        cursor = self._db.connection().execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, status, total),
        )
        return cursor.lastrowid

    def adicionar_item(self, pedido_id, produto_id, quantidade, preco_unitario):
        self._db.connection().execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
            "VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )

    def atualizar_status(self, pedido_id, novo_status):
        cursor = self._db.connection().execute(
            "UPDATE pedidos SET status = ? WHERE id = ?",
            (novo_status, pedido_id),
        )
        return cursor.rowcount > 0
