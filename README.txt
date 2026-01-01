Atualizar Banco de Dados Postgresql:
PgAdmin 4

Atualizar requirement.txt:
pip freeze > requirements.txt


Salvar no github (https://github.com/janssengh/ouvirtiba):
bash
git add . 
git commit -m "Alteração models invoice para number de sting para integer"
git push origin master

Atualizar Render (https://dashboard.render.com/web/srv-d26hb715pdvs73a2ut8g/deploys/dep-d526tge3jp1c73btdm70):
Entrar o render/github
ouvirtiba
manual deploy/deploy latest commit

Para manter ativo o Render Free, foi usado UptimeRobot.
Para manter ativo o SUPABASE Free, incluso no app.py o ENDPOINT 


Atualizar Supabase ():
github
Projects: ouvirtiba
Databases
Schema ouvirtiba
Sql Editor

Run
UPDATE ouvirtiba.customer_request_item 
SET serialnumber = '2544X1CP1'
WHERE id = 94;
Run


# Guia de Debug no Render - Erro na Geração de PDF

## 1. Verificar Logs no Render

1. Acesse o dashboard do Render: https://dashboard.render.com/web/srv-d26hb715pdvs73a2ut8g
2. Clique na aba **"Logs"**
3. Procure por mensagens de erro que começam com:
   - `ERROR`
   - `Erro ao gerar PDF`
   - `wkhtmltopdf`
   - `Traceback`

## 2. Provável Causa: wkhtmltopdf não instalado

O erro mais comum é que o **wkhtmltopdf** não está instalado no servidor Render.

### Solução: Adicionar wkhtmltopdf ao projeto

**Opção A: Usar arquivo `packages.txt` (RECOMENDADO)**

Crie um arquivo chamado `packages.txt` na raiz do projeto com:

```
wkhtmltopdf
```

**Opção B: Adicionar ao `requirements.txt`**

Adicione ao final do seu `requirements.txt`:

```
# Para geração de PDF
pdfkit==1.0.0
```

E crie um arquivo `render.yaml` na raiz:

```yaml
services:
  - type: web
    name: ouvirtiba
    env: python
    buildCommand: |
      apt-get update
      apt-get install -y wkhtmltopdf
      pip install -r requirements.txt
    startCommand: gunicorn app:app
```

**Opção C: Usar Buildpack**

No dashboard do Render:
1. Vá em **Settings**
2. Em **Build Command**, adicione:
```bash
apt-get update && apt-get install -y wkhtmltopdf && pip install -r requirements.txt
```

## 3. Verificar Permissões da Pasta

O servidor precisa ter permissão para criar a pasta `static/pdf`. Adicione ao seu código de inicialização:

```python
import os
pdf_folder = 'static/pdf'
if not os.path.exists(pdf_folder):
    os.makedirs(pdf_folder, exist_ok=True)
```

## 4. Alternativa: Usar biblioteca Python pura

Se o wkhtmltopdf continuar dando problemas, considere usar uma biblioteca Python pura:

```bash
pip install weasyprint
```

Depois substitua o pdfkit por WeasyPrint no código.

## 5. Comandos para Debug

Após fazer deploy, acesse o Shell no Render e execute:

```bash
which wkhtmltopdf
wkhtmltopdf --version
ls -la static/
```

## 6. Logs Detalhados

Com o código atualizado que forneci, você verá logs como:

```
INFO: Gerando PDF para pedido 20241219123456
INFO: Template renderizado com sucesso
INFO: Caminho do PDF: static/pdf/pedido-joao.pdf
INFO: wkhtmltopdf encontrado em: /usr/bin/wkhtmltopdf
INFO: Iniciando geração do PDF...
INFO: PDF gerado com sucesso em: static/pdf/pedido-joao.pdf
```

Ou mensagens de erro específicas que indicarão o problema exato.

## 7. Checklist de Verificação

- [ ] wkhtmltopdf está instalado?
- [ ] A pasta `static/pdf` existe e tem permissão de escrita?
- [ ] O template `order/order_pdf.html` existe e está correto?
- [ ] As variáveis de sessão estão configuradas corretamente?
- [ ] Os logs mostram qual linha específica está falhando?

## 8. Próximos Passos

1. **Atualize o código** com a versão que forneci (tem logging detalhado)
2. **Crie o arquivo `packages.txt`** com `wkhtmltopdf`
3. **Faça commit e push** para o GitHub
4. **Aguarde o deploy** no Render
5. **Verifique os logs** para ver mensagens específicas
6. **Teste novamente** a geração do PDF