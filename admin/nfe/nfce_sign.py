# admin/nfe/nfce_sign.py
# ------------------------------------------------------------
# Assinatura XML NFC-e com certificado A1 (.pfx) - SHA256
# Compatível com SEFAZ SVRS (SC)
# ------------------------------------------------------------

from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from signxml import XMLSigner, methods
from lxml import etree

def assinar_xml_nfce(xml_string, pfx_path, pfx_password):
    """
    Assina digitalmente o XML da NFC-e (tag <infNFe>) usando certificado A1 (.pfx).
    - Usa SHA256
    - Método enveloped
    """

    # 1️⃣ Carrega certificado digital .pfx
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data,
        pfx_password.encode()
    )

    if not private_key or not certificate:
        raise ValueError("Erro ao carregar chave privada ou certificado do arquivo .pfx")

    # 2️⃣ Converte chave e certificado para PEM
    key_pem = private_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        NoEncryption()
    )
    cert_pem = certificate.public_bytes(Encoding.PEM)

    # 3️⃣ Prepara o XML para assinatura
    parser = etree.XMLParser(remove_blank_text=True)
    xml_root = etree.fromstring(xml_string, parser)

    # 4️⃣ Localiza a tag <infNFe>
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    infNFe = xml_root.find(".//nfe:infNFe", namespaces=ns)
    if infNFe is None:
        raise ValueError("Tag <infNFe> não encontrada no XML para assinatura!")

    # 5️⃣ Cria o objeto de assinatura SHA256
    signer = XMLSigner(
        method=methods.enveloped,
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
    )

    # 6️⃣ Executa assinatura no elemento <infNFe>
    signed_infNFe = signer.sign(
        infNFe,
        key=key_pem,
        cert=cert_pem
    )

    # 7️⃣ Substitui o nó original pelo assinado
    xml_root.replace(infNFe, signed_infNFe)

    # 8️⃣ Retorna o XML final assinado
    xml_assinado = etree.tostring(
        xml_root,
        xml_declaration=True,
        encoding="utf-8",
        pretty_print=True
    )

    return xml_assinado
