Atualizar Banco de Dados Postgresql:
PgAdmin 4

Salvar no github (https://github.com/janssengh/ouvirtiba):
bash
git add . 
git commit -m "Inclusão do gerenciamento pedidos em pdf"
git push origin master

Atualizar Render (https://dashboard.render.com/web/srv-d26hb715pdvs73a2ut8g/deploys/dep-d526tge3jp1c73btdm70):
Entrar o render/github
ouvirtiba
manual deploy/deploy latest commit

Atualizar Supabase ():
github
Projects: ouvirtiba
Databases
Schema ouvirtiba
Sql Editor
ALTER TABLE ouvirtiba.customer_request_item 
ADD COLUMN serialnumber VARCHAR(15);
Run
UPDATE ouvirtiba.customer_request_item 
SET serialnumber = '2544X1CP1'
WHERE id = 94;
Run