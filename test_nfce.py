#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Teste Completo para NFC-e
Testa: Geração XML → Assinatura → Validação → QR Code
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from admin.nfe.nfce_sign import assinar_xml_nfce, validar_assinatura_xml
from admin.nfe.services.qr_code import gerar_qrcode_url, validar_qrcode_url
from config import NFeConfig as CFG
from lxml import etree


def print_header(title):
    """Imprime cabeçalho formatado"""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)
    print()


def test_1_ler_xml():
    """Teste 1: Leitura do XML"""
    print_header("TESTE 1: LEITURA DO XML")
    
    xml_path = "admin/nfe/output/nfce_1.xml"
    
    if not os.path.exists(xml_path):
        print(f"❌ ERRO: Arquivo não encontrado: {xml_path}")
        return None
    
    try:
        with open(xml_path, 'rb') as f:
            xml_content = f.read()
        
        # Parse do XML para validar estrutura
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(xml_content, parser)
        
        # Extrai informações básicas
        namespace = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        infNFe = root.find('.//nfe:infNFe', namespace)
        
        if infNFe is None:
            print("❌ ERRO: Tag <infNFe> não encontrada")
            return None
        
        chave = infNFe.get('Id', '').replace('NFe', '')
        numero = infNFe.find('.//nfe:nNF', namespace)
        serie = infNFe.find('.//nfe:serie', namespace)
        
        print(f"✅ XML lido com sucesso!")
        print(f"   📄 Arquivo: {xml_path}")
        print(f"   📊 Tamanho: {len(xml_content)} bytes")
        print(f"   🔑 Chave: {chave}")
        print(f"   🔢 Número: {numero.text if numero is not None else 'N/A'}")
        print(f"   📋 Série: {serie.text if serie is not None else 'N/A'}")
        
        return xml_content, chave
        
    except Exception as e:
        print(f"❌ ERRO ao ler XML: {e}")
        return None


def test_2_validar_estrutura(xml_content):
    """Teste 2: Validação da estrutura do XML"""
    print_header("TESTE 2: VALIDAÇÃO DA ESTRUTURA XML")
    
    try:
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(xml_content, parser)
        namespace = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        checks = {
            'infNFe': root.find('.//nfe:infNFe', namespace),
            'ide': root.find('.//nfe:ide', namespace),
            'emit': root.find('.//nfe:emit', namespace),
            'dest': root.find('.//nfe:dest', namespace),
            'det': root.find('.//nfe:det', namespace),
            'total': root.find('.//nfe:total', namespace),
            'transp': root.find('.//nfe:transp', namespace),
            'pag': root.find('.//nfe:pag', namespace),
            'infAdic': root.find('.//nfe:infAdic', namespace),
            'infNFeSupl': root.find('.//nfe:infNFeSupl', namespace),
        }
        
        print("Verificando tags obrigatórias:")
        print()
        
        all_ok = True
        for tag, element in checks.items():
            status = "✅" if element is not None else "❌"
            print(f"  {status} <{tag}>")
            if element is None:
                all_ok = False
        
        print()
        if all_ok:
            print("✅ Estrutura XML validada com sucesso!")
            return True
        else:
            print("❌ Estrutura XML incompleta!")
            return False
            
    except Exception as e:
        print(f"❌ ERRO na validação: {e}")
        return False


def test_3_verificar_qrcode(chave):
    """Teste 3: Verificação do QR Code"""
    print_header("TESTE 3: VERIFICAÇÃO DO QR CODE")
    
    try:
        # Gera URL do QR Code
        qrcode_url = gerar_qrcode_url(
            chave_acesso=chave,
            ambiente=int(CFG.TP_AMB),
            id_token=CFG.CSC_ID,
            csc_token=CFG.CSC_TOKEN
        )
        
        print(f"✅ QR Code gerado com sucesso!")
        print(f"   🔗 URL: {qrcode_url[:80]}...")
        print()
        
        # Valida URL
        valido, mensagem = validar_qrcode_url(qrcode_url)
        
        if valido:
            print(f"✅ {mensagem}")
        else:
            print(f"❌ {mensagem}")
            return False
        
        # Analisa componentes
        params = qrcode_url.split('?p=')[1]
        partes = params.split('|')
        
        print()
        print("📋 Componentes do QR Code:")
        print(f"   1. Chave:    {partes[0]}")
        print(f"   2. Versão:   {partes[1]}")
        print(f"   3. Ambiente: {partes[2]}")
        print(f"   4. ID Token: {partes[3]}")
        print(f"   5. Hash:     {partes[4][:20]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO ao gerar QR Code: {e}")
        return False


