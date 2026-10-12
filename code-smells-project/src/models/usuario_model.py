"""Persistencia da entidade usuario.

A coluna e `senha_hash`, nunca `senha`: o nome passa a dizer o que o valor e.
Nenhuma funcao daqui devolve o hash para fora da camada de dominio — quem
serializa decide, e o serializador publico nao o inclui.
"""

COLUNAS_PUBLICAS = "id, nome, email, tipo, criado_em"


class UsuarioModel:
    def __init__(self, db):
        self._db = db

    def listar(self, limit, offset=0):
        cursor = self._db.connection().execute(
            f"SELECT {COLUNAS_PUBLICAS} FROM usuarios ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return cursor.fetchall()

    def contar(self):
        return self._db.connection().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    def buscar_por_id(self, usuario_id):
        return self._db.connection().execute(
            f"SELECT {COLUNAS_PUBLICAS} FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()

    def existe(self, usuario_id):
        return self._db.connection().execute(
            "SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone() is not None

    def buscar_credenciais_por_email(self, email):
        """Usado apenas pela autenticacao: inclui o hash, por isso o nome explicito."""
        return self._db.connection().execute(
            "SELECT id, nome, email, tipo, senha_hash FROM usuarios WHERE email = ?",
            (email,),
        ).fetchone()

    def email_cadastrado(self, email):
        return self._db.connection().execute(
            "SELECT 1 FROM usuarios WHERE email = ?", (email,)
        ).fetchone() is not None

    def criar(self, nome, email, senha_hash, tipo="cliente"):
        cursor = self._db.connection().execute(
            "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
        return cursor.lastrowid
