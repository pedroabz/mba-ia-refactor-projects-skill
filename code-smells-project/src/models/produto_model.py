"""Persistencia e invariantes da entidade produto.

Toda consulta e parametrizada: nenhum valor vindo da requisicao entra no texto
do comando SQL. Os unicos fragmentos interpolados em `buscar` sao clausulas
escritas pelo proprio codigo.
"""

COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
NOME_TAMANHO_MINIMO = 2
NOME_TAMANHO_MAXIMO = 200


class ProdutoModel:
    def __init__(self, db):
        self._db = db

    # ---- leitura -------------------------------------------------------

    def listar(self, limit, offset=0):
        cursor = self._db.connection().execute(
            f"SELECT {COLUNAS} FROM produtos WHERE ativo = 1 "
            "ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return cursor.fetchall()

    def contar(self):
        return self._db.connection().execute(
            "SELECT COUNT(*) FROM produtos WHERE ativo = 1"
        ).fetchone()[0]

    def buscar_por_id(self, produto_id):
        return self._db.connection().execute(
            f"SELECT {COLUNAS} FROM produtos WHERE id = ? AND ativo = 1",
            (produto_id,),
        ).fetchone()

    def _filtros(self, termo, categoria, preco_min, preco_max):
        clausulas, parametros = ["ativo = 1"], []
        if termo:
            clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
            parametros += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clausulas.append("categoria = ?")
            parametros.append(categoria)
        if preco_min is not None:
            clausulas.append("preco >= ?")
            parametros.append(preco_min)
        if preco_max is not None:
            clausulas.append("preco <= ?")
            parametros.append(preco_max)
        return " AND ".join(clausulas), parametros

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None,
               limit=50, offset=0):
        where, parametros = self._filtros(termo, categoria, preco_min, preco_max)
        cursor = self._db.connection().execute(
            f"SELECT {COLUNAS} FROM produtos WHERE {where} ORDER BY id LIMIT ? OFFSET ?",
            (*parametros, limit, offset),
        )
        return cursor.fetchall()

    def contar_busca(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        where, parametros = self._filtros(termo, categoria, preco_min, preco_max)
        return self._db.connection().execute(
            f"SELECT COUNT(*) FROM produtos WHERE {where}", parametros
        ).fetchone()[0]

    # ---- escrita -------------------------------------------------------

    def criar(self, nome, descricao, preco, estoque, categoria):
        cursor = self._db.connection().execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        return cursor.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        cursor = self._db.connection().execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, "
            "categoria = ? WHERE id = ? AND ativo = 1",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )
        return cursor.rowcount > 0

    def desativar(self, produto_id):
        """Exclusao logica: preserva o historico de pedidos que referencia o produto."""
        cursor = self._db.connection().execute(
            "UPDATE produtos SET ativo = 0 WHERE id = ? AND ativo = 1",
            (produto_id,),
        )
        return cursor.rowcount > 0

    def ajustar_estoque(self, produto_id, delta):
        """Soma `delta` ao estoque. Negativo debita, positivo devolve."""
        cursor = self._db.connection().execute(
            "UPDATE produtos SET estoque = estoque + ? WHERE id = ?",
            (delta, produto_id),
        )
        return cursor.rowcount > 0
