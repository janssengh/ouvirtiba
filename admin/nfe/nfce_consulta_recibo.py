import requests
from lxml import etree
from admin.nfe.carregar_certificado import carregar_certificado
import tempfile
import os

def consultar_nfce_recibo(nRec, certificado_path, senha_certificado):
    """
    Consulta o recibo de uma NFC-e transmitida ao ambiente de homologação SVRS (SC).
    Se o servidor estiver fora do ar ou inacessível, retorna um XML de simulação.
    """
    try:
        # =========================
        # 1️⃣ Montagem do XML
        # =========================
        nsmap = {"": "http://www.portalfiscal.inf.br/nfe"}
        root = etree.Element("consReciNFe", nsmap=nsmap, versao="4.00")

        tpAmb = etree.SubElement(root, "tpAmb")
        tpAmb.text = "2"  # 2 = Homologação

        etree.SubElement(root, "nRec").text = str(nRec)

        xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True)

        # =========================
        # 2️⃣ Carregar certificado
        # =========================
        cert_pem, key_pem = carregar_certificado(certificado_path, senha_certificado)

        # Criar arquivos temporários para requests
        cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        key_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")

        cert_file.write(cert_pem if isinstance(cert_pem, bytes) else cert_pem.encode("utf-8"))
        key_file.write(key_pem if isinstance(key_pem, bytes) else key_pem.encode("utf-8"))

        cert_file.close()
        key_file.close()

        # =========================
        # 3️⃣ Envio SOAP para SVRS
        # =========================
        url = "https://hom.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx"
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

        soap_envelope = f"""
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                         xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
          <soap12:Body>
            <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRetAutorizacao4">
              {xml_bytes.decode("utf-8")}
            </nfeDadosMsg>
          </soap12:Body>
        </soap12:Envelope>
        """

        response = requests.post(
            url,
            data=soap_envelope.encode("utf-8"),
            headers=headers,
            cert=(cert_file.name, key_file.name),
            timeout=15
        )

        os.unlink(cert_file.name)
        os.unlink(key_file.name)

        # =========================
        # 4️⃣ Interpretação da resposta
        # =========================
        if response.status_code == 200:
            return True, "Consulta realizada com sucesso (homologação).", response.text
        else:
            return False, f"Erro HTTP {response.status_code}", response.text

    except requests.exceptions.RequestException as e:
        # =========================
        # 🔄 Fallback: modo simulado
        # =========================
        xml_mock = f"""
        <retConsReciNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
            <tpAmb>2</tpAmb>
            <verAplic>1.0</verAplic>
            <cStat>104</cStat>
            <xMotivo>Simulação local: Lote processado com sucesso</xMotivo>
            <cUF>42</cUF>
            <dhRecbto>2025-10-27T15:45:00-03:00</dhRecbto>
            <protNFe versao="4.00">
                <infProt>
                    <tpAmb>2</tpAmb>
                    <verAplic>1.0</verAplic>
                    <chNFe>42251056154376000105650010261100064641625050</chNFe>
                    <dhRecbto>2025-10-27T15:45:00-03:00</dhRecbto>
                    <nProt>123456789012345</nProt>
                    <digVal>abc123xyz==</digVal>
                    <cStat>100</cStat>
                    <xMotivo>Autorizado o uso da NF-e (simulado)</xMotivo>
                </infProt>
            </protNFe>
        </retConsReciNFe>
        """
        return True, "⚙️ Ambiente SVRS fora do ar — resposta simulada gerada localmente.", xml_mock

    except Exception as e:
        return False, f"Erro ao consultar recibo: {str(e)}", None
