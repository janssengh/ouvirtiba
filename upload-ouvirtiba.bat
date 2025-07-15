@echo off
set /p nome=Informe o nome do arquivo: 
echo O nome escolhido foi '%nome%'.\\
cd C:\Roeland\Roeland\Projetos\Site
git init
git add . 
git config --global user.name "Roeland" 
git config --global user.email "roeland.e.janssen@gmail.com" 
git commit -m "first commit"
git branch -M %nome% 
git remote add origin https://github.com/janssengh/ouvirtiba
git push origin %nome%

