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

# Geração XML NFCe
from decimal import Decimal
NAMESPACE = "http://www.portalfiscal.inf.br/nfe"
from config import TP_AMB

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
    orders = Customer_request.query.filter_by(is_invoiced='N').order_by(Customer_request.id.desc()).all()    

    # Criando o dicionário: { id_do_pedido: valor_do_desconto }
    discounts_dict = {order.id: float(order.discount or 0) for order in orders}

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        # Garante que order_id seja None se vier vazio do formulário
        order_id = request.form.get('order_id') or None 
        total_value = float(request.form.get('total_value', 0))

        # 2. Converte para Inteiro para bater com a chave do dicionário
        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            order_id = None

        # 3. Busca o desconto usando o ID convertido
        # O .get(order_id, 0) evita o erro KeyError se o ID não existir
        discount = discounts_dict.get(order_id, 0.0)

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
            access_key=chave,
            discount=discount
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
                        discount=item.discount,
                        serialnumber=item.serialnumber,
                        # Mapeamento dos campos. unit_price e total_price esperam Float/Numeric
                        unit_price=float(item.price), 
                        total_price=float(item.amount), # Usa o valor final do item (já com desconto, se houver),
                        ncm="90214000",
                        cfop="5102",
                        csosn="102"
                    )
                    invoice_items.append(invoice_item)

                # Adiciona todos os novos itens à sessão de uma só vez (bulk add)
                db.session.add_all(invoice_items)
            
            # Localize o pedido original
            order = Customer_request.query.get(order_id)
            if order:
                order.is_invoiced = 'S' # Marca como Nota Gerada

                # Confirma a transação (criação da Nota e de todos os Itens)
                db.session.commit()
                flash(f"✅ Nota Fiscal {new_invoice.number} criada com sucesso!", "success")
                return redirect(url_for('nfe_bp.nfe_list'))
            else:
                db.session.rollback() 
                print(f"Erro ao criar NFE: {e}") # Loga o erro
                flash(f"❌ Erro ao criar Nota Fiscal. Detalhes: {e}", "danger")
                return redirect(url_for('nfe_bp.nfe_create'))   


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

