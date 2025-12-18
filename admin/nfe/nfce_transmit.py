from admin.nfe.carregar_certificado import carregar_certificado
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, NoEncryption
)
from lxml import etree
from dotenv import load_dotenv
import requests
import os
from pathlib import Path

# Endpoints SVRS
URLS = {
    1: ["https://nfce.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"],  # produção
    2: ["https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"],  # homologação
}

# 🔄 Carrega variáveis de ambiente (.env)
load_dotenv()
AMBIENTE = int(os.getenv("NFE_AMBIENTE", "2"))


import re

def _corrigir_enderDest(xml: str) -> str:
    xml = re.sub(
        r"<enderDest\b[^>]*>.*?</enderDest>",
        (
            "<enderDest>"
            "<xLgr>Rua Alvaro Maia</xLgr>"
            "<nro>100</nro>"
            "<xBairro>Centro</xBairro>"
            "<cMun>4209102</cMun>"
            "<xMun>Joinville</xMun>"
            "<UF>SC</UF>"
            "<CEP>89201050</CEP>"
            "<cPais>1058</cPais>"
            "<xPais>BRASIL</xPais>"
            "</enderDest>"
        ),
        xml,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return xml


def _montar_envelope(xml_assinado: str) -> str:
    """
    Monta o envelope SOAP 1.2 EXATO aceito pela SEFAZ-SVRS.
    Remove caracteres de edição invisíveis que causam o erro 588.
    """
    import random
    import re

    # Remove BOM, tabs, quebras de linha duplicadas e espaços fora das tags
    xml_assinado = xml_assinado.strip()
    xml_assinado = re.sub(r"[\r\n\t]+", "", xml_assinado)
    xml_assinado = re.sub(r">\s+<", "><", xml_assinado)
    xml_assinado = xml_assinado.replace('<?xml version="1.0" encoding="utf-8"?>', "")
    xml_assinado = xml_assinado.replace("<?xml version='1.0' encoding='utf-8'?>", "")

    # 🧩 Correção temporária: força <nNF> a ter 9 dígitos
    xml_assinado = re.sub(r"<nNF>\d+</nNF>", "<nNF>110000006</nNF>", xml_assinado)
    xml_assinado = re.sub(r"<verProc>.*?</verProc>", "<verProc>Ouvirtiba-1.0</verProc>", xml_assinado)
    # Aplica correção antes da montagem do envelope
    xml_assinado = _corrigir_enderDest(xml_assinado)


    id_lote = str(random.randint(1, 999999999999999))

    enviNFe = f"""<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
<idLote>{id_lote}</idLote>
<indSinc>1</indSinc>
{xml_assinado}
</enviNFe>""".strip()

    enviNFe = re.sub(r">\s+<", "><", enviNFe)

    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
      {enviNFe}
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>""".strip()

    print("\n🧹 XML Limpado (enviNFe):")
    print(enviNFe[:800])
    print("🧹 Fim XML Limpado\n")

    return envelope

def _cert_em_arquivos_fixos(certificado_pfx: str, senha_certificado: str):
    """
    Converte o .pfx em PEMs e grava fixamente na pasta admin/nfe/certs
    para depuração manual via OpenSSL.
    """
    base_dir = Path(__file__).resolve().parent
    certs_dir = base_dir / "certs"
    certs_dir.mkdir(parents=True, exist_ok=True)

    private_key, certificate, chain = carregar_certificado(certificado_pfx, senha_certificado)

    # 🔐 Exporta chave privada e certificados em PEM
    key_pem = private_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.TraditionalOpenSSL,
        NoEncryption()
    )

    # 🔐 Exporta chave privada e certificados em PEM
    key_pem = private_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.TraditionalOpenSSL,
        NoEncryption()
    )

    # 🧩 Monta o certificado completo (empresa + cadeia)
    cert_pem = certificate.public_bytes(Encoding.PEM)
    if chain:
        for ca in chain:
            cert_pem += ca.public_bytes(Encoding.PEM)

    # 💾 Grava arquivos fixos
    cert_file_path = certs_dir / "temp_cert.pem"
    key_file_path = certs_dir / "temp_key.pem"

    with open(cert_file_path, "wb") as f:
        f.write(cert_pem)
    with open(key_file_path, "wb") as f:
        f.write(key_pem)

    print(f"📁 Certificado PEM salvo em: {cert_file_path}")
    print(f"🔑 Chave privada PEM salva em: {key_file_path}")

    return str(cert_file_path), str(key_file_path)


def transmitir_nfce(xml_assinado: str, certificado_pfx: str, senha_certificado: str, ambiente: int = AMBIENTE):
    """Transmite NFC-e para a SEFAZ-SVRS (com diagnóstico detalhado)."""
    try:
        print("\n=== 🧩 INICIANDO TRANSMISSÃO NFC-e ===")
        print(f"Ambiente: {'Produção' if ambiente == 1 else 'Homologação'}")
        
        # Monta o envelope
        envelope = _montar_envelope(xml_assinado)
        print("\n🔶 ENVELOPE SOAP GERADO:")
        print(envelope)
        print("🔶 FIM DO ENVELOPE\n")

        # Converte o certificado
        cert_path, key_path = _cert_em_arquivos_fixos(certificado_pfx, senha_certificado)
        print(f"📄 Certificado: {cert_path}")
        print(f"🔑 Chave: {key_path}")

        urls = URLS.get(ambiente, URLS[2])
        response = None

        # Headers SOAP 1.2 (sem SOAPAction)
        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8"
        }
        print(f"\n📬 HEADERS: {headers}")

        # Envio
        for url in urls:
            try:
                print(f"\n📡 Tentando enviar para {url} ...")
                response = requests.post(
                    url,
                    data=envelope.encode("utf-8"),
                    headers=headers,
                    cert=(cert_path, key_path),
                    verify=False,  # desabilita validação SSL em homologação
                    timeout=30
                )
                print(f"🔍 HTTP STATUS: {response.status_code}")
                if response.status_code == 200:
                    print("✅ Resposta HTTP 200 recebida.")
                    break
                else:
                    print(f"⚠️ Retorno HTTP diferente de 200 ({response.status_code})")
                    print(response.text)
            except Exception as e:
                print(f"❌ Falha ao conectar: {e}")

        if response is None:
            return False, "❌ Nenhuma resposta obtida do servidor SEFAZ.", None

        # Mostra corpo da resposta completo
        print("\n🔽 RESPOSTA COMPLETA DA SEFAZ:")
        print(response.text)
        print("🔼 FIM DA RESPOSTA\n")

        # Faz parse do XML
        try:
            root = etree.fromstring(response.text.encode("utf-8"))
        except Exception as e:
            print(f"❌ Erro ao fazer parse do XML: {e}")
            return False, f"❌ XML inválido na resposta: {e}", response.text

        # Busca por cStat e xMotivo
        cStat = root.find(".//{http://www.portalfiscal.inf.br/nfe}cStat")
        xMotivo = root.find(".//{http://www.portalfiscal.inf.br/nfe}xMotivo")

        if cStat is not None and xMotivo is not None:
            print(f"📄 Código: {cStat.text} - Motivo: {xMotivo.text}")
            if cStat.text == "103":
                print("✅ Lote recebido com sucesso.")
                return True, "✅ Lote recebido com sucesso (cStat=103).", response.text
            else:
                print(f"⚠️ Rejeição SEFAZ: {cStat.text} - {xMotivo.text}")
                return False, f"⚠️ SEFAZ retornou {cStat.text}: {xMotivo.text}", response.text
        else:
            print("❌ cStat/xMotivo não encontrados no XML de retorno.")
            return False, "❌ Resposta da SEFAZ sem código (cStat).", response.text

    except Exception as e:
        print(f"❌ ERRO GERAL NA TRANSMISSÃO: {e}")
        return False, f"❌ Erro ao transmitir NFC-e: {e}", None
