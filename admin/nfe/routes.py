from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, current_app
from admin.nfe.models import db, Invoice, InvoiceItem
from admin.order.models import Customer_request, Customer_request_item # Importação já existe
from admin.client.models import Client
from admin.models import Product

from admin.nfe.nfce_xml import gerar_xml_nfce
from admin.nfe.nfce_sign import assinar_xml_nfce
from admin.nfe.nfce_transmit import transmitir_nfce
from admin.nfe.nfce_consulta_recibo import consultar_nfce_recibo

from datetime import datetime

from pathlib import Path
from lxml import etree
import os
from random import randint
from io import BytesIO
from fpdf import FPDF

# 🔄 Carrega variáveis do .env
from dotenv import load_dotenv
load_dotenv()

# Ambiente: 1 = Produção | 2 = Homologação (padrão seguro)
AMBIENTE = int(os.getenv("NFE_AMBIENTE", "2"))


nfe_bp = Blueprint('nfe_bp', __name__, template_folder='templates')

def gerar_chave_acesso(uf, cnpj, modelo, serie, numero_nfe, codigo_numerico):
    """
    Gera a chave de acesso NFC-e (modelo 65) conforme o padrão SEFAZ.
    """
    from datetime import datetime

    # Ano e mês no formato AAMM
    data = datetime.now().strftime("%y%m")

    # Monta os 43 primeiros dígitos (sem o DV)
    chave_sem_dv = f"{uf}{data}{cnpj:0>14}{modelo:0>2}{serie:0>3}{numero_nfe:0>9}{codigo_numerico:0>9}"

    # Calcula o dígito verificador (módulo 11)
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    for i, n in enumerate(reversed(chave_sem_dv)):
        soma += int(n) * pesos[i % 8]
    dv = 11 - (soma % 11)
    if dv >= 10:
        dv = 0

    return chave_sem_dv + str(dv)

def formatar_chave_acesso(chave):
    """
    Formata a chave de acesso NFC-e em blocos de 4 dígitos para exibição no DANFE.
    Exemplo: '42251012345678000123650010000000011000012345'
             -> '4225 1012 3456 7800 0123 6500 1000 0000 0110 0001 2345'
    """
    if not chave:
        return ""
    chave_str = str(chave).replace(" ", "").strip()
    return " ".join(chave_str[i:i+4] for i in range(0, len(chave_str), 4))



# Inserir o QR Code no XML da NFC-e
from xml.etree.ElementTree import Element, SubElement, tostring
from admin.nfe.nfce_qrcode import generate_qrcode_url



def append_qrcode_to_xml(nfe_xml: Element, access_key: str, ambiente: int, token_id: str, token_value: str):
    """Adiciona a tag <infNFeSupl> com QR Code e URL de consulta"""
    inf_supl = SubElement(nfe_xml, "infNFeSupl")

    qrcode_url = generate_qrcode_url(access_key, ambiente, token_id, token_value)
    qr_tag = SubElement(inf_supl, "qrCode")
    qr_tag.text = f"<![CDATA[{qrcode_url}]]>"

    url_tag = SubElement(inf_supl, "urlChave")
    url_tag.text = "https://sat.sef.sc.gov.br/nfce/consulta"

    return nfe_xml

# cria o gerador de cupom
import qrcode
from fpdf import FPDF

