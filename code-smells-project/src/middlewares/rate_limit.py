"""Limite de requisicoes por janela, para as rotas que o exigem.

Escopo deliberado: login (forca bruta de senha) e rotas administrativas
(operacoes destrutivas). O contador e por IP e por escopo, com janela fixa, e o
dicionario e podado a cada janela — estado com dono, limite e regra de descarte
explicitos.

Processo unico. Com varios workers, troque esta implementacao por um limitador
com armazenamento compartilhado; o ponto de troca e o composition root.
"""
import logging
import time
from functools import wraps

from flask import request

from src.errors import RateLimited

logger = logging.getLogger(__name__)

JANELA_SEGUNDOS = 60


class RateLimiter:
    def __init__(self, enabled=True, janela_segundos=JANELA_SEGUNDOS):
        self._enabled = enabled
        self._janela = janela_segundos
        self._contadores = {}
        self._janela_atual = None

    def _chave(self, escopo):
        return (escopo, request.remote_addr or "desconhecido")

    def _registrar(self, escopo, maximo):
        janela = int(time.time() // self._janela)
        if janela != self._janela_atual:
            self._contadores.clear()
            self._janela_atual = janela

        chave = self._chave(escopo)
        usados = self._contadores.get(chave, 0) + 1
        self._contadores[chave] = usados
        return usados <= maximo

    def limit(self, escopo, maximo):
        def decorator(view):
            @wraps(view)
            def wrapper(*args, **kwargs):
                if self._enabled and not self._registrar(escopo, maximo):
                    logger.warning("limite de requisicoes atingido",
                                   extra={"escopo": escopo, "maximo": maximo})
                    raise RateLimited()
                return view(*args, **kwargs)

            return wrapper

        return decorator
