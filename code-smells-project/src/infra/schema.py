"""Criacao de schema e carga inicial — passo explicito, nao efeito de leitura.

Antes isto acontecia dentro do getter da conexao, o que significava que ninguem
conseguia abrir uma conexao sem tambem criar tabelas e inserir dados. Aqui e uma
operacao nomeada que o composition root chama uma vez no boot.
"""
import logging

logger = logging.getLogger(__name__)

DDL = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT NOT NULL DEFAULT '',
        preco REAL NOT NULL,
        estoque INTEGER NOT NULL,
        categoria TEXT NOT NULL DEFAULT 'geral',
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
        status TEXT NOT NULL DEFAULT 'pendente',
        total REAL NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
        produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
        quantidade INTEGER NOT NULL CHECK (quantidade > 0),
        preco_unitario REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pedidos_usuario ON pedidos(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_itens_pedido ON itens_pedido(pedido_id)",
    "CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens_pedido(produto_id)",
)

PRODUTOS_SEED = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
)

# Credenciais de desenvolvimento: gravadas com hash pela funcao injetada, nunca
# em texto puro. Em producao o seed de usuarios deve ser desligado.
USUARIOS_SEED = (
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
)


def create_schema(connection):
    """Cria tabelas e indices se ainda nao existirem."""
    for statement in DDL:
        connection.execute(statement)
    connection.commit()
    logger.info("schema verificado")


def seed_if_empty(connection, hash_password):
    """Insere os dados de exemplo apenas em um banco vazio."""
    already_populated = connection.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    if already_populated:
        return False

    connection.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
        "VALUES (?, ?, ?, ?, ?)",
        PRODUTOS_SEED,
    )
    connection.executemany(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
        [(nome, email, hash_password(senha), tipo) for nome, email, senha, tipo in USUARIOS_SEED],
    )
    connection.commit()
    logger.info(
        "carga inicial aplicada",
        extra={"produtos": len(PRODUTOS_SEED), "usuarios": len(USUARIOS_SEED)},
    )
    return True