def generate_danfe_nfce(invoice_data, qrcode_url, output_file="danfe_nfce.pdf"):
    """Gera o cupom DANFE-NFC-e em PDF (formato simplificado)"""
    
    # Gerar imagem QR Code
    qr_img = qrcode.make(qrcode_url)
    qr_path = "qrcode_nfce.png" # Definir o nome do arquivo da imagem
    qr_img.save(qr_path)

    pdf = FPDF()
    # DICA: Para impressora térmica de 80mm, use: pdf.add_page(format=(80, 0)).
    # Caso contrário, mantenha o padrão e ajuste as células.
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # 1. FIX: Cabeçalho cortando.
    # Usar largura 0 (máxima disponível) e dividir em duas linhas
    pdf.set_font("Arial", "B", size=12) # Aumenta o tamanho da fonte para o título
    pdf.cell(0, 6, txt="DANFE - Documento Auxiliar da", ln=True, align="C")
    pdf.cell(0, 6, txt="Nota Fiscal do Consumidor Eletrônica", ln=True, align="C")
    pdf.set_font("Arial", size=10) # Volta ao tamanho normal
    
    pdf.cell(0, 6, txt=f"Emitente: {invoice_data['company_name']}", ln=True)
    pdf.cell(0, 6, txt=f"CNPJ: {invoice_data['cnpj']}", ln=True)
    pdf.cell(0, 6, txt=f"Endereço: {invoice_data['address']}", ln=True)
    pdf.cell(0, 5, txt="----------------------------------------------", ln=True, align="C")

    for item in invoice_data["items"]:
        # Usar largura 0 para garantir que o texto não corte
        pdf.cell(0, 5, txt=f"{item['name']} - R$ {item['total']:.2f}", ln=True)

    pdf.cell(0, 5, txt="----------------------------------------------", ln=True, align="C")
    pdf.cell(0, 6, txt=f"Valor total: R$ {invoice_data['total']:.2f}", ln=True)
    
    # Chave de Acesso: usando a função 'formatar_chave_acesso'
    pdf.cell(0, 6, txt=f"Chave de acesso:", ln=True)
    pdf.multi_cell(0, 4, txt=formatar_chave_acesso(invoice_data['access_key']), align="C") # Centraliza a chave formatada
    
    pdf.cell(0, 5, txt=f"Data de emissão: {invoice_data['issue_date']}", ln=True)
    pdf.cell(0, 3, txt="", ln=True) # Espaçamento

    # 2. FIX: Inserir e centralizar QR Code.
    qr_width = 40 # Largura do QR Code em mm
    page_width = pdf.w - 2 * pdf.l_margin
    qr_x = (page_width / 2) - (qr_width / 2) # Cálculo para centralizar
    
    pdf.image(qr_path, x=qr_x, y=pdf.get_y(), w=qr_width)
    
    # Ajusta o cursor para baixo após a imagem do QR Code
    pdf.set_y(pdf.get_y() + qr_width + 5) 
    
    pdf.cell(0, 5, txt="Consulte a autenticidade em:", ln=True, align="C")
    
    # 2. FIX: Imprimir a URL base de consulta em vez da URL completa do QR Code.
    base_consulta_url = "https://sat.sef.sc.gov.br/nfce/consulta"
    pdf.set_font("Arial", size=8) # Fonte menor para o link
    pdf.multi_cell(0, 3, txt=base_consulta_url, align="C")
    pdf.set_font("Arial", size=10) # Volta ao tamanho normal

    pdf.output(output_file)
    return output_file

def linha_tracejada(pdf, char="-", count=60):
    pdf.set_x(2)
    pdf.cell(76, 5, txt=char * count, ln=True, align="C")



# 📜 Lista
@nfe_bp.route('/admin/nfe/list')
def nfe_list():
    invoices = Invoice.query.order_by(Invoice.issue_date.desc()).all()
    return render_template('admin/nfe/nfe_list.html', notas=invoices, titulo="Notas Fiscais Emitidas")

