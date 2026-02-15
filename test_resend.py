#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 SCRIPT DE TESTE - INTEGRAÇÃO RESEND
Ouvirtiba Aparelhos Auditivos

Este script testa se a configuração do Resend está funcionando corretamente.

COMO USAR:
    python test_resend.py

O QUE ELE FAZ:
    1. Verifica se as variáveis de ambiente estão configuradas
    2. Testa a conexão com a API do Resend
    3. Envia um email de teste
    4. Mostra o resultado e o link para ver no dashboard
"""

import os
import sys

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Verificar se o pacote resend está instalado
try:
    import resend
except ImportError:
    print("\n" + "="*60)
    print("❌ ERRO: Pacote 'resend' não está instalado!")
    print("="*60)
    print("\n📦 Para instalar, execute:")
    print("   pip install resend")
    print("\n")
    sys.exit(1)


def imprimir_linha(char="=", length=60):
    """Imprime uma linha decorativa"""
    print(char * length)


def imprimir_secao(titulo):
    """Imprime um título de seção"""
    print("\n")
    imprimir_linha()
    print(f"  {titulo}")
    imprimir_linha()


def verificar_variaveis():
    """Verifica se as variáveis de ambiente estão configuradas"""
    imprimir_secao("🔍 VERIFICANDO CONFIGURAÇÃO")
    
    # Obter variáveis
    api_key = os.getenv('RESEND_API_KEY')
    email_from = os.getenv('EMAIL_FROM', 'contato@ouvirtiba.com.br')
    email_to = os.getenv('EMAIL_TO', 'roeland.e.janssen@gmail.com')
    
    # Status das variáveis
    todas_ok = True
    
    # Verificar API Key
    if not api_key:
        print("❌ RESEND_API_KEY: NÃO ENCONTRADA")
        print("   Adicione no arquivo .env: RESEND_API_KEY=re_sua_chave_aqui")
        todas_ok = False
    else:
        # Mostrar apenas os primeiros caracteres da chave
        chave_oculta = api_key[:15] + "..." if len(api_key) > 15 else api_key
        print(f"✅ RESEND_API_KEY: {chave_oculta} (OK)")
    
    # Verificar EMAIL_FROM
    if not email_from:
        print("❌ EMAIL_FROM: NÃO ENCONTRADO")
        todas_ok = False
    else:
        print(f"✅ EMAIL_FROM: {email_from}")
        if "@ouvirtiba.com.br" not in email_from:
            print("   ⚠️  AVISO: Email não é @ouvirtiba.com.br")
            print("   Seu domínio está verificado, use emails @ouvirtiba.com.br")
    
    # Verificar EMAIL_TO
    if not email_to:
        print("❌ EMAIL_TO: NÃO ENCONTRADO")
        todas_ok = False
    else:
        print(f"✅ EMAIL_TO: {email_to}")
    
    print()
    
    if not todas_ok:
        print("❌ Corrija as configurações no arquivo .env antes de continuar.")
        return None
    
    return {
        'api_key': api_key,
        'email_from': email_from,
        'email_to': email_to
    }


def enviar_email_teste(config):
    """Envia um email de teste usando o Resend"""
    imprimir_secao("📧 ENVIANDO EMAIL DE TESTE")
    
    # Configurar API Key
    resend.api_key = config['api_key']
    
    print(f"De:   {config['email_from']}")
    print(f"Para: {config['email_to']}")
    print("\n📤 Enviando...")
    
    try:
        # Montar corpo do email em HTML
        corpo_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                .status { background: #4CAF50; color: white; padding: 15px; border-radius: 5px; 
                         text-align: center; margin: 20px 0; }
                .info { background: white; padding: 15px; border-left: 4px solid #667eea; margin: 10px 0; }
                .footer { text-align: center; color: #666; margin-top: 20px; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Email de Teste</h1>
                    <p>Integração Resend - Ouvirtiba</p>
                </div>
                <div class="content">
                    <div class="status">
                        <strong>✅ Integração funcionando corretamente!</strong>
                    </div>
                    
                    <h2>Informações do Teste:</h2>
                    
                    <div class="info">
                        <strong>🏢 Sistema:</strong> Ouvirtiba Aparelhos Auditivos<br>
                        <strong>📧 Serviço:</strong> Resend API<br>
                        <strong>🎯 Objetivo:</strong> Validar configuração de envio de emails
                    </div>
                    
                    <h3>O que isso significa?</h3>
                    <p>Se você recebeu este email, significa que:</p>
                    <ul>
                        <li>✅ A API Key do Resend está configurada corretamente</li>
                        <li>✅ O domínio ouvirtiba.com.br está verificado</li>
                        <li>✅ Os emails estão sendo enviados com sucesso</li>
                        <li>✅ O formulário de contato do site está pronto para uso</li>
                    </ul>
                    
                    <h3>Próximos passos:</h3>
                    <ol>
                        <li>Testar o formulário localmente em http://localhost:5000/contato</li>
                        <li>Configurar as variáveis de ambiente no servidor de produção</li>
                        <li>Fazer deploy e testar em produção</li>
                    </ol>
                    
                    <div class="footer">
                        <p>Este é um email automático de teste do sistema Ouvirtiba.</p>
                        <p>Para ver detalhes técnicos, acesse: 
                           <a href="https://resend.com/emails">Dashboard do Resend</a>
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Parâmetros do email
        params = {
            "from": f"Ouvirtiba - Teste <{config['email_from']}>",
            "to": [config['email_to']],
            "subject": "✅ Teste de Integração Resend - Ouvirtiba",
            "html": corpo_html,
        }
        
        # Enviar email
        response = resend.Emails.send(params)
        
        # Sucesso!
        print("\n" + "="*60)
        print("✅ EMAIL ENVIADO COM SUCESSO!")
        print("="*60)
        
        email_id = response.get('id', 'N/A')
        print(f"\n📊 Detalhes do envio:")
        print(f"   ID do Email: {email_id}")
        print(f"   Remetente: {config['email_from']}")
        print(f"   Destinatário: {config['email_to']}")
        
        print(f"\n🔍 Acompanhe o email no dashboard:")
        print(f"   https://resend.com/emails")
        
        print(f"\n📬 Verifique sua caixa de entrada:")
        print(f"   O email deve chegar em alguns segundos")
        print(f"   Se não aparecer na caixa de entrada, verifique o SPAM")
        
        return True
        
    except resend.exceptions.ResendError as e:
        print("\n" + "="*60)
        print("❌ ERRO AO ENVIAR EMAIL (Resend Error)")
        print("="*60)
        print(f"\nMensagem de erro: {str(e)}")
        
        # Sugestões baseadas no erro
        erro_str = str(e).lower()
        print("\n💡 Possíveis causas:")
        
        if "api key" in erro_str or "unauthorized" in erro_str:
            print("   • API Key inválida ou incorreta")
            print("   • Verifique se a chave está completa no .env")
            print("   • Gere uma nova chave em: https://resend.com/api-keys")
        
        elif "domain" in erro_str or "verified" in erro_str:
            print("   • O domínio não está verificado")
            print("   • Verifique em: https://resend.com/domains")
            print("   • Use um email @ouvirtiba.com.br como remetente")
        
        elif "rate limit" in erro_str:
            print("   • Limite de envios atingido")
            print("   • Aguarde alguns minutos e tente novamente")
        
        else:
            print("   • Verifique a conexão com a internet")
            print("   • Verifique se o Resend está online")
            print("   • Consulte: https://resend.com/docs")
        
        return False
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERRO INESPERADO")
        print("="*60)
        print(f"\nTipo: {type(e).__name__}")
        print(f"Mensagem: {str(e)}")
        
        # Traceback completo para debug
        import traceback
        print("\n📋 Detalhes técnicos:")
        print(traceback.format_exc())
        
        return False


def main():
    """Função principal do script"""
    imprimir_secao("🚀 TESTE DE INTEGRAÇÃO RESEND - OUVIRTIBA")
    
    print("\n📝 Este script irá:")
    print("   1. Verificar se as variáveis de ambiente estão configuradas")
    print("   2. Testar a conexão com a API do Resend")
    print("   3. Enviar um email de teste para o endereço configurado")
    
    # Verificar configuração
    config = verificar_variaveis()
    
    if not config:
        print("\n❌ Teste abortado. Corrija os erros acima e tente novamente.\n")
        sys.exit(1)
    
    # Perguntar se deseja continuar
    imprimir_linha("-")
    resposta = input("\n📧 Deseja enviar um email de teste? (s/n): ").lower().strip()
    
    if resposta not in ['s', 'sim', 'y', 'yes']:
        print("\n✋ Teste cancelado pelo usuário.\n")
        sys.exit(0)
    
    # Enviar email de teste
    sucesso = enviar_email_teste(config)
    
    # Resultado final
    print("\n")
    imprimir_linha()
    
    if sucesso:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        imprimir_linha()
        print("\n📋 Próximos passos:")
        print("   1. Verifique se o email chegou em sua caixa de entrada")
        print("   2. Teste o formulário localmente: http://localhost:5000/contato")
        print("   3. Configure as variáveis no servidor de produção")
        print("   4. Faça o deploy e teste em produção")
        print("\n✨ Sua migração para o Resend está completa!\n")
        sys.exit(0)
    else:
        print("❌ TESTE FALHOU")
        imprimir_linha()
        print("\n📋 O que fazer:")
        print("   1. Verifique os erros acima")
        print("   2. Corrija as configurações no .env")
        print("   3. Execute o teste novamente")
        print("\n❓ Precisa de ajuda? Consulte o arquivo COMO_COPIAR_API_KEY.md\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✋ Teste interrompido pelo usuário (Ctrl+C)\n")
        sys.exit(0)
    except Exception as e:
        print("\n\n❌ ERRO CRÍTICO:")
        print(f"   {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)