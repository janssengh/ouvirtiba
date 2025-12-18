import xml.etree.ElementTree as ET
from datetime import datetime

def gerar_xml_nfce(invoice, client, items, emitente, qrcode_url):
    """
    Gera o XML da NFC-e (modelo 65) versão 4.00
    """
    # --------------------------
    # Raiz e atributos principais
    # --------------------------
    nfe = ET.Element("NFe", xmlns="http://www.portalfiscal.inf.br/nfe")
    infNFe = ET.SubElement(
        nfe,
        "infNFe",
        attrib={
            "versao": "4.00",
            "Id": f"NFe{invoice.access_key}"
        }
    )

    # --------------------------
    # <ide> - Identificação
    # --------------------------
    ide = ET.SubElement(infNFe, "ide")
    ET.SubElement(ide, "cUF").text = "42"  # SC
    ET.SubElement(ide, "cNF").text = invoice.access_key[-8:]  # Código numérico da chave
    ET.SubElement(ide, "natOp").text = "VENDA DE MERCADORIA"
    ET.SubElement(ide, "mod").text = "65"
    ET.SubElement(ide, "serie").text = str(invoice.series or 1)
    ET.SubElement(ide, "nNF").text = str(invoice.number)
    ET.SubElement(ide, "dhEmi").text = invoice.issue_date.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    ET.SubElement(ide, "tpNF").text = "1"  # Saída
    ET.SubElement(ide, "idDest").text = "1"  # Operação interna
    ET.SubElement(ide, "cMunFG").text = "4209102"  # Joinville/SC
    ET.SubElement(ide, "tpImp").text = "4"  # DANFE NFC-e
    ET.SubElement(ide, "tpEmis").text = "1"
    ET.SubElement(ide, "cDV").text = invoice.access_key[-1]
    ET.SubElement(ide, "tpAmb").text = "2"  # 1=Produção, 2=Homologação
    ET.SubElement(ide, "finNFe").text = "1"  # NFe normal
    ET.SubElement(ide, "indFinal").text = "1"
    ET.SubElement(ide, "indPres").text = "1"  # Operação presencial
    ET.SubElement(ide, "procEmi").text = "0"  # Emissor do contribuinte
    ET.SubElement(ide, "verProc").text = "Ouvirtiba-Emissor-1.0"

    # --------------------------
    # <emit> - Emitente
    # --------------------------
    emit = ET.SubElement(infNFe, "emit")
    ET.SubElement(emit, "CNPJ").text = "56154376000105"
    ET.SubElement(emit, "xNome").text = "JANSSEN APARELHOS AUDITIVOS LTDA"
    enderEmit = ET.SubElement(emit, "enderEmit")
    ET.SubElement(enderEmit, "xLgr").text = "Rua Jerônimo Coelho"
    ET.SubElement(enderEmit, "nro").text = "78"
    ET.SubElement(enderEmit, "xBairro").text = "Centro"
    ET.SubElement(enderEmit, "cMun").text = "4209102"
    ET.SubElement(enderEmit, "xMun").text = "Joinville"
    ET.SubElement(enderEmit, "UF").text = "SC"
    ET.SubElement(enderEmit, "CEP").text = "89201050"
    ET.SubElement(enderEmit, "cPais").text = "1058"
    ET.SubElement(enderEmit, "xPais").text = "Brasil"
    ET.SubElement(emit, "IE").text = "255000376"
    ET.SubElement(emit, "CRT").text = "1"  # Simples Nacional

    # --------------------------
    # <dest> - Destinatário
    # --------------------------
    dest = ET.SubElement(infNFe, "dest")
    ET.SubElement(dest, "CPF").text = client.code if client.code else ""
    ET.SubElement(dest, "xNome").text = client.name or "CONSUMIDOR NÃO IDENTIFICADO"
    ET.SubElement(dest, "indIEDest").text = "9"  # Não contribuinte
    enderDest = ET.SubElement(dest, "enderDest")
    ET.SubElement(enderDest, "xLgr").text = client.address or ""
    ET.SubElement(enderDest, "xMun").text = "Joinville"
    ET.SubElement(enderDest, "UF").text = "SC"
    ET.SubElement(enderDest, "CEP").text = "89201050"
    ET.SubElement(enderDest, "cPais").text = "1058"
    ET.SubElement(enderDest, "xPais").text = "Brasil"

    # --------------------------
    # <det> - Itens
    # --------------------------
    for i, item in enumerate(items, start=1):
        det = ET.SubElement(infNFe, "det", nItem=str(i))
        prod = ET.SubElement(det, "prod")
        ET.SubElement(prod, "cProd").text = str(item.product_id)
        ET.SubElement(prod, "xProd").text = item.product.name
        ET.SubElement(prod, "NCM").text = item.ncm
        ET.SubElement(prod, "CFOP").text = "5102"
        ET.SubElement(prod, "uCom").text = "UN"
        ET.SubElement(prod, "qCom").text = f"{item.quantity:.2f}"
        ET.SubElement(prod, "vUnCom").text = f"{item.unit_price:.2f}"
        ET.SubElement(prod, "vProd").text = f"{item.total_price:.2f}"
        ET.SubElement(prod, "indTot").text = "1"
        imposto = ET.SubElement(det, "imposto")
        icms = ET.SubElement(imposto, "ICMS")
        icms40 = ET.SubElement(icms, "ICMSSN102")
        ET.SubElement(icms40, "orig").text = "0"
        ET.SubElement(icms40, "CSOSN").text = "102"

    # --------------------------
    # <total>
    # --------------------------
    total = ET.SubElement(infNFe, "total")
    ICMSTot = ET.SubElement(total, "ICMSTot")
    ET.SubElement(ICMSTot, "vBC").text = "0.00"
    ET.SubElement(ICMSTot, "vICMS").text = "0.00"
    ET.SubElement(ICMSTot, "vProd").text = f"{invoice.total_value:.2f}"
    ET.SubElement(ICMSTot, "vNF").text = f"{invoice.total_value:.2f}"

    # --------------------------
    # <pag> - Pagamento
    # --------------------------
    pag = ET.SubElement(infNFe, "pag")
    detPag = ET.SubElement(pag, "detPag")
    ET.SubElement(detPag, "tPag").text = "01"  # Dinheiro
    ET.SubElement(detPag, "vPag").text = f"{invoice.total_value:.2f}"

    # --------------------------
    # <infAdic>
    # --------------------------
    infAdic = ET.SubElement(infNFe, "infAdic")
    ET.SubElement(infAdic, "infCpl").text = "Emitido em ambiente de homologação - sem valor fiscal."

    # --------------------------
    # <infNFeSupl> - QR Code
    # --------------------------
    infNFeSupl = ET.SubElement(nfe, "infNFeSupl")
    ET.SubElement(infNFeSupl, "qrCode").text = f"<![CDATA[{qrcode_url}]]>"
    ET.SubElement(infNFeSupl, "urlChave").text = "https://sat.sef.sc.gov.br/nfce/consulta"

    # --------------------------
    # Converter para string formatada
    # --------------------------
    xml_string = ET.tostring(nfe, encoding="utf-8", xml_declaration=True)
    return xml_string
