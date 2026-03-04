document.addEventListener('DOMContentLoaded', () => {
  const config = window.perfilEditarConfig || {};
  const getDataUrl = config.getDataUrl;
  const updateProfileUrl = config.updateProfileUrl;
  const changePasswordUrl = config.changePasswordUrl;

  const profileForm = document.getElementById('profile-form');
  const passwordForm = document.getElementById('password-form');
  const msgBox = document.getElementById('profile-msg');

  const nameInput = document.getElementById('name');
  const lastNameInput = document.getElementById('last_name');
  const usernameInput = document.getElementById('username');
  const emailInput = document.getElementById('email');

  const currentPasswordInput = document.getElementById('current_password');
  const newPasswordInput = document.getElementById('new_password');
  const confirmPasswordInput = document.getElementById('confirm_password');

  const showMsg = (message, type = 'info') => {
    msgBox.textContent = message;
    msgBox.className = `msg ${type}`;
  };

  const loadProfileData = async () => {
    try {
      const response = await fetch(getDataUrl, { method: 'GET' });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'No se pudo cargar el perfil.');
      }

      const user = data.user || {};
      nameInput.value = user.name || '';
      lastNameInput.value = user.last_name || '';
      usernameInput.value = user.username || '';
      emailInput.value = user.email || '';
    } catch (error) {
      showMsg(error.message || 'Error al cargar perfil.', 'error');
    }
  };

  profileForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const payload = {
      name: (nameInput.value || '').trim(),
      last_name: (lastNameInput.value || '').trim()
    };

    if (!payload.name || !payload.last_name) {
      showMsg('Nombre y apellido son obligatorios.', 'error');
      return;
    }

    try {
      const response = await fetch(updateProfileUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'No se pudo guardar el perfil.');
      }
      showMsg(data.msg || 'Perfil actualizado correctamente.', 'success');
    } catch (error) {
      showMsg(error.message || 'Error al guardar perfil.', 'error');
    }
  });

  passwordForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const payload = {
      current_password: currentPasswordInput.value || '',
      new_password: newPasswordInput.value || '',
      confirm_password: confirmPasswordInput.value || ''
    };

    try {
      const response = await fetch(changePasswordUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'No se pudo actualizar la contrasena.');
      }

      currentPasswordInput.value = '';
      newPasswordInput.value = '';
      confirmPasswordInput.value = '';
      showMsg(data.msg || 'Contrasena actualizada correctamente.', 'success');
    } catch (error) {
      showMsg(error.message || 'Error al actualizar contrasena.', 'error');
    }
  });

  loadProfileData();
});
