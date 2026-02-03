"""
Gerador de URL do QR Code para NFC-e conforme padrão SEFAZ
Nota Técnica 2015.002 versão 1.50
"""

import hashlib
from urllib.parse import urlencode


def gerar_qrcode_url(chave_acesso, ambiente, id_token, csc_token):
    """
    Gera a URL do QR Code para NFC-e (modelo 65)
    
    Parâmetros conforme NT 2015.002:
    - chave_acesso: Chave de acesso da NFC-e (44 dígitos)
    - ambiente: 1=Produção, 2=Homologação
    - id_token: ID do CSC (Código de Segurança do Contribuinte)
    - csc_token: Token do CSC
    
    Formato da URL:
    https://[dominio]/nfce/consulta?p=[chave]|[versao]|[tpAmb]|[cDest]|[dhEmi]|[vNF]|[digVal]|[idToken]|[hash]
    
    Onde:
    - p = parâmetros concatenados por pipe (|)
    - chave = chave de acesso (44 posições)
    - versao = versão do QR Code (fixo: 2)
    - tpAmb = tipo de ambiente (1=Prod, 2=Homolog)
    - cDest = identificação do destinatário (CNPJ/CPF ou vazio)
    - dhEmi = data/hora de emissão (vazio para NFC-e - opcional)
    - vNF = valor da nota (vazio para NFC-e - opcional)
    - digVal = digest value da assinatura (vazio antes de assinar)
    - idToken = ID do CSC
    - hash = SHA-1 dos parâmetros + CSC
    
    Retorna: URL completa do QR Code
    """
    
    # Validações básicas
    if not chave_acesso or len(chave_acesso) != 44:
        raise ValueError(f"Chave de acesso inválida: {chave_acesso}")
    
    if ambiente not in [1, 2]:
        raise ValueError(f"Ambiente inválido: {ambiente}. Use 1 (Produção) ou 2 (Homologação)")
    
    if not id_token or not csc_token:
        raise ValueError("CSC ID e Token são obrigatórios")
    
    # ============================================================
    # Monta os parâmetros do QR Code
    # ============================================================
    
    # Versão do QR Code (sempre 2 para NFC-e)
    versao = "2"
    
    # Tipo de ambiente
    tp_amb = str(ambiente)
    
    # Identificação do destinatário (vazio para NFC-e sem CPF/CNPJ)
    # Você pode passar o CPF/CNPJ aqui se desejar, mas é opcional
    c_dest = ""
    
    # Data/hora de emissão (vazio para simplificar - opcional)
    dh_emi = ""
    
    # Valor da nota (vazio para simplificar - opcional)
    v_nf = ""
    
    # Digest Value (vazio antes da assinatura)
    dig_val = ""
    
    # ============================================================
    # Gera o Hash SHA-1
    # ============================================================
    
    # String para hash: chave|versao|tpAmb|cDest|dhEmi|vNF|digVal|idToken|cscToken
    # ATENÇÃO: Os campos vazios também entram no hash (com os pipes)
    parametros_hash = f"{chave_acesso}|{versao}|{tp_amb}|{id_token}|{csc_token}"
    
    # Calcula SHA-1
    hash_sha1 = hashlib.sha1(parametros_hash.encode('utf-8')).hexdigest().upper()
    
    # ============================================================
    # Monta a URL final do QR Code
    # ============================================================
    
    # Parâmetros da URL (sem o CSC Token - ele só entra no hash!)
    parametros_url = f"{chave_acesso}|{versao}|{tp_amb}|{id_token}|{hash_sha1}"
    
    # URL base conforme ambiente
    if ambiente == 2:
        url_base = "https://hom.sat.sef.sc.gov.br/nfce/consulta"
    else:
        url_base = "https://sat.sef.sc.gov.br/nfce/consulta"
    
    # URL completa
    qrcode_url = f"{url_base}?p={parametros_url}"
    
    return qrcode_url


