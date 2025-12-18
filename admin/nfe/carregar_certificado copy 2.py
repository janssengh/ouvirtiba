import warnings
from cryptography.hazmat.primitives.serialization import pkcs12

def carregar_certificado(caminho_certificado: str, senha: str):
    """
    Carrega um certificado .pfx/.p12 e retorna:
      - private_key: objeto da chave privada
      - certificate: objeto do certificado principal
      - chain: lista de certificados intermediários (ou vazia)
    """

    with open(caminho_certificado, "rb") as f:
        pfx_data = f.read()

    # Suprime o aviso "fallback DER → BER"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        private_key, certificate, chain = pkcs12.load_key_and_certificates(
            pfx_data,
            senha.encode("utf-8")
        )

    if not private_key or not certificate:
        raise ValueError("❌ Certificado inválido ou senha incorreta.")

    # Garante que 'chain' seja sempre lista (mesmo se None)
    chain = chain if chain else []

    return private_key, certificate, chain
