import warnings
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    PrivateFormat,
    NoEncryption
)

def carregar_certificado(caminho_certificado: str, senha: str):
    """
    Carrega um certificado .pfx/.p12 e retorna (cert_pem_bytes, key_pem_bytes).
    Remove o aviso BER/DER e usa os enums corretos.
    """
    with open(caminho_certificado, "rb") as f:
        pfx_data = f.read()


    # Suprime aviso de fallback DER → BER
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        private_key, certificate, chain = pkcs12.load_key_and_certificates(
            pfx_data,
            senha.encode("utf-8")
        )

    if not private_key or not certificate:
        raise ValueError("Certificado inválido ou senha incorreta.")

    # Garante que 'chain' seja uma lista (pode vir como None)
    chain = chain if chain else []

    # ✅ Usa os enums corretos
    cert_pem = certificate.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        NoEncryption()
    )

    return cert_pem, key_pem, chain
    #return private_key, certificate, chain
