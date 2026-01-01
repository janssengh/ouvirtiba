import hashlib
from urllib.parse import urlencode
from config import NFeConfig as CFG

def gerar_qrcode_url(chave, valor_nf, digest_value):
    base_url = (
        CFG.URL_QRCODE_PROD if CFG.TP_AMB == 1 else CFG.URL_QRCODE_HOMOLOG
    )

    params = {
        "chNFe": chave,
        "nVersao": "100",
        "tpAmb": CFG.TP_AMB,
        "cIdToken": CFG.CSC_ID
    }

    # monta string para hash
    hash_string = (
        f"{chave}|100|{TP_AMB}|{valor_nf:.2f}|{digest_value}|"
        f"{CFG.CSC_ID}{CFG.CSC_TOKEN}"
    )

    hash_qr = hashlib.sha1(hash_string.encode()).hexdigest()

    params["cHashQRCode"] = hash_qr

    return f"{base_url}?{urlencode(params)}"