def gerar_qrcode_url_completo(chave_acesso, ambiente, id_token, csc_token, 
                               cpf_cnpj_dest="", dh_emissao="", valor_nf="", digest_value=""):
    """
    Versão completa com todos os parâmetros opcionais
    Use esta versão se precisar incluir CPF/CNPJ do destinatário ou outros dados
    
    Parâmetros adicionais:
    - cpf_cnpj_dest: CPF ou CNPJ do destinatário (sem pontos/traços)
    - dh_emissao: Data/hora no formato hexadecimal (raramente usado)
    - valor_nf: Valor da nota formatado (raramente usado)
    - digest_value: Digest da assinatura (usar após assinar o XML)
    """
    
    # Validações
    if not chave_acesso or len(chave_acesso) != 44:
        raise ValueError(f"Chave de acesso inválida: {chave_acesso}")
    
    if ambiente not in [1, 2]:
        raise ValueError(f"Ambiente inválido: {ambiente}")
    
    if not id_token or not csc_token:
        raise ValueError("CSC ID e Token são obrigatórios")
    
    # Versão do QR Code
    versao = "2"
    tp_amb = str(ambiente)
    
    # Limpa CPF/CNPJ (remove caracteres especiais)
    if cpf_cnpj_dest:
        cpf_cnpj_dest = ''.join(filter(str.isdigit, cpf_cnpj_dest))
    
    # ============================================================
    # Gera o Hash SHA-1 com TODOS os parâmetros
    # ============================================================
    
    # Monta string para hash (TODOS os campos, mesmo vazios)
    parametros_hash = (
        f"{chave_acesso}|{versao}|{tp_amb}|{cpf_cnpj_dest}|"
        f"{dh_emissao}|{valor_nf}|{digest_value}|{id_token}|{csc_token}"
    )
    
    # Calcula SHA-1
    hash_sha1 = hashlib.sha1(parametros_hash.encode('utf-8')).hexdigest().upper()
    
    # ============================================================
    # Monta URL
    # ============================================================
    
    # Parâmetros da URL (SEM o CSC Token)
    parametros_url = (
        f"{chave_acesso}|{versao}|{tp_amb}|{cpf_cnpj_dest}|"
        f"{dh_emissao}|{valor_nf}|{digest_value}|{id_token}|{hash_sha1}"
    )
    
    # URL base
    if ambiente == 2:
        url_base = "https://hom.sat.sef.sc.gov.br/nfce/consulta"
    else:
        url_base = "https://sat.sef.sc.gov.br/nfce/consulta"
    
    qrcode_url = f"{url_base}?p={parametros_url}"
    
    return qrcode_url


def validar_qrcode_url(qrcode_url):
    """
    Valida se a URL do QR Code está no formato correto
    
    Retorna: (bool, mensagem)
    """
    
    try:
        # Verifica se tem o parâmetro 'p'
        if '?p=' not in qrcode_url:
            return False, "URL deve conter o parâmetro ?p="
        
        # Extrai os parâmetros
        params = qrcode_url.split('?p=')[1]
        partes = params.split('|')
        
        # Deve ter pelo menos 5 partes (versão simplificada)
        if len(partes) < 5:
            return False, f"Formato inválido. Esperado pelo menos 5 partes, encontrado {len(partes)}"
        
        # Valida chave de acesso (primeira parte)
        chave = partes[0]
        if len(chave) != 44 or not chave.isdigit():
            return False, f"Chave de acesso inválida: {chave}"
        
        # Valida versão (segunda parte)
        versao = partes[1]
        if versao != "2":
            return False, f"Versão deve ser 2, encontrado: {versao}"
        
        # Valida ambiente (terceira parte)
        ambiente = partes[2]
        if ambiente not in ["1", "2"]:
            return False, f"Ambiente deve ser 1 ou 2, encontrado: {ambiente}"
        
        # Valida hash SHA-1 (última parte) - deve ter 40 caracteres hexadecimais
        hash_sha1 = partes[-1]
        if len(hash_sha1) != 40:
            return False, f"Hash SHA-1 deve ter 40 caracteres, encontrado: {len(hash_sha1)}"
        
        try:
            int(hash_sha1, 16)  # Tenta converter para hex
        except ValueError:
            return False, f"Hash SHA-1 inválido (não é hexadecimal): {hash_sha1}"
        
        return True, "URL válida"
        
    except Exception as e:
        return False, f"Erro ao validar: {str(e)}"
