const validar_formulario = () => {
    const descricao = document.getElementById('name').value;
    const paginas = document.getElementById('pages').value;

    if (!descricao) {     
        alerta_erro('Faltou campo descrição!')
        return false;
    } else if (!paginas || paginas <= 4){
        alerta_erro('Qtde de Páginas inválida ou não preenchida!');
        return false;    
    }
    return true;
}
