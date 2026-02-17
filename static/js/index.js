// static/js/index.js
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  const msg = document.getElementById('msg');
  const togglePassword = document.getElementById('togglePassword');
  const passwordInput = document.getElementById('password');
  const loginBtn = document.querySelector('.login-btn');
  const welcomeModal = document.getElementById('welcomeModal');

  // Alternar visibilidad de contraseña
  togglePassword.addEventListener('click', () => {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
    
    // Cambiar icono
    const icon = togglePassword.querySelector('i');
    icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
  });

  // Manejo del formulario de login
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Limpiar mensajes anteriores
    msg.textContent = '';
    msg.className = 'msg';
    
    // Obtener valores
    const user = document.getElementById('user').value.trim();
    const password = document.getElementById('password').value;

    // Validación básica
    if (!user || !password) {
      showMessage('Por favor, completa todos los campos', 'error');
      return;
    }

    // Mostrar estado de carga
    loginBtn.classList.add('loading');

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ user, password })
      });

      const data = await res.json();
      
      if (res.ok) {
        // Mostrar mensaje de éxito
        showMessage('Inicio de sesión exitoso', 'success');
        
        // Mostrar modal de bienvenida
        showWelcomeModal();
        
        // Redirigir después de 3 segundos (mismo tiempo que la animación de la barra)
        setTimeout(() => {
          window.location = '/apps_operaciones/';
        }, 3000);
      } else {
        showMessage(data.msg || 'Error en el inicio de sesión', 'error');
      }
    } catch (err) {
      console.error(err);
      showMessage('Error de conexión. Inténtalo de nuevo.', 'error');
    } finally {
      // Quitar estado de carga
      loginBtn.classList.remove('loading');
    }
  });

  // Función para mostrar mensajes
  function showMessage(text, type) {
    msg.textContent = text;
    msg.className = `msg ${type}`;
    
    // Auto-ocultar mensajes de éxito después de 5 segundos
    if (type === 'success') {
      setTimeout(() => {
        msg.textContent = '';
        msg.className = 'msg';
      }, 5000);
    }
  }

  // Función para mostrar el modal de bienvenida
  function showWelcomeModal() {
    welcomeModal.classList.add('show');
    
    // Reiniciar la animación de la barra de progreso
    const progressBar = document.querySelector('.loader-progress');
    progressBar.style.animation = 'none';
    setTimeout(() => {
      progressBar.style.animation = 'loading 3s linear forwards';
    }, 10);
  }

  // Efectos de entrada con teclado
  const inputs = document.querySelectorAll('input');
  inputs.forEach(input => {
    // Efecto al enfocar
    input.addEventListener('focus', () => {
      input.parentElement.classList.add('focused');
    });
    
    // Efecto al perder el foco
    input.addEventListener('blur', () => {
      if (!input.value) {
        input.parentElement.classList.remove('focused');
      }
    });
    
    // Efecto de escritura
    input.addEventListener('input', () => {
      if (input.value) {
        input.parentElement.classList.add('has-value');
      } else {
        input.parentElement.classList.remove('has-value');
      }
    });
  });
});