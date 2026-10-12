"""Controle de acesso aplicado na camada de rotas.

A politica e negar por padrao: um endpoint que precisa de identidade recebe o
decorator na definicao da rota, de modo que o controller nao pode ser alcancado
sem passar pela verificacao. Antes nao havia verificacao alguma, e o token do
login nunca existiu para ser conferido.
"""
import logging
from functools import wraps

from flask import g, request

from src.errors import Forbidden, Unauthorized

logger = logging.getLogger(__name__)

PREFIXO_BEARER = "bearer "
CHAVE_USUARIO = "current_user"


def usuario_atual():
    """Usuario autenticado desta requisicao. Só existe atrás de um guard."""
    usuario = g.get(CHAVE_USUARIO)
    if usuario is None:
        raise Unauthorized()
    return usuario


def _token_da_requisicao():
    cabecalho = request.headers.get("Authorization", "")
    if cabecalho.lower().startswith(PREFIXO_BEARER):
        return cabecalho[len(PREFIXO_BEARER):].strip()
    return request.headers.get("X-Auth-Token", "").strip() or None


class AuthGuard:
    """Fabrica de decorators de autenticacao e autorizacao."""

    def __init__(self, auth_service):
        self._auth = auth_service

    def _autenticar(self):
        usuario = self._auth.usuario_do_token(_token_da_requisicao())
        if usuario is None:
            raise Unauthorized()
        setattr(g, CHAVE_USUARIO, usuario)
        return usuario

    def require_auth(self, view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            self._autenticar()
            return view(*args, **kwargs)

        return wrapper

    def require_role(self, *papeis):
        def decorator(view):
            @wraps(view)
            def wrapper(*args, **kwargs):
                usuario = self._autenticar()
                if usuario["tipo"] not in papeis:
                    logger.warning(
                        "acesso negado",
                        extra={"usuario_id": usuario["id"], "papeis_exigidos": papeis},
                    )
                    raise Forbidden()
                return view(*args, **kwargs)

            return wrapper

        return decorator
