document.addEventListener('DOMContentLoaded', () => {
  const config = window.crearUsuarioConfig || {};
  const perfilDataUrl = config.perfilDataUrl;
  const createUserUrl = config.createUserUrl;

  const form = document.getElementById('create-user-form');
  const msgBox = document.getElementById('create-user-msg');

  const nameInput = document.getElementById('name');
  const lastNameInput = document.getElementById('last_name');
  const usernameInput = document.getElementById('username');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const rolInput = document.getElementById('rol');

  const showMsg = (message, type = 'info') => {
    msgBox.textContent = message;
    msgBox.className = `msg ${type}`;
  };

  const verifyAdminAccess = async () => {
    try {
      const response = await fetch(perfilDataUrl, { method: 'GET' });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'No se pudo validar el usuario actual.');
      }

      const rol = String(data.user?.rol || '').toLowerCase();
      if (rol !== 'administrador') {
        showMsg('No tienes permisos para crear usuarios.', 'error');
        form.querySelectorAll('input, select, button').forEach((el) => {
          el.disabled = true;
        });
      }
    } catch (error) {
      showMsg(error.message || 'Error validando permisos.', 'error');
      form.querySelectorAll('input, select, button').forEach((el) => {
        el.disabled = true;
      });
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const payload = {
      name: (nameInput.value || '').trim(),
      last_name: (lastNameInput.value || '').trim(),
      username: (usernameInput.value || '').trim(),
      email: (emailInput.value || '').trim(),
      password: passwordInput.value || '',
      rol: (rolInput.value || '').trim()
    };

    if (!payload.name || !payload.last_name || !payload.username || !payload.email || !payload.password || !payload.rol) {
      showMsg('Completa todos los campos.', 'error');
      return;
    }

    try {
      const response = await fetch(createUserUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'No se pudo crear el usuario.');
      }

      showMsg(data.msg || 'Usuario creado correctamente.', 'success');
      form.reset();
      rolInput.value = 'administrador';
    } catch (error) {
      showMsg(error.message || 'Error creando usuario.', 'error');
    }
  });

  verifyAdminAccess();
});
