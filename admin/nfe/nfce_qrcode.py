# Código Python para gerar o QR Code da NFC-e

import hashlib

token_id = '000001'
token_value = 'TESTE1234567890'

def generate_qrcode_url(access_key: str, ambiente: int, token_id: str, token_value: str) -> str:
    """
    Gera a URL do QR Code da NFC-e conforme padrão SEFAZ-SC.
    :param access_key: chave de acesso da nota (44 dígitos)
    :param ambiente: 1 = produção, 2 = homologação
    :param token_id: código do token fornecido pela SEFAZ
    :param token_value: chave secreta do token
    """
    versao_qrcode = '2'
    base_url = 'https://sat.sef.sc.gov.br/nfce/consulta'

    # Gerar o hash SHA1 (chave + token)
    texto_hash = access_key + token_value
    hash_qr = hashlib.sha1(texto_hash.encode('utf-8')).hexdigest().upper()

    # Montar URL final
    url = f"{base_url}?p={access_key}|{versao_qrcode}|{ambiente}|{token_id}|{hash_qr}"
    return url