@nfe_bp.route('/invoice_a4/<int:invoice_id>/pdf', methods=['GET'])
def generate_invoice_a4_pdf(invoice_id):
    # 1. DEFINIÇÃO DAS VARIÁVEIS NO INÍCIO (Resolve o UnboundLocalError)
    invoice = Invoice.query.get_or_404(invoice_id)
    client = Client.query.get(invoice.client_id)
    items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
    store = session.get('Store', {}) # Agora 'store' está disponível para o canhoto

    # Configuração do PDF
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # --- 0. CANHOTO (Topo da Nota) ---
    pdf.rect(10, 10, 155, 15) # Quadro texto/assinatura
    pdf.rect(165, 10, 35, 15) # Quadro NF-e / Série
    
    pdf.set_font("Helvetica", size=6)
    pdf.set_xy(11, 11)
    # Referência ao item [cite: 1] do PDF enviado
    nome_loja = store.get('Name', 'JANSSEN APARELHOS AUDITIVOS LTDA').upper()
    pdf.multi_cell(150, 3, txt=f"RECEBEMOS DE {nome_loja} OS PRODUTOS E SERVIÇOS CONSTANTES NA NOTA FISCAL INDICADA AO LADO")
    
    pdf.set_xy(11, 19)
    pdf.cell(35, 5, txt="DATA DE RECEBIMENTO", border="T")
    pdf.set_xy(48, 19)
    pdf.cell(115, 5, txt="IDENTIFICAÇÃO E ASSINATURA DO RECEBEDOR", border="T")
    
    pdf.set_xy(165, 11)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(35, 4, txt="NF-e", ln=1, align="C")
    pdf.set_x(165)
    pdf.cell(35, 4, txt=f"Nº {invoice.number}", ln=1, align="C")
    pdf.set_x(165)
    pdf.cell(35, 4, txt=f"Série {getattr(invoice, 'series', '1')}", align="C")

    # --- LINHA DE SERRILHA (PONTILHADA) ---
    pdf.set_draw_color(100, 100, 100) # Cinza
    # Ajustado para os nomes de argumentos aceitos pela biblioteca fpdf2
    pdf.dashed_line(10, 27, 200, 27, dash_length=1, space_length=1)
    pdf.set_draw_color(0, 0, 0) # Volta para preto
    
    # --- 1. CABEÇALHO (IDENTIFICAÇÃO DO EMITENTE) ---
    pdf.ln(10)
    y_emitente = pdf.get_y()
    
    # --- BLOCO 1: QUADRADO EM BRANCO (LOGOTIPO) ---
    # Posicionado na extrema esquerda (x=10), tamanho 28x30mm
    pdf.rect(10, y_emitente, 28, 30) 
    # Linha interna leve próximo ao contorno (margem de 1mm)
    pdf.set_draw_color(200, 200, 200) # Cinza claro
    pdf.rect(11, y_emitente + 1, 26, 28)
    pdf.set_draw_color(0, 0, 0) # Volta para preto

    # --- BLOCO 2: IDENTIFICAÇÃO DO EMITENTE (AJUSTE DE DISTRIBUIÇÃO) ---
    pdf.rect(38, y_emitente, 62, 30)
    pdf.set_xy(39, y_emitente + 3) # Começa um pouco mais abaixo
    pdf.set_font("Helvetica", "B", 9) # Nome da loja levemente maior
    pdf.multi_cell(60, 4, txt=nome_loja, align="C")
    
    # Aumento da fonte do endereço e espaçamento (line_height de 3.5 em vez de 3)
    pdf.set_font("Helvetica", size=7.5) 
    pdf.set_x(39)
    address_info = f"{store.get('Address')}, {store.get('Number')}\n{store.get('Neighborhood')} - {store.get('Cep origem')}\n{store.get('City')} - {store.get('Region')}\nFone: {store.get('Phone')}"
    pdf.multi_cell(60, 4, txt=address_info, align="C")

    # --- BLOCO 3: DANFE (CENTRALIZADO EM RELAÇÃO AO RESTANTE) ---
    # Mantém a largura de 30mm, começando em x=100
    pdf.rect(100, y_emitente, 30, 30)
    pdf.set_xy(100, y_emitente + 1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(30, 4, txt="DANFE", ln=1, align="C")
    
    pdf.set_font("Helvetica", size=5)
    pdf.set_x(100)
    pdf.multi_cell(30, 2.5, txt="DOCUMENTO AUXILIAR\nDA NOTA FISCAL\nELETRÔNICA", align="C")
    
    # Caixinha de Entrada/Saída
    pdf.set_font("Helvetica", size=7)
    pdf.set_xy(102, y_emitente + 11)
    pdf.cell(10, 4, txt="0 - ENTRADA")
    pdf.set_xy(102, y_emitente + 15)
    pdf.cell(10, 4, txt="1 - SAÍDA")
    pdf.rect(122, y_emitente + 13, 4, 4)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(122, y_emitente + 13)
    pdf.cell(4, 4, txt="1", align="C")
    
    # Nº e Série (dentro do bloco central)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_xy(100, y_emitente + 20)
    pdf.cell(30, 3.5, txt=f"Nº {invoice.number}", align="C", ln=1)
    pdf.set_x(100)
    pdf.cell(30, 3.5, txt=f"SÉRIE: {getattr(invoice, 'series', '1')}", align="C", ln=1)

    # --- BLOCO 4: CONTROLE DO FISCO / CHAVE (MOLDURA IDÊNTICA) ---
    # Usamos a mesma espessura dos outros (0.2)
    pdf.set_line_width(0.2) 
    pdf.rect(130, y_emitente, 70, 30)
    
    # 1. Título
    pdf.set_xy(130, y_emitente + 1)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(70, 3, txt="CONTROLE DO FISCO", align="C", ln=1)
    
    # 2. Código de Barras
    try:
        import barcode
        from barcode.writer import ImageWriter
        chave_limpa = "".join(filter(str.isdigit, str(invoice.access_key)))
        writer = ImageWriter()
        COD128 = barcode.get_barcode_class('code128')
        my_barcode = COD128(chave_limpa, writer=writer)
        
        options = {"module_height": 10.0, "module_width": 0.2, "quiet_zone": 1.0, "write_text": False}
        barcode_filename = f"temp_barcode_{invoice.id}"
        path_completo = my_barcode.save(barcode_filename, options=options)
        pdf.image(path_completo, x=132, y=y_emitente + 4, w=66, h=10)
        
        if os.path.exists(path_completo):
            os.remove(path_completo)
    except Exception as e:
        print(f"ERRO BARCODE: {e}")

    # 3. Chave de Acesso (Centralizada e em uma linha)
    pdf.set_xy(130, y_emitente + 15)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(70, 3, txt="CHAVE DE ACESSO", align="C", ln=1)
    
    pdf.set_xy(130, y_emitente + 18)
    pdf.set_font("Helvetica", size=7.5)
    pdf.cell(70, 3, txt=chave_limpa, align="C", ln=1)

    # 4. Texto de Consulta (Centralizado no Rodapé)
    pdf.set_xy(132, y_emitente + 22)
    pdf.set_font("Helvetica", size=5.5) 
    texto_consulta = "Consulta de autenticidade no portal nacional da NF-e www.nfe.fazenda.gov.br/portal ou no site da Sefaz Autorizada."
    pdf.multi_cell(66, 2.5, txt=texto_consulta, align="C")

# --- 2. NATUREZA DA OPERAÇÃO / PROTOCOLO ---
    y_natureza = 60 # Posição logo abaixo do quadro do emitente
    
    # Lógica para determinar a descrição da Natureza da Operação
    # Buscamos o primeiro item da nota para determinar o CFOP predominante
    first_item = invoice.items[0] if invoice.items else None
    cfop_value = first_item.cfop if first_item else ""
    
    if cfop_value.startswith('5'):
        natureza_texto = "VENDA DENTRO DO ESTADO"
    elif cfop_value.startswith('6'):
        natureza_texto = "VENDA FORA DO ESTADO"
    else:
        natureza_texto = "VENDA DE MERCADORIA" # Fallback

    # Bloco Natureza da Operação
    pdf.rect(10, y_natureza, 120, 10)
    pdf.set_xy(11, y_natureza + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(118, 3, txt="NATUREZA DA OPERAÇÃO", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(11)
    pdf.cell(118, 5, txt=natureza_texto) 

    # Bloco Protocolo de Autorização de Uso
    # Conforme solicitado, utiliza o nprot (ou protocol_number) da tabela invoice
    pdf.rect(130, y_natureza, 70, 10)
    pdf.set_xy(131, y_natureza + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(68, 3, txt="PROTOCOLO DE AUTORIZAÇÃO DE USO", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(131)
    
    # Busca o dado dinâmico do seu modelo atualizado
    protocolo_final = str(invoice.nprot) if hasattr(invoice, 'nprot') and invoice.nprot else ""
    
    pdf.cell(68, 5, txt=protocolo_final)

        # --- 3. INSCRIÇÃO ESTADUAL E CNPJ ---
    y_id = 70  # Posicionamento abaixo da Natureza da Operação
    store_data = session.get('Store', {})

    # Função interna para formatar CNPJ (Máscara)
    def format_cnpj(doc):
        d = ''.join(filter(str.isdigit, str(doc)))
        if len(d) == 14:
            return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        return d

    # Campo: INSCRIÇÃO ESTADUAL
    pdf.rect(10, y_id, 65, 10)
    pdf.set_xy(11, y_id + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(63, 3, txt="INSCRIÇÃO ESTADUAL", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(11)
    # Busca 'State_Registration' da sessão conforme sua nova função parametrosloja()
    ie = store_data.get('State_Registration', '')
    pdf.cell(63, 5, txt=str(ie))

    # Campo: INSC. ESTADUAL DO SUBST. TRIB. (Vazio conforme solicitado)
    pdf.rect(75, y_id, 55, 10)
    pdf.set_xy(76, y_id + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(53, 3, txt="INSC. ESTADUAL DO SUBST. TRIB.", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(76)
    pdf.cell(53, 5, txt="")

    # Campo: CNPJ
    pdf.rect(130, y_id, 70, 10)
    pdf.set_xy(131, y_id + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(68, 3, txt="CNPJ", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(131)
    # Busca 'Code' (CNPJ) da sessão e aplica a máscara
    cnpj_raw = store_data.get('Code', '')
    pdf.cell(68, 5, txt=format_cnpj(cnpj_raw))

    # --- TÍTULO DA SECÇÃO: DESTINATÁRIO / REMETENTE ---
    # Posicionado entre a linha da IE/CNPJ (y=70) e o início dos dados do cliente (y=82)
    pdf.set_xy(10, 80)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(190, 3, txt="DESTINATÁRIO/REMETENTE", ln=1)

    # --- 4. BLOCO DESTINATÁRIO / REMETENTE ---
    y_dest = 83 # Início do bloco do destinatário
    client = invoice.client # Objeto Client vindo do seu models.py

    # --- FUNÇÕES DE FORMATAÇÃO (MÁSCARAS) ---
    def format_document(doc, type_code):
        d = ''.join(filter(str.isdigit, str(doc)))
        if type_code == 'F' and len(d) == 11:
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        elif type_code == 'J' and len(d) == 14:
            return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        return d

    def format_cep(cep):
        c = ''.join(filter(str.isdigit, str(cep)))
        if len(c) == 8:
            return f"{c[:5]}-{c[5:]}"
        return c

    def format_phone(phone):
        p = ''.join(filter(str.isdigit, str(phone)))
        if len(p) == 10:
            return f"({p[:2]}) {p[2:6]}-{p[6:]}"
        elif len(p) == 11:
            return f"({p[:2]}) {p[2:7]}-{p[7:]}"
        return p

    # --- PRIMEIRA LINHA DO DESTINATÁRIO ---
    # NOME/RAZÃO SOCIAL
    pdf.rect(10, y_dest, 120, 10)
    pdf.set_xy(11, y_dest + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(118, 3, txt="NOME/RAZÃO SOCIAL", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(11)
    pdf.cell(118, 5, txt=str(client.name).upper())

    # CNPJ/CPF
    pdf.rect(130, y_dest, 45, 10)
    pdf.set_xy(131, y_dest + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(43, 3, txt="CNPJ/CPF", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(131)
    pdf.cell(43, 5, txt=format_document(client.code, client.type))

    # DATA DE EMISSÃO
    pdf.rect(175, y_dest, 25, 10)
    pdf.set_xy(176, y_dest + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(23, 3, txt="DATA DE EMISSÃO", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(176)
    pdf.cell(23, 5, txt=invoice.issue_date.strftime('%d/%m/%Y'))

    # --- SEGUNDA LINHA DO DESTINATÁRIO ---
    y_dest2 = y_dest + 10
    
    # ENDEREÇO (Logradouro + Número)
    pdf.rect(10, y_dest2, 95, 10)
    pdf.set_xy(11, y_dest2 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(93, 3, txt="ENDEREÇO", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(11)
    endereco_completo = f"{client.address}, {client.number}"
    pdf.cell(93, 5, txt=endereco_completo.upper())

    # BAIRRO/DISTRITO
    pdf.rect(105, y_dest2, 45, 10)
    pdf.set_xy(106, y_dest2 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(43, 3, txt="BAIRRO/DISTRITO", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(106)
    pdf.cell(43, 5, txt=str(client.neighborhood).upper())

    # CEP
    pdf.rect(150, y_dest2, 25, 10)
    pdf.set_xy(151, y_dest2 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(23, 3, txt="CEP", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(151)
    pdf.cell(23, 5, txt=format_cep(client.zipcode))

    # DATA DE ENTRADA/SAÍDA
    pdf.rect(175, y_dest2, 25, 10)
    pdf.set_xy(176, y_dest2 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(23, 3, txt="DATA ENTR./SAÍDA", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(176)
    pdf.cell(23, 5, txt=invoice.issue_date.strftime('%d/%m/%Y'))

    # --- TERCEIRA LINHA DO DESTINATÁRIO ---
    y_dest3 = y_dest2 + 10

    # MUNICÍPIO
    pdf.rect(10, y_dest3, 75, 10)
    pdf.set_xy(11, y_dest3 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(73, 3, txt="MUNICÍPIO", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(11)
    pdf.cell(73, 5, txt=str(client.city).upper())

    # FONE/FAX
    pdf.rect(85, y_dest3, 40, 10)
    pdf.set_xy(86, y_dest3 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(38, 3, txt="FONE/FAX", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(86)
    pdf.cell(38, 5, txt=format_phone(client.contact))

    # UF
    pdf.rect(125, y_dest3, 10, 10)
    pdf.set_xy(126, y_dest3 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(8, 3, txt="UF", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(126)
    pdf.cell(8, 5, txt=str(client.region).upper())

    # INSCRIÇÃO ESTADUAL (Vazio conforme solicitado)
    pdf.rect(135, y_dest3, 40, 10)
    pdf.set_xy(136, y_dest3 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(38, 3, txt="INSCRIÇÃO ESTADUAL", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(136)
    pdf.cell(38, 5, txt="")

    # HORA DE ENTRADA/SAÍDA
    pdf.rect(175, y_dest3, 25, 10)
    pdf.set_xy(176, y_dest3 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(23, 3, txt="HORA ENTR./SAÍDA", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.set_x(176)
    pdf.cell(23, 5, txt=invoice.issue_date.strftime('%H:%M'))

    # --- 5. QUADRO FATURA ---
    y_fatura = 113 # Posicionado após o bloco do destinatário
    pdf.set_xy(10, y_fatura)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(190, 4, txt="FATURA", ln=1)
    
    # Linha em branco (conforme solicitado)
    y_imposto_titulo = y_fatura + 8
    
    # --- 6. CÁLCULO DO IMPOSTO ---
    pdf.set_xy(10, y_imposto_titulo)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(190, 4, txt="CÁLCULO DO IMPOSTO", ln=1)
    
    y_grid = y_imposto_titulo + 4
    
    # Valores para o cálculo
    total_prod = float(invoice.total_value or 0)
    desconto = float(invoice.discount or 0)
    total_nota = total_prod - desconto

    # --- PRIMEIRA LINHA DA BORDA (IMPOSTOS ZERADOS + TOTAL PRODUTOS) ---
    # Larguras das colunas para totalizar 190mm
    w_col = 190 / 9 # Divisão aproximada para as 9 colunas da primeira linha
    
    pdf.set_font("Helvetica", "B", 5)
    
    # Headers e Células da Primeira Linha
    colunas1 = [
        ("BASE DE CÁLC. ICMS", "0,00"),
        ("VALOR DO ICMS", "0,00"),
        ("B. CÁLC. ICMS ST", "0,00"),
        ("VALOR ICMS ST", "0,00"),
        ("V. IMP. IMPORT.", "0,00"),
        ("V. ICMS UF REMET.", "0,00"),
        ("VALOR DO FCP", "0,00"),
        ("VALOR DO PIS", "0,00"),
        ("V. TOTAL PROD.", f"{total_prod:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'))
    ]

    curr_x = 10
    for header, valor in colunas1:
        pdf.rect(curr_x, y_grid, w_col, 10)
        pdf.set_xy(curr_x + 0.5, y_grid + 1)
        pdf.set_font("Helvetica", "B", 5)
        pdf.multi_cell(w_col - 1, 2.5, txt=header, align='L')
        pdf.set_xy(curr_x, y_grid + 5)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(w_col, 5, txt=valor, align='R')
        curr_x += w_col

    # --- SEGUNDA LINHA DA BORDA (FRETE, SEGURO, DESCONTO, ETC) ---
    y_grid2 = y_grid + 10
    w_col2 = 190 / 9 # 9 colunas também na segunda linha

    colunas2 = [
        ("VALOR DO FRETE", "0,00"),
        ("VALOR SEGURO", "0,00"),
        ("DESCONTO", f"{desconto:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')),
        ("OUTRAS DESP.", "0,00"),
        ("VALOR DO IPI", "0,00"),
        ("V. ICMS UF DEST.", "0,00"),
        ("V. APROX. TRIB.", "0,00"),
        ("VALOR COFINS", "0,00"),
        ("V. TOTAL NOTA", f"{total_nota:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'))
    ]

    curr_x = 10
    for header, valor in colunas2:
        pdf.rect(curr_x, y_grid2, w_col2, 10)
        pdf.set_xy(curr_x + 0.5, y_grid2 + 1)
        pdf.set_font("Helvetica", "B", 5)
        pdf.multi_cell(w_col2 - 1, 2.5, txt=header, align='L')
        pdf.set_xy(curr_x, y_grid2 + 5)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(w_col2, 5, txt=valor, align='R')
        curr_x += w_col2

    # --- 7. TRANSPORTADOR / VOLUMES TRANSPORTADOS ---
    y_transp_titulo = y_grid2 + 12 # Espaçamento após o cálculo do imposto
    
    pdf.set_xy(10, y_transp_titulo)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(190, 4, txt="TRANSPORTADOR/VOLUMES TRANSPORTADOS", ln=1)
    
    y_tgrid = y_transp_titulo + 4
    
    # --- PRIMEIRA LINHA DA BORDA (RAZÃO SOCIAL, FRETE, PLACA, ETC) ---
    # Razão Social
    pdf.rect(10, y_tgrid, 75, 10)
    pdf.set_xy(11, y_tgrid + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(73, 3, txt="RAZÃO SOCIAL", ln=1)
    
    # Frete por Conta (Com a caixinha e o número 9)
    pdf.rect(85, y_tgrid, 35, 10)
    pdf.set_xy(86, y_tgrid + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(33, 2, txt="FRETE POR CONTA", ln=1)
    pdf.set_font("Helvetica", size=5)
    pdf.set_x(86)
    pdf.cell(33, 2, txt="0-Emitente", ln=1)
    pdf.set_x(86)
    pdf.cell(33, 2, txt="1-Destinatário", ln=1)
    pdf.set_x(86)
    pdf.cell(33, 2, txt="9-Sem Frete", ln=1)
    
    # Caixinha do Frete (Valor 9 conforme solicitado)
    pdf.rect(112, y_tgrid + 3, 5, 5) 
    pdf.set_xy(112, y_tgrid + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(5, 5, txt="9", align='C')
    
    # Código ANTT
    pdf.rect(120, y_tgrid, 25, 10)
    pdf.set_xy(121, y_tgrid + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.cell(23, 3, txt="CÓDIGO ANTT", ln=1)
    
    # Placa do Veículo
    pdf.rect(145, y_tgrid, 20, 10)
    pdf.set_xy(146, y_tgrid + 1)
    pdf.cell(18, 3, txt="PLACA", ln=1)
    
    # UF Veículo
    pdf.rect(165, y_tgrid, 10, 10)
    pdf.set_xy(166, y_tgrid + 1)
    pdf.cell(8, 3, txt="UF", ln=1)
    
    # CNPJ/CPF Transportador
    pdf.rect(175, y_tgrid, 25, 10)
    pdf.set_xy(176, y_tgrid + 1)
    pdf.cell(23, 3, txt="CNPJ/CPF", ln=1)

    # --- SEGUNDA LINHA DA BORDA (ENDEREÇO, MUNICÍPIO, UF, IE) ---
    y_tgrid2 = y_tgrid + 10
    
    pdf.rect(10, y_tgrid2, 75, 10) # Endereço
    pdf.set_xy(11, y_tgrid2 + 1)
    pdf.cell(73, 3, txt="ENDEREÇO", ln=1)
    
    pdf.rect(85, y_tgrid2, 60, 10) # Município
    pdf.set_xy(86, y_tgrid2 + 1)
    pdf.cell(58, 3, txt="MUNICÍPIO", ln=1)
    
    pdf.rect(145, y_tgrid2, 10, 10) # UF
    pdf.set_xy(146, y_tgrid2 + 1)
    pdf.cell(8, 3, txt="UF", ln=1)
    
    pdf.rect(155, y_tgrid2, 45, 10) # Inscrição Estadual
    pdf.set_xy(156, y_tgrid2 + 1)
    pdf.cell(43, 3, txt="INSCRIÇÃO ESTADUAL", ln=1)

    # --- TERCEIRA LINHA DA BORDA (VOLUMES) ---
    y_tgrid3 = y_tgrid2 + 10
    w_vol = 190 / 6 # Divisão igual para as 6 colunas de volumes
    
    titulos_volumes = ["QUANTIDADE", "ESPÉCIE", "MARCA", "NUMERAÇÃO", "PESO BRUTO", "PESO LÍQUIDO"]
    
    curr_tx = 10
    for titulo in titulos_volumes:
        pdf.rect(curr_tx, y_tgrid3, w_vol, 10)
        pdf.set_xy(curr_tx + 1, y_tgrid3 + 1)
        pdf.set_font("Helvetica", "B", 6)
        pdf.cell(w_vol - 2, 3, txt=titulo, ln=1)
        curr_tx += w_vol

    # --- 8. DADOS DO PRODUTO / SERVIÇO ---
    y_prod_titulo = y_tgrid3 + 12
    pdf.set_xy(10, y_prod_titulo)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(190, 4, txt="DADOS DO PRODUTO/SERVIÇO", ln=1)

    y_pheader = y_prod_titulo + 4
    # Definição precisa das larguras das colunas (Soma total = 190mm)
    cols = {
        'cod': 12, 'desc': 53, 'ncm': 15, 'cst': 8, 'cfop': 10, 
        'un': 7, 'qtd': 10, 'v_unit': 15, 'v_total': 15, 
        'bc': 10, 'v_icms': 10, 'v_ipi': 10, 'a_icms': 7, 'a_ipi': 8
    }

    # --- CABEÇALHO EM DUAS LINHAS ---
    pdf.set_font("Helvetica", "B", 5)
    headers = [
        ('CÓDIGO', '', 'cod'), ('DESCRIÇÃO DO PRODUTO/SERVIÇO', '', 'desc'), 
        ('NCM/SH', '', 'ncm'), ('CST', '', 'cst'), ('CFOP', '', 'cfop'), 
        ('UN', '', 'un'), ('QTDE.', '', 'qtd'), ('VLR.', 'UNIT.', 'v_unit'), 
        ('VLR.', 'TOTAL', 'v_total'), ('BC', 'ICMS', 'bc'), ('VLR.', 'ICMS', 'v_icms'), 
        ('VLR.', 'IPI', 'v_ipi'), ('ALIQ.', 'ICMS', 'a_icms'), ('ALIQ.', 'IPI', 'a_ipi')
    ]

    curr_px = 10
    for h1, h2, key in headers:
        pdf.rect(curr_px, y_pheader, cols[key], 8)
        pdf.set_xy(curr_px, y_pheader + 1)
        pdf.cell(cols[key], 3, txt=h1, align='C')
        if h2:
            pdf.set_xy(curr_px, y_pheader + 4)
            pdf.cell(cols[key], 3, txt=h2, align='C')
        curr_px += cols[key]

    # --- LOOP NOS ITENS ---
    y_item = y_pheader + 8
    pdf.set_font("Helvetica", size=7)

    for item in invoice.items:
        product = Product.query.get(item.product_id)
        
        # 1. Capturar o nome do produto
        p_name = product.name.upper() if product else "PRODUTO NÃO ENCONTRADO"
        
        # 2. Capturar o Serial Number (corrigido para garantir que apareça)
        # Usamos str() para garantir que números não quebrem a concatenação
        serial = ""
        if item.serialnumber:
            serial = f" S/N: {item.serialnumber}"
            
        # 3. Montar a descrição completa
        full_description = f"{p_name}{serial}"
        
        start_y = y_item
        line_height = 4
        
        # 4. Inserir o texto (o multi_cell cuidará da quebra de linha se for longo)
        pdf.set_xy(10 + cols['cod'], start_y)
        pdf.multi_cell(cols['desc'], line_height, txt=full_description, border=0, align='L')        
        # 1. Primeira passada: calcular altura da descrição multiline
        pdf.set_xy(10 + cols['cod'], start_y)
        pdf.multi_cell(cols['desc'], line_height, txt=full_description, border=0, align='L')
        end_y = pdf.get_y()
        row_height = max(8, end_y - start_y)

        # 2. Desenhar as células garantindo o alinhamento X com o cabeçalho
        temp_x = 10
        
        # Função para desenhar célula e borda sincronizada
        def draw_aligned_cell(key, text, align='C'):
            nonlocal temp_x
            pdf.rect(temp_x, start_y, cols[key], row_height)
            pdf.set_xy(temp_x, start_y)
            pdf.cell(cols[key], row_height, txt=str(text), align=align)
            temp_x += cols[key]

        # Aplicando a todas as colunas na ordem correta
        v_unit = f"{item.unit_price:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
        v_total = f"{item.total_price:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')

        draw_aligned_cell('cod', item.product_id)
        
        # Borda da descrição (o texto já foi inserido pelo multi_cell acima)
        pdf.rect(temp_x, start_y, cols['desc'], row_height)
        temp_x += cols['desc']
        
        draw_aligned_cell('ncm', getattr(item, 'ncm', '00000000'))
        draw_aligned_cell('cst', getattr(item, 'csosn', '0102'))
        draw_aligned_cell('cfop', item.cfop)
        draw_aligned_cell('un', "UN")
        draw_aligned_cell('qtd', item.quantity)
        draw_aligned_cell('v_unit', v_unit, align='R')
        draw_aligned_cell('v_total', v_total, align='R')
        
        # Colunas de impostos que estavam desalinhadas
        draw_aligned_cell('bc', "0,00", align='R')
        draw_aligned_cell('v_icms', "0,00", align='R')
        draw_aligned_cell('v_ipi', "0,00", align='R')
        draw_aligned_cell('a_icms', "0", align='R')
        draw_aligned_cell('a_ipi', "0", align='R')

        y_item = start_y + row_height
        
        # Quebra de página se necessário
        if y_item > 270:
            pdf.add_page()
            y_item = 20


    # --- AJUSTE: ALONGAR BORDAS DOS ITENS ATÉ O RODAPÉ ---
    # Definimos onde o rodapé deve começar (ex: y=230)
    y_rodape_inicio = 230
    
    # Desenha as linhas verticais para fechar o quadro de itens até o rodapé
    curr_px = 10
    for key in cols:
        pdf.line(curr_px, y_item, curr_px, y_rodape_inicio)
        curr_px += cols[key]
    pdf.line(200, y_item, 200, y_rodape_inicio) # Linha final direita
    pdf.line(10, y_rodape_inicio, 200, y_rodape_inicio) # Linha horizontal de fechamento

    # --- 9. CÁLCULO DO ISSQN ---
    y_issqn = y_rodape_inicio + 5
    pdf.set_xy(10, y_issqn)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(190, 4, txt="CÁLCULO DO ISSQN", ln=1)

    y_issqn_grid = y_issqn + 4
    w_issqn = 190 / 4

    # Linha 1: Cabeçalhos
    titulos_issqn = ["INSCRIÇÃO MUNICIPAL", "VALOR TOTAL DOS SERVIÇOS", "BASE DE CÁLCULO DO ISSQN", "VALOR DO ISSQN"]
    curr_ix = 10
    for titulo in titulos_issqn:
        pdf.rect(curr_ix, y_issqn_grid, w_issqn, 10)
        pdf.set_xy(curr_ix + 1, y_issqn_grid + 1)
        pdf.set_font("Helvetica", "B", 6)
        pdf.cell(w_issqn - 2, 3, txt=titulo, ln=1)
        
        # Linha 2: Valores (Inscrição vazia, demais zerados)
        pdf.set_xy(curr_ix, y_issqn_grid + 5)
        pdf.set_font("Helvetica", size=8)
        valor = "" if "INSCRIÇÃO" in titulo else "0,00"
        pdf.cell(w_issqn, 5, txt=valor, align='R' if valor else 'L')
        curr_ix += w_issqn

    # Espaço em branco solicitado
    y_adicionais = y_issqn_grid + 15

    # --- 10. DADOS ADICIONAIS ---
    pdf.set_xy(10, y_adicionais)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(190, 4, txt="DADOS ADICIONAIS", ln=1)

    y_adi_grid = y_adicionais + 4
    
    # Borda-2: Duas colunas iguais (95mm cada)
    pdf.rect(10, y_adi_grid, 95, 30)  # Coluna Informações Complementares
    pdf.rect(105, y_adi_grid, 95, 30) # Coluna Reserva ao Fisco

    # Títulos das Colunas
    pdf.set_font("Helvetica", "B", 6)
    pdf.set_xy(11, y_adi_grid + 1)
    pdf.cell(93, 3, txt="INFORMAÇÕES COMPLEMENTARES")
    pdf.set_xy(106, y_adi_grid + 1)
    pdf.cell(93, 3, txt="RESERVA AO FISCO")

    # Conteúdo Informações Complementares (Simples Nacional)
    pdf.set_font("Helvetica", size=7)
    texto_simples = (
        "DOCUMENTO EMITIDO POR ME OU EPP OPTANTE PELO SIMPLES NACIONAL. "
        "NAO GERA DIREITO A CREDITO FISCAL DE ICMS, ISS E IPI."
    )
    pdf.set_xy(11, y_adi_grid + 6)
    pdf.multi_cell(90, 3.5, txt=texto_simples, align='L')
    
    # Se houver informações do pedido/cliente, pode-se concatenar aqui:
    if invoice.order:
        pdf.set_x(11)
        pdf.cell(90, 4, txt=f"PEDIDO: {invoice.order.id}", ln=1)


    # --- FINALIZAÇÃO ---
    pdf_output = pdf.output(dest="S")
    return send_file(BytesIO(pdf_output), as_attachment=False, download_name=f"DANFE_{invoice.number}.pdf", mimetype="application/pdf")

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
@nfe_bp.route('/generate_xml_nfce/<int:id>', methods=['GET'])
def gerar_xml_nfce(id):
    """
    Gera o XML da NFC-e (modelo 65) usando:
    - access_key da invoice
    - dados do emitente vindos da sessão
    - NCM, CFOP e CSOSN vindos do invoice_item
    """

    invoice: Invoice = Invoice.query.get(id)
    if not invoice:
        raise Exception("Invoice não encontrada")

    if not invoice.access_key or len(invoice.access_key) != 44:
        raise Exception("Chave de acesso inválida ou não informada na invoice")

    # =========================
    # Emitente (via sessão)
    # =========================
    emitente = session.get("Store")
    if not emitente:
        raise Exception("Dados do emitente não encontrados na sessão")

    cnpj = emitente["Code"]
    razao_social = emitente["Name"]
    ie = emitente["State_Registration"]
    uf = emitente["Region"]

    # =========================
    # TAG RAIZ
    # =========================
    nfe = etree.Element(
        "{%s}NFe" % NAMESPACE,
        nsmap={None: NAMESPACE}
    )

    infNFe = etree.SubElement(
        nfe,
        "infNFe",
        Id=f"NFe{invoice.access_key}",
        versao="4.00"
    )

    # =========================
    # ide
    # =========================
    ide = etree.SubElement(infNFe, "ide")
    etree.SubElement(ide, "cUF").text = invoice.access_key[:2]
    etree.SubElement(ide, "natOp").text = "Venda"
    etree.SubElement(ide, "mod").text = "65"
    etree.SubElement(ide, "serie").text = str(invoice.series)
    etree.SubElement(ide, "nNF").text = str(invoice.number)
    etree.SubElement(ide, "tpAmb").text = TP_AMB
    etree.SubElement(ide, "tpNF").text = "1"
    etree.SubElement(ide, "finNFe").text = "1"
    etree.SubElement(ide, "indFinal").text = "1"
    etree.SubElement(ide, "indPres").text = "1"
    etree.SubElement(ide, "procEmi").text = "0"
    etree.SubElement(ide, "verProc").text = "Ouvirtiba 1.0"
    etree.SubElement(ide, "dhEmi").text = invoice.issue_date.isoformat()

    # =========================
    # emit
    # =========================
    emit = etree.SubElement(infNFe, "emit")
    etree.SubElement(emit, "CNPJ").text = cnpj
    etree.SubElement(emit, "xNome").text = razao_social
    etree.SubElement(emit, "IE").text = ie

    enderEmit = etree.SubElement(emit, "enderEmit")
    etree.SubElement(enderEmit, "UF").text = uf

    # =========================
    # Itens
    # =========================
    total_produtos = Decimal("0.00")

    for index, item in enumerate(invoice.items, start=1):
        det = etree.SubElement(infNFe, "det", nItem=str(index))

        # -------- PRODUTO --------
        prod = etree.SubElement(det, "prod")
        etree.SubElement(prod, "cProd").text = str(item.product_id)
        etree.SubElement(prod, "xProd").text = item.product.name
        etree.SubElement(prod, "NCM").text = item.ncm
        etree.SubElement(prod, "CFOP").text = item.cfop
        etree.SubElement(prod, "uCom").text = "UN"
        etree.SubElement(prod, "qCom").text = str(item.quantity)
        etree.SubElement(prod, "vUnCom").text = f"{item.unit_price:.2f}"
        etree.SubElement(prod, "vProd").text = f"{item.total_price:.2f}"
        etree.SubElement(prod, "indTot").text = "1"

        total_produtos += Decimal(str(item.total_price))

        # -------- ICMS (Simples Nacional) --------
        imposto = etree.SubElement(det, "imposto")
        icms = etree.SubElement(imposto, "ICMS")

        icmssn = etree.SubElement(icms, f"ICMSSN{item.csosn}")
        etree.SubElement(icmssn, "orig").text = "0"
        etree.SubElement(icmssn, "CSOSN").text = item.csosn

    # =========================
    # Total
    # =========================
    total = etree.SubElement(infNFe, "total")
    icmsTot = etree.SubElement(total, "ICMSTot")
    etree.SubElement(icmsTot, "vProd").text = f"{total_produtos:.2f}"
    etree.SubElement(icmsTot, "vNF").text = f"{invoice.total_value:.2f}"

    # =========================
    # Pagamento
    # =========================
    pag = etree.SubElement(infNFe, "pag")
    detPag = etree.SubElement(pag, "detPag")
    etree.SubElement(detPag, "tPag").text = "01"
    etree.SubElement(detPag, "vPag").text = f"{invoice.total_value:.2f}"

    # =========================
    # Salvar XML
    # =========================
    xml_bytes = etree.tostring(
        nfe,
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )

    output_path = f"admin/nfe/output/nfce_{invoice.id}.xml"
    with open(output_path, "wb") as f:
        f.write(xml_bytes)

    invoice.xml_path = output_path
    invoice.status = "X"
    db.session.commit()

    # 🔔 mensagem de sucesso
    flash("Geração do XML da NFC-e concluída com sucesso!", "success")

    # 🔁 volta para lista
    return redirect(url_for('nfe_bp.nfe_list'))


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

# ================================================================
# 📄 GERENCIAMENTO DE ARQUIVOS XML
# ================================================================

@nfe_bp.route('/admin/nfe/xml/list')
def xml_list():
    """Lista todos os arquivos XML gerados na pasta admin/nfe/output"""
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))
    
    xml_folder = 'admin/nfe/output'
    xml_files = []
    
    # Verifica se a pasta existe
    if os.path.exists(xml_folder):
        # Lista todos os arquivos XML
        for filename in os.listdir(xml_folder):
            if filename.endswith('.xml'):
                filepath = os.path.join(xml_folder, filename)
                
                # Obtém informações do arquivo
                file_stats = os.stat(filepath)
                file_size = file_stats.st_size
                
                # Formata o tamanho
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                # Formata a data de criação
                created_timestamp = file_stats.st_mtime
                created_date = datetime.fromtimestamp(created_timestamp)
                created_str = created_date.strftime('%d/%m/%Y %H:%M')
                
                xml_files.append({
                    'name': filename,
                    'size': size_str,
                    'created_at': created_str,
                    'timestamp': created_timestamp
                })
        
        # Ordena por data de criação (mais recente primeiro)
        xml_files.sort(key=lambda x: x['timestamp'], reverse=True)
    else:
        flash(f"⚠️ Pasta '{xml_folder}' não encontrada.", "warning")
    
    return render_template(
        'admin/nfe/xml_list.html',
        xml_files=xml_files,
        titulo="Lista de XMLs Gerados"
    )


@nfe_bp.route('/admin/nfe/xml/edit/<filename>', methods=['GET', 'POST'])
def xml_edit(filename):
    """Edita um arquivo XML específico"""
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))
    
    # Valida o nome do arquivo (segurança)
    if '..' in filename or '/' in filename or '\\' in filename:
        flash("❌ Nome de arquivo inválido!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    if not filename.endswith('.xml'):
        flash("❌ Arquivo deve ser do tipo XML!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    xml_folder = 'admin/nfe/output'
    filepath = os.path.join(xml_folder, filename)
    
    # Verifica se o arquivo existe
    if not os.path.exists(filepath):
        flash(f"❌ Arquivo '{filename}' não encontrado!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    if request.method == 'POST':
        try:
            xml_content = request.form.get('xml_content', '')
            
            # Cria backup antes de salvar
            backup_folder = os.path.join(xml_folder, 'backup')
            os.makedirs(backup_folder, exist_ok=True)
            
            backup_filename = f"{filename}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(backup_folder, backup_filename)
            
            # Copia o arquivo original para backup
            import shutil
            shutil.copy2(filepath, backup_path)
            
            # Salva o conteúdo editado
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            flash(f"✅ XML '{filename}' salvo com sucesso! Backup criado em: {backup_filename}", "success")
            return redirect(url_for('nfe_bp.xml_list'))
            
        except Exception as e:
            flash(f"❌ Erro ao salvar XML: {e}", "danger")
            return redirect(url_for('nfe_bp.xml_edit', filename=filename))
    
    # GET - Carrega o conteúdo do arquivo
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            xml_content = f.read()
    except Exception as e:
        flash(f"❌ Erro ao ler arquivo: {e}", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    return render_template(
        'admin/nfe/xml_edit.html',
        filename=filename,
        xml_content=xml_content,
        titulo=f"Editar XML: {filename}"
    )


@nfe_bp.route('/admin/nfe/xml/download/<filename>')
def xml_download(filename):
    """Faz download de um arquivo XML específico"""
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))
    
    # Valida o nome do arquivo (segurança)
    if '..' in filename or '/' in filename or '\\' in filename:
        flash("❌ Nome de arquivo inválido!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    if not filename.endswith('.xml'):
        flash("❌ Arquivo deve ser do tipo XML!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    xml_folder = 'admin/nfe/output'
    filepath = os.path.join(xml_folder, filename)
    
    if not os.path.exists(filepath):
        flash(f"❌ Arquivo '{filename}' não encontrado!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    try:
        return send_file(
            filepath,
            mimetype='application/xml',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f"❌ Erro ao fazer download: {e}", "danger")
        return redirect(url_for('nfe_bp.xml_list'))


@nfe_bp.route('/admin/nfe/xml/delete/<filename>', methods=['POST'])
def xml_delete(filename):
    """Exclui um arquivo XML específico"""
    if 'email' not in session:
        flash('Favor fazer o seu login no sistema primeiro!', 'danger')
        return redirect(url_for('login', origin='admin'))
    
    # Valida o nome do arquivo (segurança)
    if '..' in filename or '/' in filename or '\\' in filename:
        flash("❌ Nome de arquivo inválido!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    if not filename.endswith('.xml'):
        flash("❌ Arquivo deve ser do tipo XML!", "danger")
        return redirect(url_for('nfe_bp.xml_list'))
    
    xml_folder = 'admin/nfe/output'
    filepath = os.path.join(xml_folder, filename)
    
    try:
        if os.path.exists(filepath):
            # Cria backup antes de excluir
            backup_folder = os.path.join(xml_folder, 'backup')
            os.makedirs(backup_folder, exist_ok=True)
            
            backup_filename = f"{filename}.deleted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(backup_folder, backup_filename)
            
            # Move para backup em vez de excluir permanentemente
            import shutil
            shutil.move(filepath, backup_path)
            
            flash(f"✅ Arquivo '{filename}' excluído com sucesso! Backup salvo como: {backup_filename}", "success")
        else:
            flash(f"❌ Arquivo '{filename}' não encontrado!", "danger")
    except Exception as e:
        flash(f"❌ Erro ao excluir arquivo: {e}", "danger")
    
    return redirect(url_for('nfe_bp.xml_list'))