from cryptography.hazmat.primitives.serialization import pkcs12
from signxml import XMLSigner, methods
from lxml import etree


def assinar_xml_nfce(xml_string, pfx_path, pfx_password):
    """
    Assina digitalmente o XML da NFC-e (tag <infNFe>) usando o certificado A1 (.pfx)
    Compatível com signxml 3.2.1 e SEFAZ (SHA1)
    """

    # 1️⃣ Carrega o certificado digital .pfx
    try:
        with open(pfx_path, "rb") as f:
            pfx_data = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Certificado não encontrado em: {pfx_path}")

    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data,
        pfx_password.encode()
    )

    if not private_key or not certificate:
        raise ValueError("Erro ao carregar chave privada ou certificado do .pfx")

    # 2️⃣ Converte o XML para estrutura manipulável
    parser = etree.XMLParser(remove_blank_text=True)
    xml = etree.fromstring(xml_string, parser)

    # 3️⃣ Localiza o elemento <infNFe>
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    infNFe = xml.find(".//nfe:infNFe", namespaces=ns)
    if infNFe is None:
        raise ValueError("Elemento <infNFe> não encontrado no XML!")

    # 4️⃣ Cria o objeto de assinatura compatível com SHA1 (aceito pela SEFAZ)
    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha1",
        digest_algorithm="sha1"
    )

    # 5️⃣ Executa a assinatura
    signed_inf = signer.sign(
        infNFe,
        key=private_key,
        cert=certificate
    )

    # 6️⃣ Substitui a tag <infNFe> original pela assinada
    xml.replace(infNFe, signed_inf)

    # 7️⃣ Retorna o XML assinado formatado
    xml_assinado = etree.tostring(
        xml,
        xml_declaration=True,
        encoding="utf-8",
        pretty_print=True
    )

    return xml_assinado
