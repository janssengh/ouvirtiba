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