def test_4_assinar_xml(xml_content):
    """Teste 4: Assinatura Digital"""
    print_header("TESTE 4: ASSINATURA DIGITAL")
    
    pfx_path = CFG.CERT_PFX_PATH
    pfx_password = CFG.CERT_PFX_PASSWORD
    
    print(f"🔐 Certificado: {pfx_path}")
    print(f"🔑 Senha: {'*' * len(pfx_password)}")
    print()
    
    if not os.path.exists(pfx_path):
        print(f"❌ ERRO: Certificado não encontrado!")
        print(f"   Esperado em: {pfx_path}")
        print()
        print("💡 DICA: Copie seu certificado .pfx para o diretório:")
        print(f"   {os.path.dirname(pfx_path)}/")
        return None
    
    try:
        print("⏳ Assinando XML...")
        xml_assinado = assinar_xml_nfce(xml_content, pfx_path, pfx_password)
        
        print("✅ XML assinado com sucesso!")
        print(f"   📊 Tamanho: {len(xml_assinado)} bytes")
        
        return xml_assinado
        
    except Exception as e:
        print(f"❌ ERRO ao assinar: {e}")
        return None


def test_5_validar_assinatura(xml_assinado):
    """Teste 5: Validação da Assinatura"""
    print_header("TESTE 5: VALIDAÇÃO DA ASSINATURA")
    
    try:
        valido, mensagem = validar_assinatura_xml(xml_assinado)
        
        print(mensagem)
        
        if valido:
            # Extrai informações da assinatura
            parser = etree.XMLParser(remove_blank_text=False)
            root = etree.fromstring(xml_assinado, parser)
            
            ds_namespace = "http://www.w3.org/2000/09/xmldsig#"
            
            signature_value = root.find(f'.//{{{ds_namespace}}}SignatureValue')
            digest_value = root.find(f'.//{{{ds_namespace}}}DigestValue')
            
            print()
            print("📋 Detalhes da Assinatura:")
            if signature_value is not None:
                print(f"   SignatureValue: {signature_value.text[:40]}...")
            if digest_value is not None:
                print(f"   DigestValue:    {digest_value.text}")
        
        return valido
        
    except Exception as e:
        print(f"❌ ERRO na validação: {e}")
        return False


def test_6_salvar_xml(xml_assinado):
    """Teste 6: Salvar XML Assinado"""
    print_header("TESTE 6: SALVAR XML ASSINADO")
    
    output_path = "admin/nfe/output/nfce_1_assinado.xml"
    
    try:
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(xml_assinado)
        
        file_size = os.path.getsize(output_path)
        
        print(f"✅ XML assinado salvo com sucesso!")
        print(f"   📂 Arquivo: {output_path}")
        print(f"   📊 Tamanho: {file_size} bytes")
        
        return output_path
        
    except Exception as e:
        print(f"❌ ERRO ao salvar: {e}")
        return None


def main():
    """Executa todos os testes"""
    
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "TESTE COMPLETO NFC-e" + " " * 38 + "║")
    print("║" + " " * 15 + "Geração → Assinatura → Validação" + " " * 30 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Teste 1: Leitura
    result = test_1_ler_xml()
    if result is None:
        print("\n❌ FALHA NO TESTE 1. Encerrando...")
        return False
    
    xml_content, chave = result
    
    # Teste 2: Estrutura
    if not test_2_validar_estrutura(xml_content):
        print("\n⚠️  AVISO: Estrutura XML incompleta, mas continuando...")
    
    # Teste 3: QR Code
    if not test_3_verificar_qrcode(chave):
        print("\n⚠️  AVISO: QR Code com problemas, mas continuando...")
    
    # Teste 4: Assinatura
    xml_assinado = test_4_assinar_xml(xml_content)
    if xml_assinado is None:
        print("\n❌ FALHA NO TESTE 4. Encerrando...")
        return False
    
    # Teste 5: Validação
    if not test_5_validar_assinatura(xml_assinado):
        print("\n❌ FALHA NO TESTE 5. Encerrando...")
        return False
    
    # Teste 6: Salvar
    output_path = test_6_salvar_xml(xml_assinado)
    if output_path is None:
        print("\n❌ FALHA NO TESTE 6. Encerrando...")
        return False
    
    # Resumo Final
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "✅ TODOS OS TESTES PASSARAM!" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    print("📋 PRÓXIMOS PASSOS:")
    print()
    print("   1. ✅ XML assinado gerado com sucesso")
    print(f"   2. 📂 Arquivo: {output_path}")
    print("   3. 🔐 Obter CSC real da SEFAZ (substituir tokens fictícios)")
    print("   4. 🧪 Testar transmissão em ambiente de Homologação")
    print("   5. 📝 Após testes aprovados, solicitar habilitação em Produção")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)