# ➕ Criar nova nota
@nfe_bp.route('/admin/nfe/new', methods=['GET', 'POST'])
def nfe_create():
    #clients = Client.query.order_by(Client.name).all()
    orders = Customer_request.query.order_by(Customer_request.id.desc()).all()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        # Garante que order_id seja None se vier vazio do formulário
        order_id = request.form.get('order_id') or None 
        total_value = float(request.form.get('total_value', 0))

        # -------------------------
        # 🔹 Geração da chave de acesso dinâmica
        # -------------------------
        store_data = session.get('Store', {})
        uf_map = {
            'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
            'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
            'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
            'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
            'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
            'SE': '28', 'TO': '17'
        }

        region = store_data.get('Region', 'SC')
        uf_code = uf_map.get(region.upper(), '42')  # padrão SC

        # ⚠️ Certifique-se que o campo correto com CNPJ existe
        cnpj_loja = store_data.get('Code', '00000000000000')  # substitua por stores.cnpj se existir
        cnpj_numerico = ''.join(filter(str.isdigit, cnpj_loja))[:14].ljust(14, '0')

        number = datetime.now().strftime('%Y%m%d%H%M%S')
        codigo_numerico = randint(100000000, 999999999)

        chave = gerar_chave_acesso(
            uf=uf_code,
            cnpj=cnpj_numerico,
            modelo='65',
            serie='1',
            numero_nfe=number[-9:],
            codigo_numerico=codigo_numerico
        )

        new_invoice = Invoice(
            number=datetime.now().strftime('%Y%m%d%H%M%S'),
            store_id=session['Store']['Id'],
            client_id=client_id,
            # Se order_id for None, o campo order_id no banco aceitará NULL
            order_id=order_id, 
            total_value=total_value,
            status='N',
            access_key=chave
        )

        try:
            db.session.add(new_invoice)
            # Flush forçará a geração do new_invoice.id no banco de dados,
            # sem finalizar a transação, permitindo o uso do ID abaixo.
            db.session.flush() 

            # ------------------------------------------------------------------
            # LÓGICA PARA GERAR OS ITENS DA NOTA FISCAL (InvoiceItem)
            # ------------------------------------------------------------------
            if order_id:
                # Busca os itens do pedido com o ID fornecido
                order_items = Customer_request_item.query.filter(
                    Customer_request_item.customer_request_id == order_id,
                    Customer_request_item.price > 0 # <--- NOVO FILTRO AQUI
                ).all()

                #order_items = Customer_request_item.query.filter_by(customer_request_id=order_id).all()

                invoice_items = []
                for item in order_items:
                    # Cria um novo InvoiceItem para cada Customer_request_item
                    invoice_item = InvoiceItem(
                        invoice_id=new_invoice.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        # Mapeamento dos campos. unit_price e total_price esperam Float/Numeric
                        unit_price=float(item.price), 
                        total_price=float(item.amount), # Usa o valor final do item (já com desconto, se houver),
                        ncm="90214000",
                        cfop="5702",
                        csosn="102"
                    )
                    invoice_items.append(invoice_item)

                # Adiciona todos os novos itens à sessão de uma só vez (bulk add)
                db.session.add_all(invoice_items)
            
            # Confirma a transação (criação da Nota e de todos os Itens)
            db.session.commit() 
            flash(f"✅ Nota Fiscal {new_invoice.number} criada com sucesso!", "success")
            return redirect(url_for('nfe_bp.nfe_list'))

        except Exception as e:
            # Em caso de qualquer erro (criação da Nota ou dos Itens), 
            # a transação inteira é desfeita.
            db.session.rollback() 
            print(f"Erro ao criar NFE: {e}") # Loga o erro
            flash(f"❌ Erro ao criar Nota Fiscal. Detalhes: {e}", "danger")
            return redirect(url_for('nfe_bp.nfe_create'))

    return render_template('admin/nfe/nfe_create.html', orders=orders, titulo="Emitir Nova Nota Fiscal")

@nfe_bp.route('/admin/nfe/<int:id>/detail')
def nfe_detail(id):
    invoice = db.session.execute(
        db.select(Invoice).filter_by(id=id)
    ).scalar_one_or_none()

    if invoice is None:
        flash(f"Nota Fiscal com ID {id} não encontrada.", "danger")
        return redirect(url_for('nfe_bp.nfe_list'))
    
    items = db.session.execute(
        db.select(InvoiceItem).filter_by(invoice_id=id).options(db.joinedload(InvoiceItem.product))
    ).scalars().all()

    # ---- formata a chave de acesso (e protege se for None) ----
    chave_formatada = formatar_chave_acesso(invoice.access_key) if getattr(invoice, 'access_key', None) else ""
    # anexar ao objeto invoice para uso direto no template como nota.access_key_formatted
    setattr(invoice, 'access_key_formatted', chave_formatada)

    # debug log quando não houver chave (apenas para ajudar no diagnóstico)
    if not chave_formatada:
        print(f"⚠️ Nota {invoice.id} ({invoice.number}) sem access_key. Verifique geração/armazenamento.")

    return render_template(
        'admin/nfe/nfe_detail.html',
        nota=invoice,
        itens=items,
        titulo=f"Detalhes da Nota Fiscal #{invoice.number}"
    )

