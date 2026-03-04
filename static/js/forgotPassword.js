document.addEventListener('DOMContentLoaded', () => {
  const requestCodeForm = document.getElementById('request-code-form');
  const resetForm = document.getElementById('reset-form');
  const sendCodeBtn = document.getElementById('send-code-btn');
  const changePasswordBtn = document.getElementById('change-password-btn');
  const userInput = document.getElementById('user');
  const codeInput = document.getElementById('code');
  const newPasswordInput = document.getElementById('new_password');
  const confirmPasswordInput = document.getElementById('confirm_password');
  const msg = document.getElementById('msg');

  const showMessage = (text, type) => {
    msg.textContent = text;
    msg.className = `msg ${type}`;
  };

  requestCodeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const user = (userInput.value || '').trim();
    if (!user) {
      showMessage('Ingresa correo o usuario.', 'error');
      return;
    }

    sendCodeBtn.disabled = true;
    try {
      const res = await fetch('/api/forgot-password/request-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.msg || 'No se pudo enviar el codigo.');
      }

      showMessage(data.msg || 'Codigo enviado.', 'success');
      resetForm.classList.remove('hidden');
      codeInput.focus();
    } catch (err) {
      showMessage(err.message || 'Error enviando codigo.', 'error');
    } finally {
      sendCodeBtn.disabled = false;
    }
  });

  resetForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const user = (userInput.value || '').trim();
    const code = (codeInput.value || '').trim();
    const new_password = newPasswordInput.value || '';
    const confirm_password = confirmPasswordInput.value || '';

    if (!user || !code || !new_password || !confirm_password) {
      showMessage('Completa todos los campos.', 'error');
      return;
    }

    changePasswordBtn.disabled = true;
    try {
      const res = await fetch('/api/forgot-password/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user, code, new_password, confirm_password })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.msg || 'No se pudo cambiar la contrasena.');
      }

      showMessage(data.msg || 'Contrasena actualizada.', 'success');
      setTimeout(() => {
        window.location.href = '/inicio/';
      }, 1500);
    } catch (err) {
      showMessage(err.message || 'Error al cambiar contrasena.', 'error');
    } finally {
      changePasswordBtn.disabled = false;
    }
  });
});
