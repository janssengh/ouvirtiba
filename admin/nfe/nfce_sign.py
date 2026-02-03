# admin/nfe/nfce_sign.py
"""
Módulo para assinatura digital de XMLs da NFC-e usando certificado A1 (.pfx)
Padrão XML-DSig conforme especificação da SEFAZ
"""

from lxml import etree
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography import x509
import base64
import hashlib


def assinar_xml_nfce(xml_content, pfx_path, pfx_password):
    """
    Assina digitalmente o XML da NFC-e usando certificado A1
    
    Args:
        xml_content (bytes ou str): Conteúdo do XML a ser assinado
        pfx_path (str): Caminho do arquivo .pfx do certificado
        pfx_password (str): Senha do certificado
    
    Returns:
        bytes: XML assinado em bytes
    
    Raises:
        Exception: Erro na leitura do certificado ou assinatura
    """
    
    # ============================================================
    # 1. CARREGA O CERTIFICADO DIGITAL (.pfx)
    # ============================================================
    try:
        with open(pfx_path, 'rb') as f:
            pfx_data = f.read()
    except FileNotFoundError:
        raise Exception(f"❌ Certificado não encontrado em: {pfx_path}")
    except Exception as e:
        raise Exception(f"❌ Erro ao ler certificado: {e}")
    
    try:
        # Extrai chave privada e certificado do arquivo .pfx
        from cryptography.hazmat.primitives.serialization import pkcs12
        
        private_key, certificate, ca_certs = pkcs12.load_key_and_certificates(
            pfx_data,
            pfx_password.encode() if isinstance(pfx_password, str) else pfx_password,
            backend=default_backend()
        )
    except ValueError as e:
        raise Exception(f"❌ Senha incorreta ou certificado inválido: {e}")
    except Exception as e:
        raise Exception(f"❌ Erro ao extrair dados do certificado: {e}")
    
    # ============================================================
    # 2. PARSER DO XML
    # ============================================================
    try:
        if isinstance(xml_content, str):
            xml_content = xml_content.encode('utf-8')
        
        parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
        root = etree.fromstring(xml_content, parser)
    except Exception as e:
        raise Exception(f"❌ Erro ao fazer parse do XML: {e}")
    
    # ============================================================
    # 3. LOCALIZA A TAG <infNFe> PARA ASSINAR
    # ============================================================
    namespace = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    infNFe = root.find('.//nfe:infNFe', namespace)
    if infNFe is None:
        raise Exception("❌ Tag <infNFe> não encontrada no XML")
    
    # Pega o ID da tag infNFe (ex: NFe42260156154376000105650010000000012412469927)
    uri_reference = infNFe.get('Id')
    if not uri_reference:
        raise Exception("❌ Atributo 'Id' não encontrado na tag <infNFe>")
    
    # ============================================================
    # 4. CANONICALIZA A TAG <infNFe> (C14N)
    # ============================================================
    try:
        # Canonicalização exclusiva (C14N) conforme padrão XML-DSig
        canonicalized_xml = etree.tostring(
            infNFe,
            method='c14n',
            exclusive=True,
            with_comments=False
        )
    except Exception as e:
        raise Exception(f"❌ Erro na canonicalização: {e}")
    
    # ============================================================
    # 5. CALCULA O DIGEST (SHA-1) DO XML CANONICALIZADO
    # ============================================================
    try:
        digest = hashlib.sha1(canonicalized_xml).digest()
        digest_value = base64.b64encode(digest).decode('utf-8')
    except Exception as e:
        raise Exception(f"❌ Erro ao calcular digest: {e}")
    
    # ============================================================
    # 6. MONTA A TAG <SignedInfo>
    # ============================================================
    ds_namespace = "http://www.w3.org/2000/09/xmldsig#"
    
    signed_info = etree.Element(
        f"{{{ds_namespace}}}SignedInfo",
        nsmap={'ds': ds_namespace}
    )
    
    # CanonicalizationMethod
    canonicalization_method = etree.SubElement(
        signed_info,
        f"{{{ds_namespace}}}CanonicalizationMethod",
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    )
    
    # SignatureMethod (RSA-SHA1)
    signature_method = etree.SubElement(
        signed_info,
        f"{{{ds_namespace}}}SignatureMethod",
        Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"
    )
    
    # Reference
    reference = etree.SubElement(
        signed_info,
        f"{{{ds_namespace}}}Reference",
        URI=f"#{uri_reference}"
    )
    
    # Transforms
    transforms = etree.SubElement(reference, f"{{{ds_namespace}}}Transforms")
    
    transform1 = etree.SubElement(
        transforms,
        f"{{{ds_namespace}}}Transform",
        Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"
    )
    
    transform2 = etree.SubElement(
        transforms,
        f"{{{ds_namespace}}}Transform",
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    )
    
    # DigestMethod (SHA-1)
    digest_method = etree.SubElement(
        reference,
        f"{{{ds_namespace}}}DigestMethod",
        Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"
    )
    
    # DigestValue
    digest_value_elem = etree.SubElement(reference, f"{{{ds_namespace}}}DigestValue")
    digest_value_elem.text = digest_value
    
    # ============================================================
    # 7. CANONICALIZA O <SignedInfo>
    # ============================================================
    try:
        signed_info_c14n = etree.tostring(
            signed_info,
            method='c14n',
            exclusive=False,
            with_comments=False
        )
    except Exception as e:
        raise Exception(f"❌ Erro ao canonicalizar SignedInfo: {e}")
    
    # ============================================================
    # 8. ASSINA O <SignedInfo> COM A CHAVE PRIVADA
    # ============================================================
    try:
        signature_bytes = private_key.sign(
            signed_info_c14n,
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        signature_value = base64.b64encode(signature_bytes).decode('utf-8')
    except Exception as e:
        raise Exception(f"❌ Erro ao assinar: {e}")
    
    # ============================================================
    # 9. EXTRAI O CERTIFICADO EM BASE64
    # ============================================================
    try:
        cert_pem = certificate.public_bytes(
            encoding=serialization.Encoding.DER
        )
        x509_certificate = base64.b64encode(cert_pem).decode('utf-8')
    except Exception as e:
        raise Exception(f"❌ Erro ao extrair certificado: {e}")
    
    # ============================================================
    # 10. MONTA A TAG <Signature> COMPLETA
    # ============================================================
    signature = etree.Element(
        f"{{{ds_namespace}}}Signature",
        nsmap={'ds': ds_namespace}
    )
    
    # Adiciona SignedInfo
    signature.append(signed_info)
    
    # SignatureValue
    signature_value_elem = etree.SubElement(signature, f"{{{ds_namespace}}}SignatureValue")
    signature_value_elem.text = signature_value
    
    # KeyInfo
    key_info = etree.SubElement(signature, f"{{{ds_namespace}}}KeyInfo")
    
    x509_data = etree.SubElement(key_info, f"{{{ds_namespace}}}X509Data")
    
    x509_certificate_elem = etree.SubElement(x509_data, f"{{{ds_namespace}}}X509Certificate")
    x509_certificate_elem.text = x509_certificate
    
    # ============================================================
    # 11. INSERE A ASSINATURA NO XML
    # ============================================================
    # A assinatura deve ser inserida após a tag <infNFe> mas antes de </NFe>
    nfe_element = root  # <NFe> é a raiz
    
    # Remove qualquer assinatura existente (se houver)
    for existing_sig in nfe_element.findall(f'.//{{{ds_namespace}}}Signature'):
        nfe_element.remove(existing_sig)
    
    # Insere a nova assinatura após <infNFe> e antes de <infNFeSupl> (se existir)
    infNFeSupl = nfe_element.find('.//nfe:infNFeSupl', namespace)
    
    if infNFeSupl is not None:
        # Insere antes de infNFeSupl
        index = list(nfe_element).index(infNFeSupl)
        nfe_element.insert(index, signature)
    else:
        # Adiciona no final
        nfe_element.append(signature)
    
    # ============================================================
    # 12. RETORNA O XML ASSINADO
    # ============================================================
    try:
        xml_assinado = etree.tostring(
            root,
            xml_declaration=True,
            encoding='utf-8',
            pretty_print=True
        )
        return xml_assinado
    except Exception as e:
        raise Exception(f"❌ Erro ao gerar XML final: {e}")


def validar_assinatura_xml(xml_assinado):
    """
    Valida se a assinatura digital do XML está correta
    
    Args:
        xml_assinado (bytes ou str): XML assinado
    
    Returns:
        tuple: (bool, str) - (sucesso, mensagem)
    """
    try:
        if isinstance(xml_assinado, str):
            xml_assinado = xml_assinado.encode('utf-8')
        
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(xml_assinado, parser)
        
        # Verifica se tem assinatura
        ds_namespace = "http://www.w3.org/2000/09/xmldsig#"
        signature = root.find(f'.//{{{ds_namespace}}}Signature')
        
        if signature is None:
            return False, "❌ Assinatura não encontrada no XML"
        
        # Verifica se tem SignatureValue
        signature_value = signature.find(f'.//{{{ds_namespace}}}SignatureValue')
        if signature_value is None or not signature_value.text:
            return False, "❌ SignatureValue não encontrado"
        
        # Verifica se tem DigestValue
        digest_value = signature.find(f'.//{{{ds_namespace}}}DigestValue')
        if digest_value is None or not digest_value.text:
            return False, "❌ DigestValue não encontrado"
        
        # Verifica se tem X509Certificate
        x509_cert = signature.find(f'.//{{{ds_namespace}}}X509Certificate')
        if x509_cert is None or not x509_cert.text:
            return False, "❌ Certificado X509 não encontrado"
        
        return True, "✅ Assinatura presente e estrutura válida"
        
    except Exception as e:
        return False, f"❌ Erro na validação: {e}"


# ============================================================
# EXEMPLO DE USO
# ============================================================
if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("TESTE DE ASSINATURA DIGITAL NFC-e")
    print("=" * 80)
    print()
    
    # Caminhos
    xml_path = "admin/nfe/output/nfce_1.xml"
    pfx_path = "admin/nfe/certs/JANSSEN APARELHOS AUDITIVOS LTDA56154376000105.pfx"
    pfx_password = "123456"
    output_path = "admin/nfe/output/nfce_1_assinado.xml"
    
    try:
        # 1. Lê o XML
        print(f"📄 Lendo XML: {xml_path}")
        with open(xml_path, 'rb') as f:
            xml_content = f.read()
        print("✅ XML lido com sucesso")
        print()
        
        # 2. Assina
        print(f"🔐 Assinando XML com certificado: {pfx_path}")
        xml_assinado = assinar_xml_nfce(xml_content, pfx_path, pfx_password)
        print("✅ XML assinado com sucesso")
        print()
        
        # 3. Valida
        print("🔍 Validando assinatura...")
        valido, mensagem = validar_assinatura_xml(xml_assinado)
        print(mensagem)
        print()
        
        # 4. Salva
        if valido:
            print(f"💾 Salvando XML assinado: {output_path}")
            with open(output_path, 'wb') as f:
                f.write(xml_assinado)
            print("✅ XML assinado salvo com sucesso!")
            print()
            print(f"📂 Arquivo disponível em: {output_path}")
        else:
            print("❌ Assinatura inválida. XML não foi salvo.")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
    print("=" * 80)