@nfe_bp.route('/invoice/<int:invoice_id>/pdf', methods=['GET'])
def generate_invoice_pdf(invoice_id):
    """Gera DANFE NFC-e (modelo 65) com alinhamento e QR Code corrigidos"""

    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        flash("Nota fiscal não encontrada.", "danger")
        return redirect(url_for('order_bp.order_list'))

    client = Client.query.get(invoice.client_id)
    items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()

    # Gerar URL e imagem do QR Code
    token_id = '000001'
    token_value = 'TESTE1234567890'
    ambiente = 2  # 1 = produção, 2 = homologação
    qrcode_url = generate_qrcode_url(invoice.access_key, ambiente, token_id, token_value)

    #qr_img = qrcode.make(qrcode_url)
    #qr_path = f"temp_qrcode_{invoice_id}.png"
    #qr_img.save(qr_path)

    # 🧾 Cria o PDF térmico (80mm de largura)
    pdf = FPDF(unit="mm", format=(80, 260))
    pdf.set_auto_page_break(auto=True, margin=4)
    pdf.set_margins(left=2, top=5, right=2)
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)

    # 🧾 Cabeçalho
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(76, 5, txt="DANFE NFC-e\nDocumento Auxiliar da Nota Fiscal do Consumidor Eletrônica", align="C")
    pdf.cell(76, 3, txt="-" * 40, ln=True, align="C")

    # CNPJ: XX.XXX.XXX/YYYY-ZZ
    cnpj_emitente = f"{session['Store']['Code'][:2]}.{session['Store']['Code'][2:5]}.{session['Store']['Code'][5:8]}/{session['Store']['Code'][8:12]}-{session['Store']['Code'][12:]}"
    cep_formatado = f"{session['Store']['Cep origem'][:5]}-{session['Store']['Cep origem'][5:]}"

    endereco_emitente_1 = f"{session['Store']['Address']}, {session['Store']['Number']} - {session['Store']['Neighborhood']}"  
    endereco_emitente_2 = f"{session['Store']['City']}/{session['Store']['Region']} {cep_formatado}"

    pdf.set_font("Helvetica", size=8)
    pdf.cell(76, 5, txt="Emitente: JANSSEN APARELHOS AUDITIVOS LTDA", ln=True)
    pdf.cell(76, 5, txt=f"CNPJ: {cnpj_emitente}", ln=True)
    pdf.multi_cell(
        76,
        4,
        txt=f"Endereço: {endereco_emitente_1}\n{endereco_emitente_2}",
        align="L"
    )
    pdf.set_x(2)  # garante início na margem esquerda
    pdf.multi_cell(
        76,                # largura útil da página (80mm - margens)
        4,                 # altura da linha
        txt=f"NFC-e nº {invoice.number}",
        align="L"
    )
    # linha tracejada
    linha_tracejada(pdf, char="=", count=46)
    #pdf.cell(76, 3, txt="-" * 40, ln=True, align="C")

    # 🧩 Itens
    for item in items:
        product = Product.query.get(item.product_id)
        total_price_formatado = f"{item.total_price:.2f}".replace('.', ',')
        pdf.multi_cell(76, 4, txt=f"{product.name}\nR$ {total_price_formatado}", align="L")
    pdf.cell(76, 3, txt="-" * 40, ln=True, align="C")

    # Totais
    valor_total_formatado = f"{invoice.total_value:.2f}".replace('.', ',')
    pdf.cell(76, 5, txt=f"Valor total: R$ {valor_total_formatado}", ln=True)
    pdf.cell(76, 5, txt="Chave de acesso:", ln=True)
    pdf.multi_cell(76, 4, txt=invoice.access_key, align="C")

    # 🔧 Garante que próxima linha comece na margem esquerda
    pdf.set_x(2)
    pdf.cell(76, 5, txt=f"Emitido em: {invoice.issue_date.strftime('%d/%m/%Y %H:%M')}", ln=True)

    # 📱 QR Code de alta resolução e centralizado
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        box_size=8,  # maior resolução (pixels por quadrado)
        border=2
    )
    qr.add_data(qrcode_url)
    qr.make(fit=True)
    #qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_path = f"temp_qrcode_{invoice_id}.png"
    qr_img.save(qr_path)

    qr_width = 36
    usable_width = 80 - 2 * 2  # 80mm - 4mm margens
    qr_x = 2 + (usable_width - qr_width) / 2
    pdf.image(qr_path, x=qr_x, y=pdf.get_y() + 4, w=qr_width)
    pdf.ln(qr_width + 10)

    # 🔗 URL de consulta
    pdf.set_font("Helvetica", size=7)
    pdf.set_x(2)
    pdf.multi_cell(76, 4, txt="Consulte a autenticidade em:", align="C")

    pdf.set_x(2)
    url_consulta = "https://sat.sef.sc.gov.br/nfce/consulta"
    pdf.multi_cell(76, 4, txt=url_consulta, align="C")

    # 🔄 Gera PDF em memória
    pdf_bytes = pdf.output(dest="S")
    pdf_buffer = BytesIO(pdf_bytes)

    return send_file(
        pdf_buffer,
        as_attachment=False,
        download_name=f"NFCe_{invoice.number}.pdf",
        mimetype="application/pdf"
    )

