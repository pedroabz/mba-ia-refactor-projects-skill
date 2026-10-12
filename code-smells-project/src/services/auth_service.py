"""Autenticacao: derivacao de senha e emissao/verificacao de token.

Senhas sao gravadas com `generate_password_hash` (PBKDF2 com sal por usuario,
que acompanha o Werkzeug — sem dependencia nova) e verificadas pela funcao de
comparacao da propria biblioteca, nunca com `==` e nunca dentro do SQL.

O token e assinado com a SECRET_KEY e tem validade: um token emitido e de fato
verificado em cada requisicao protegida, ao contrario do login anterior, que
devolvia o usuario e nao produzia nada verificavel.
"""
import logging

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

SENHA_TAMANHO_MINIMO = 6
TOKEN_SALT = "autenticacao-loja"


class AuthService:
    def __init__(self, usuario_model, secret_key, token_ttl_seconds=3600):
        self._usuarios = usuario_model
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)
        self._ttl = token_ttl_seconds

    # ---- senhas --------------------------------------------------------

    @staticmethod
    def hash_senha(senha):
        return generate_password_hash(senha)

    # ---- login ---------------------------------------------------------

    def autenticar(self, email, senha):
        """Devolve os dados publicos do usuario, ou None se as credenciais falham."""
        registro = self._usuarios.buscar_credenciais_por_email(email)
        if registro is None:
            # Mesmo custo e mesma resposta de uma senha errada: nao revela se o
            # email existe.
            check_password_hash(generate_password_hash("inexistente"), senha)
            return None
        if not check_password_hash(registro["senha_hash"], senha):
            return None
        return {
            "id": registro["id"],
            "nome": registro["nome"],
            "email": registro["email"],
            "tipo": registro["tipo"],
        }

    # ---- token ---------------------------------------------------------

    def emitir_token(self, usuario):
        return self._serializer.dumps({"id": usuario["id"], "tipo": usuario["tipo"]})

    def usuario_do_token(self, token):
        """Verifica assinatura e validade e devolve o usuario atual, ou None."""
        if not token:
            return None
        try:
            payload = self._serializer.loads(token, max_age=self._ttl)
        except SignatureExpired:
            logger.info("token expirado")
            return None
        except BadSignature:
            logger.warning("token com assinatura invalida")
            return None

        registro = self._usuarios.buscar_por_id(payload.get("id"))
        if registro is None:
            return None
        # O tipo vem do banco, nao do token: uma mudanca de papel vale na hora.
        return {
            "id": registro["id"],
            "nome": registro["nome"],
            "email": registro["email"],
            "tipo": registro["tipo"],
        }
