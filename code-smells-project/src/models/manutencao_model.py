"""Operacoes de diagnostico e manutencao do banco.

Antes viviam soltas: as contagens dentro do handler de health check e os DELETE
dentro do arquivo de entrada da aplicacao.
"""

# Ordem filho -> pai: com as chaves estrangeiras ativas, o inverso e recusado.
TABELAS_EM_ORDEM_DE_EXCLUSAO = ("itens_pedido", "pedidos", "produtos", "usuarios")


class ManutencaoModel:
    def __init__(self, db):
        self._db = db

    def ping(self):
        """Confirma que a conexao responde."""
        self._db.connection().execute("SELECT 1").fetchone()
        return True

    def contagens(self):
        connection = self._db.connection()
        return {
            "produtos": connection.execute(
                "SELECT COUNT(*) FROM produtos WHERE ativo = 1"
            ).fetchone()[0],
            "usuarios": connection.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0],
            "pedidos": connection.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0],
        }

    def apagar_tudo(self):
        """Esvazia as tabelas em uma unica transacao."""
        with self._db.transaction() as connection:
            for tabela in TABELAS_EM_ORDEM_DE_EXCLUSAO:
                connection.execute(f"DELETE FROM {tabela}")
        return True
