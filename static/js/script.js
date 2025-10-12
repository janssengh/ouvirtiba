document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form');
  const nome = document.getElementById('nome');
  const email = document.getElementById('email');
  const telefone = document.getElementById('telefone');
  const mensagem = document.getElementById('mensagem');
  const alerta = document.getElementById('mensagem-validacao');

  // MÁSCARA DE TELEFONE AO DIGITAR
  telefone.addEventListener('input', function () {
    let valor = telefone.value.replace(/\D/g, '');

    if (valor.length > 11) valor = valor.slice(0, 11);

    if (valor.length <= 10) {
      telefone.value = valor.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
    } else {
      telefone.value = valor.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
    }
  });

  form.addEventListener('submit', function (event) {
    alerta.classList.add('d-none');
    alerta.textContent = '';

    if (!nome.value.trim()) {
      event.preventDefault();
      alerta.textContent = 'Preencha seu Nome completo!';
      alerta.classList.remove('d-none');
      nome.focus();
      return;
    }

    if (!email.validity.valid) {
      event.preventDefault();
      alerta.textContent = 'Digite um e-mail válido!';
      alerta.classList.remove('d-none');
      email.focus();
      return;
    }

    let telefoneValor = telefone.value.replace(/\D/g, '');
    if (telefoneValor.length < 10 || telefoneValor.length > 11) {
      event.preventDefault();
      alerta.textContent = 'Informe um número de telefone válido com DDD e pelo menos 8 dígitos.';
      alerta.classList.remove('d-none');
      telefone.focus();
      return;
    }

    if (!mensagem.value.trim()) {
      event.preventDefault();
      alerta.textContent = 'Escreva sua mensagem!';
      alerta.classList.remove('d-none');
      mensagem.focus();
      return;
    } else if (mensagem.value.trim().length < 20) {
      event.preventDefault();
      alerta.textContent = 'Sua mensagem deve ter no mínimo 20 caracteres.';
      alerta.classList.remove('d-none');
      mensagem.focus();
      return;
    }
  });
});

document.addEventListener("DOMContentLoaded", function () {
  // ✅ Captura o TYPE_ID passado do Flask (usado para produtos)
  const initialTypeId = typeof TYPE_ID_URL !== 'undefined' ? TYPE_ID_URL : 'null';

  const btnCancelar = document.getElementById("btnCancelar");
  if (!btnCancelar) return; // segurança

  btnCancelar.addEventListener("click", function (e) {
    e.preventDefault();

    const confirmar = confirm("Deseja realmente cancelar? As alterações não salvas serão perdidas.");

    if (confirmar) {
      // 🔍 Detecta automaticamente se é uma tela de MARCA (brand_ins.html ou brand_upd.html)
      const isBrandPage = window.location.pathname.includes("/brand/");

      // 🔍 NOVO: Detecta automaticamente se é uma tela de CATEGORIA
      const isCategoryPage = window.location.pathname.includes("/category/");

      // 🔍 NOVO: Detecta automaticamente se é uma tela de COR
      const isColorPage = window.location.pathname.includes("/color/"); //

       // 🔍 NOVO: Detecta automaticamente se é uma tela de TAMANHO
      const isSizePage = window.location.pathname.includes("/size/"); 

      // 🔍 NOVO: Detecta automaticamente se é uma tela de EMBALAGEM
      const isPackagingPage = window.location.pathname.includes("/packaging/"); 

      if (isBrandPage) {
        // Retorna para a lista de marcas
        window.location.href = "/admin/brand/list";
      } else if (isCategoryPage) {
        // Retorna para a lista de categorias
        window.location.href = "/admin/category/list";
      } else if (isColorPage) { //
        // Retorna para a lista de cores
        window.location.href = "/admin/color/list"; //
      } else if (isSizePage) { // <-- NOVO BLOCO
        // Retorna para a lista de tamanhos
        window.location.href = "/admin/size/list";   
      } else if (isPackagingPage) { // <-- NOVO BLOCO
        // Retorna para a lista de embalagens
        window.location.href = "/admin/packaging/list";     
      } else if (initialTypeId && initialTypeId !== "null") {
        // Retorna para a lista filtrada por tipo (produtos)
        window.location.href = `/admin/${initialTypeId}`;
      } else {
        // Padrão de segurança
        window.location.href = "/admin";
      }
    }
  });
});