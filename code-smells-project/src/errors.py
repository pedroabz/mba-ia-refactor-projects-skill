"""Tipos de erro da aplicacao.

Cada erro carrega o status HTTP e a mensagem que o cliente pode ver. Quem levanta
nao formata resposta; quem formata e o error handler registrado no composition
root (um lugar, nao dezessete blocos try/except).
"""


class AppError(Exception):
    """Erro esperado, com status e mensagem seguros para o cliente."""

    status = 500
    mensagem = "Erro interno"

    def __init__(self, mensagem=None, detalhes=None):
        super().__init__(mensagem or self.mensagem)
        if mensagem:
            self.mensagem = mensagem
        self.detalhes = detalhes


class ValidationError(AppError):
    status = 400
    mensagem = "Dados inválidos"


class BusinessRuleError(AppError):
    """Regra de negocio recusou a operacao — entrada bem formada, pedido invalido."""

    status = 400
    mensagem = "Operação não permitida"


class NotFound(AppError):
    status = 404
    mensagem = "Recurso não encontrado"


class Unauthorized(AppError):
    status = 401
    mensagem = "Autenticação necessária"


class Forbidden(AppError):
    status = 403
    mensagem = "Acesso negado"


class Conflict(AppError):
    status = 409
    mensagem = "Conflito com o estado atual"


class RateLimited(AppError):
    status = 429
    mensagem = "Muitas requisições. Tente novamente em instantes."