# --------------------------------------
# 🔶 GERA XML BASE E SALVA EM static/xml/
# --------------------------------------
@nfe_bp.route('/generate_xml_base/<int:id>', methods=['GET'])
def generate_xml_base(id):
    invoice = Invoice.query.get_or_404(id)
    client = Client.query.get(invoice.client_id)
    items = InvoiceItem.query.filter_by(invoice_id=id).all()

    # URL de consulta fictícia (substituir quando for real)
    qrcode_url = "https://sat.sef.sc.gov.br/nfce/consulta?p=TESTE"
    emitente = {
        "cnpj": "56154376000105",
        "razao": "JANSSEN APARELHOS AUDITIVOS LTDA"
    }

    # Gera o XML
    xml_bytes = gerar_xml_nfce(invoice, client, items, emitente, qrcode_url)

    # Caminho absoluto da pasta static/xml
    base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    xml_folder = base_dir / "static" / "xml"
    xml_folder.mkdir(parents=True, exist_ok=True)

    xml_path = xml_folder / f"NFCe_{invoice.access_key}_base.xml"

    # Salva o arquivo XML
    with open(xml_path, "wb") as f:
        f.write(xml_bytes)

    flash(f"XML base salvo em {xml_path}", "success")

    return send_file(
        xml_path,
        mimetype="application/xml",
        as_attachment=True,
        download_name=f"NFCe_{invoice.access_key}_base.xml"
    )


# --------------------------------------
# 🟢 GERA XML ASSINADO E SALVA EM static/xml/
# --------------------------------------
@nfe_bp.route('/generate_xml_signed/<int:id>', methods=['GET'])
def generate_xml_signed(id):
    invoice = Invoice.query.get_or_404(id)
    client = Client.query.get(invoice.client_id)
    items = InvoiceItem.query.filter_by(invoice_id=id).all()

    qrcode_url = "https://hom.sat.sef.sc.gov.br/nfce/consulta?p=" if AMBIENTE == 2 else "https://sat.sef.sc.gov.br/nfce/consulta?p="
    emitente = {
        "cnpj": "56154376000105",
        "razao": "JANSSEN APARELHOS AUDITIVOS LTDA"
    }

    # 1) XML base
    xml_bytes = gerar_xml_nfce(invoice, client, items, emitente, qrcode_url)

    # 2) Certificado A1 (.pfx)
    base_dir = Path(current_app.root_path)
    certs_folder = base_dir / "admin" / "nfe" / "certs"
    pfx_path = certs_folder / "JANSSEN APARELHOS AUDITIVOS LTDA56154376000105.pfx"

    # 3) Assina XML
    xml_assinado = assinar_xml_nfce(
        xml_bytes,
        pfx_path=str(pfx_path),
        pfx_password="123456"
    )

    # 4) Salva XML assinado
    xml_folder = base_dir / "static" / "xml"
    xml_folder.mkdir(parents=True, exist_ok=True)
    # Usa a chave de acesso se existir, senão fallback no número
    nome_arquivo = f"NFCe_{(invoice.access_key or invoice.number)}_assinado.xml"
    xml_path_abs = xml_folder / nome_arquivo

    with open(xml_path_abs, "wb") as f:
        f.write(xml_assinado)

    # Salva caminho RELATIVO no banco (portável)
    try:
        rel = xml_path_abs.relative_to(base_dir)
    except ValueError:
        rel = xml_path_abs  # fallback, mas em geral não ocorre

    invoice.xml_path = str(rel).replace("\\", "/")
    invoice.status = "assinado"
    db.session.commit()

    flash(f"✅ XML assinado salvo em {invoice.xml_path}", "success")

    return send_file(
        xml_path_abs,
        mimetype="application/xml",
        as_attachment=True,
        download_name=nome_arquivo
    )

