class NFeConfig:
    # ============================================================
    # CONFIGURAÇÕES GERAIS
    # ============================================================
    UF = "SC"
    TP_AMB = "2"  # 2 = Homologação, 1 = Produção
    
    # ============================================================
    # CÓDIGOS DE MUNICÍPIO (IBGE)
    # ============================================================
    IBGE_CITY_CODE = "4209102"      # Joinville/SC (Emitente)
    IBGE_CITY_CODE_CLI = "4209102"  # Joinville/SC (Cliente padrão)
    
    # ============================================================
    # REGIME TRIBUTÁRIO
    # ============================================================
    CRT = "1"  # 1=Simples Nacional
    
    # ============================================================
    # IDENTIFICAÇÃO DA OPERAÇÃO (TAG IDE)
    # ============================================================
    NATOP = "VENDA DE MERCADORIA"
    MOD = "65"          # Modelo 65 = NFC-e
    TP_NF = "1"         # 1=Saída
    ID_DEST = "1"       # 1=Operação interna, 2=Interestadual, 3=Exterior
    TP_IMP = "4"        # 4=DANFE NFC-e em papel
    TP_EMIS = "1"       # 1=Emissão normal
    FIN_NFE = "1"       # 1=NF-e normal
    IND_FINAL = "1"     # 1=Consumidor final
    IND_PRES = "1"      # 1=Operação presencial
    PROC_EMI = "0"      # 0=Emissão com aplicativo do contribuinte
    VER_PROC = "Ouvirtiba 1.0"
    
    # ============================================================
    # EMITENTE
    # ============================================================
    CNPJ_EMITENTE = "56154376000105"
    IE_EMITENTE = "263067041"
    RAZAO_SOCIAL = "JANSSEN APARELHOS AUDITIVOS LTDA"
    XFANT = "OUVRTIBA APARELHOS AUDITIVOS"
    
    # ============================================================
    # DADOS INTERNACIONAIS
    # ============================================================
    CPAIS = "1058"
    XPAIS = "BRASIL"
    
    # ============================================================
    # DESTINATÁRIO
    # ============================================================
    IND_IE_DEST = "9"  # 9=Não Contribuinte
    
    # ============================================================
    # ITENS/PRODUTOS
    # ============================================================
    CEAN = "SEM GTIN"
    UCOM = "UN"
    IND_TOT = "1"       # 1=Compõe total da NF-e
    TX_TRIB = "0.15"    # 15% = Taxa aproximada de tributos
    PIS_CST = "99"      # 99=Outras operações
    COFINS_CST = "99"   # 99=Outras operações
    
    # ============================================================
    # TRANSPORTE
    # ============================================================
    MOD_FRETE = "9"  # 9=Sem frete
    
    # ============================================================
    # PAGAMENTO
    # ============================================================
    IND_PAG = "0"  # 0=Pagamento à Vista
    T_PAG = "01"   # 01=Dinheiro
    
    # ============================================================
    # INFORMAÇÕES ADICIONAIS
    # ============================================================
    INF_ADIC_TXT_1 = "DOCUMENTO EMITIDO POR ME OU EPP OPTANTE PELO SIMPLES NACIONAL. "
    INF_ADIC_TXT_2 = "NAO GERA DIREITO A CREDITO FISCAL DE ICMS, ISS E IPI."
    
    # ============================================================
    # QR CODE (CSC - Código de Segurança do Contribuinte)
    # ============================================================
    # ⚠️ TOKENS FICTÍCIOS - Substituir pelos reais da SEFAZ
    CSC_ID = "000001"
    CSC_TOKEN = "1A2B3C4D5E6F7G8H9I0J"
    
    # ============================================================
    # URLS DE CONSULTA QR CODE
    # ============================================================
    URL_QRCODE_HOMOLOG = "https://hom.sat.sef.sc.gov.br/nfce/consulta"
    URL_QRCODE_PROD = "https://sat.sef.sc.gov.br/nfce/consulta"
    
    # ============================================================
    # CERTIFICADO DIGITAL A1
    # ============================================================
    # ⚠️ SENHA FICTÍCIA - Substituir pela senha real do certificado
    CERT_PFX_PATH = "admin/nfe/certs/JANSSEN APARELHOS AUDITIVOS LTDA56154376000105.pfx"
    CERT_PFX_PASSWORD = "123456"
    
    # ============================================================
    # NAMESPACE XML
    # ============================================================
    NAMESPACE = "http://www.portalfiscal.inf.br/nfe"
    
    # ============================================================
    # URLS DOS WEBSERVICES SEFAZ
    # ============================================================
    # Homologação
    WS_NFCE_AUTORIZACAO_HOMOLOG = "https://hom.nfe.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx"
    WS_NFCE_RET_AUTORIZACAO_HOMOLOG = "https://hom.nfe.fazenda.gov.br/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx"
    WS_NFCE_CONSULTA_HOMOLOG = "https://hom.nfe.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx"
    
    # Produção
    WS_NFCE_AUTORIZACAO_PROD = "https://nfe.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx"
    WS_NFCE_RET_AUTORIZACAO_PROD = "https://nfe.fazenda.gov.br/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx"
    WS_NFCE_CONSULTA_PROD = "https://nfe.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx"
    
    # ============================================================
    # CONFIGURAÇÕES DE AMBIENTE DINÂMICAS
    # ============================================================
    @classmethod
    def get_ws_autorizacao(cls):
        """Retorna URL do webservice de autorização conforme ambiente"""
        return cls.WS_NFCE_AUTORIZACAO_PROD if cls.TP_AMB == "1" else cls.WS_NFCE_AUTORIZACAO_HOMOLOG
    
    @classmethod
    def get_ws_ret_autorizacao(cls):
        """Retorna URL do webservice de consulta recibo conforme ambiente"""
        return cls.WS_NFCE_RET_AUTORIZACAO_PROD if cls.TP_AMB == "1" else cls.WS_NFCE_RET_AUTORIZACAO_HOMOLOG
    
    @classmethod
    def get_ws_consulta(cls):
        """Retorna URL do webservice de consulta protocolo conforme ambiente"""
        return cls.WS_NFCE_CONSULTA_PROD if cls.TP_AMB == "1" else cls.WS_NFCE_CONSULTA_HOMOLOG
    
    @classmethod
    def get_url_qrcode(cls):
        """Retorna URL de consulta do QR Code conforme ambiente"""
        return cls.URL_QRCODE_PROD if cls.TP_AMB == "1" else cls.URL_QRCODE_HOMOLOG