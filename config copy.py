
class NFeConfig:
    UF = "SC"
    TP_AMB = "2"  # 2 = Homologação
    IBGE_CITY_CODE = "4209102" # Código do Município (IBGE) Emitente = Joinville
    IBGE_CITY_CODE_CLI = "4205407" # Código do Município (IBGE) Cliente = Itajaí
    CRT = "1" # Código de Regime Tributário (clínicas, comercios locais, pequenas empresas)
    NATOP = "VENDA DE MERCADORIA"
    MOD = "65" # Modelo NF
    TP_NF ="1" # 1=Saída
    ID_DEST = "1" # 1=Operação interna, 2=Interestadual, 3=Exterior
    TP_IMP = "4" # 4=DANFE NFC-e em papel
    TP_EMIS = "1" # 1=Emissão normal
    FIN_NFE = "1" # 1=NF-e normal
    IND_FINAL = "1" # 1=Consumidor final
    IND_PRES = "1" # 1=Operação presencial
    PROC_EMI = "0" # 0=Emissão com aplicativo do contribuinte
    VER_PROC =  "Ouvirtiba 1.0"
    XFANT = "OUVRTIBA APARELHOS AUDITIVOS"
    CPAIS = "1058"
    XPAIS = "BRASIL"
    IND_IE_DEST = "9" # 9=Não Contribuinte

    # Itens
    CEAN = "SEM GTIN"
    UCOM = "UN"
    IND_TOT = "1" # 1=Compõe total da NF-e
    TX_TRIB = "0.15" # Taxa tributação imposto
    PIS_CST = "99" # 99=Outras operações
    COFINS_CST = "99" # 99=Outras operações

    # Transporte
    MOD_FRETE = "9" # 9=Sem frete

    # Pagamento
    IND_PAG = "0" # 0=Pagamento à Vista
    T_PAG = "01" # 01=Dinheiro

    # Informações adicionais
    INF_ADIC_TXT_1 = "DOCUMENTO EMITIDO POR ME OU EPP OPTANTE PELO SIMPLES NACIONAL. "
    INF_ADIC_TXT_2 = "NAO GERA DIREITO A CREDITO FISCAL DE ICMS, ISS E IPI."

    CSC_ID = "000001" 
    CSC_TOKEN = "1A2B3C4D5E6F7G8H9I0J"
    AMBIENTE = "2" # 1 = produção, 2 = homologação

    URL_QRCODE_HOMOLOG = "https://sat.sef.sc.gov.br/nfce/consulta"
    URL_QRCODE_PROD = "https://sat.sef.sc.gov.br/nfce/consulta"


    CNPJ_EMITENTE = "56154376000105"
    IE_EMITENTE = "263067041"
    RAZAO_SOCIAL = "JANSSEN APARELHOS AUDITIVOS LTDA"

    CERT_PFX_PATH = "admin/nfe/certs/JANSSEN APARELHOS AUDITIVOS LTDA56154376000105.pfx"
    CERT_PFX_PASSWORD = "123456"

    NAMESPACE = "http://www.portalfiscal.inf.br/nfe"