# ================================================================
# 🛰️ TRANSMISSÃO DA NFC-e (HOMOLOGAÇÃO SC - SVRS)
# ================================================================
@nfe_bp.route("/transmit_nfe/<int:id>", methods=["GET"])
def transmit_nfe(id):
    invoice = Invoice.query.get_or_404(id)

    # Caminho do certificado .pfx
    base_dir = Path(current_app.root_path)
    certificado_path = base_dir / "admin" / "nfe" / "certs" / "JANSSEN APARELHOS AUDITIVOS LTDA56154376000105.pfx"
    senha_certificado = "123456"

    if not certificado_path.exists():
        return render_template(
            "admin/nfe/nfe_response.html",
            success=False,
            message=f"❌ Certificado não encontrado em: {certificado_path}",
            response_text=None,
            titulo="Erro na Transmissão"
        )

    # Lê o XML assinado do caminho salvo no banco
    if not invoice.xml_path:
        return render_template(
            "admin/nfe/nfe_response.html",
            success=False,
            message="❌ Nenhum XML assinado registrado na nota. Gere o XML assinado antes de transmitir.",
            response_text=None,
            titulo="Erro na Transmissão"
        )

    xml_signed_path = base_dir / invoice.xml_path
    if not xml_signed_path.exists():
        return render_template(
            "admin/nfe/nfe_response.html",
            success=False,
            message=f"❌ Arquivo XML assinado não encontrado em: {xml_signed_path}",
            response_text=None,
            titulo="Erro na Transmissão"
        )

    with open(xml_signed_path, "r", encoding="utf-8") as f:
        xml_assinado = f.read()

    # Envia conforme AMBIENTE (2=homologação, 1=produção)
    success, message, response_text = transmitir_nfce(
        xml_assinado=xml_assinado,
        certificado_pfx=str(certificado_path),
        senha_certificado=senha_certificado,
        ambiente=AMBIENTE
    )

    # Atualiza nRec e status (se retorno cStat=103)
    if success and response_text:
        try:
            NS = "{http://www.portalfiscal.inf.br/nfe}"
            root = etree.fromstring(response_text.encode("utf-8"))
            nRec_el = root.find(f".//{NS}nRec")
            if nRec_el is not None and nRec_el.text:
                invoice.nrec = nRec_el.text.strip()
                invoice.status = "Transmitida" if AMBIENTE == 2 else "Transmitida-Prod"
                db.session.commit()
                flash(f"✅ NFC-e enviada. Recibo: {invoice.nrec}", "success")
            else:
                flash("⚠️ Lote recebido, mas número de recibo não veio no retorno.", "warning")
        except Exception as e:
            db.session.rollback()
            flash(f"⚠️ Erro ao extrair recibo: {e}", "warning")

    return render_template(
        "admin/nfe/nfe_response.html",
        success=success,
        message=message,
        response_text=response_text,
        titulo=f"Transmissão da NFC-e ({'Homologação' if AMBIENTE==2 else 'Produção'})"
    )

### CONSULTAR RECIBO
@nfe_bp.route("/consultar_recibo/<int:id>")
def consultar_recibo(id):
    from admin.nfe.nfce_consulta_recibo import consultar_nfce_recibo

    invoice = Invoice.query.get_or_404(id)
    certificado_path = "certificados/JANSSEN_APARELHOS_AUDITIVOS_LTDA56154376000105.pfx"
    senha_certificado = "123456"

    nRec = invoice.nrec or "123456789012345"  # se ainda não armazenado
    success, message, response_text = consultar_nfce_recibo(nRec, certificado_path, senha_certificado)

    # Atualiza status da nota se autorizado (simulado)
    if success and "Autorizado" in (response_text or ""):
        invoice.status = "Aprovada"
        db.session.commit()

    return render_template(
        "admin/nfe/nfe_response.html",
        success=success,
        message=message,
        response_text=response_text,
        titulo="Consulta de Recibo NFC-e"
    )
