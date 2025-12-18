import warnings
from cryptography.hazmat.primitives.serialization import pkcs12

def carregar_certificado(caminho_certificado: str, senha: str):
    """
    Carrega o certificado digital .pfx (A1) e retorna:
      - private_key: objeto da chave privada
      - certificate: certificado principal
      - chain: lista de certificados intermediários (ou vazia)
    """

    with open(caminho_certificado, "rb") as f:
        pfx_data = f.read()

    # Ignora warning BER/DER
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        private_key, certificate, chain = pkcs12.load_key_and_certificates(
            pfx_data, senha.encode("utf-8")
        )

    if not private_key or not certificate:
        raise ValueError("❌ Certificado inválido ou senha incorreta.")

    chain = list(chain) if chain else []

    print(f"✅ Certificado carregado: {certificate.subject}")
    print(f"🔗 Intermediários detectados: {len(chain)}")

    return private_key, certificate, chain
