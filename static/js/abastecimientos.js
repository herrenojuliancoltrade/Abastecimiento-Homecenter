// abastecimientos.js - Efectos premium mejorados
(() => {
  // --------------------------
  // Utilities
  // --------------------------
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  // --------------------------
  // Sistema de Partículas para el fondo
  // --------------------------
  function initParticleSystem() {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let particles = [];
    let animationId;

    // Configuración de partículas
    const particleCount = 50;
    const colors = [
      'rgba(108, 92, 231, 0.3)',   // primary
      'rgba(0, 184, 148, 0.3)',    // success
      'rgba(116, 185, 255, 0.3)',  // info
      'rgba(253, 203, 110, 0.3)',  // warning
      'rgba(232, 67, 147, 0.3)'    // danger
    ];

    function resizeCanvas() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }

    function createParticles() {
      particles = [];
      for (let i = 0; i < particleCount; i++) {
        particles.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: Math.random() * 3 + 1,
          speedX: (Math.random() - 0.5) * 0.5,
          speedY: (Math.random() - 0.5) * 0.5,
          color: colors[Math.floor(Math.random() * colors.length)],
          opacity: Math.random() * 0.5 + 0.1
        });
      }
    }

    function animateParticles() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach(particle => {
        // Actualizar posición
        particle.x += particle.speedX;
        particle.y += particle.speedY;
        
        // Rebote en los bordes
        if (particle.x < 0 || particle.x > canvas.width) particle.speedX *= -1;
        if (particle.y < 0 || particle.y > canvas.height) particle.speedY *= -1;
        
        // Dibujar partícula
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = particle.color;
        ctx.globalAlpha = particle.opacity;
        ctx.fill();
      });
      
      ctx.globalAlpha = 1;
      animationId = requestAnimationFrame(animateParticles);
    }

    // Inicializar
    window.addEventListener('resize', () => {
      resizeCanvas();
      createParticles();
    });

    resizeCanvas();
    createParticles();
    animateParticles();

    // Limpiar al salir
    window.addEventListener('beforeunload', () => {
      if (animationId) cancelAnimationFrame(animationId);
    });
  }

  // --------------------------
  // CONFETTI mejorado
  // --------------------------
  const canvas = document.getElementById('confetti-canvas');
  const ctx = canvas && canvas.getContext ? canvas.getContext('2d') : null;
  let confettiAnim = null;
  
  function resizeCanvas() {
    if (!canvas) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function launchConfetti(count = 60, duration = 1200) {
    if (!ctx || !canvas) return;
    
    const particles = [];
    const t0 = performance.now();
    const colors = [
      'var(--primary)', 'var(--success)', 'var(--info)', 
      'var(--warning)', 'var(--danger)'
    ];

    for (let i = 0; i < count; i++) {
      particles.push({
        x: canvas.width / 2 + (Math.random() - 0.5) * 300,
        y: canvas.height / 2 + (Math.random() - 0.5) * 100,
        vx: (Math.random() - 0.5) * 8,
        vy: - (Math.random() * 8 + 3),
        size: Math.random() * 10 + 8,
        rot: Math.random() * Math.PI * 2,
        vrot: (Math.random() - 0.5) * 0.4,
        color: colors[Math.floor(Math.random() * colors.length)],
        shape: Math.random() > 0.5 ? 'circle' : 'rect',
        opacity: 1
      });
    }
    
    canvas.style.opacity = '1';

    function frame(now) {
      const dt = now - t0;
      const progress = dt / duration;
      
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.15; // gravity
        p.rot += p.vrot;
        p.opacity = 1 - progress;
        
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.globalAlpha = p.opacity;
        ctx.fillStyle = p.color;
        
        if (p.shape === 'circle') {
          ctx.beginPath();
          ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
        }
        
        ctx.restore();
      });
      
      if (dt < duration) {
        confettiAnim = requestAnimationFrame(frame);
      } else {
        cancelAnimationFrame(confettiAnim);
        confettiAnim = null;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        canvas.style.opacity = '0';
      }
    }
    
    confettiAnim = requestAnimationFrame(frame);
  }

  // --------------------------
  // Modal system mejorado
  // --------------------------
  const openModal = (modal) => {
    modal.setAttribute('aria-hidden', 'false');
    modal._prevFocus = document.activeElement;
    
    // Enfocar el primer elemento interactivo
    const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable) focusable.focus();
    
    document.documentElement.style.overflow = 'hidden';
    modal.classList.add('modal-opened');

    // Efectos de entrada
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
      modalContent.style.animation = 'modalSlideIn 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
    }

    // Confetti mejorado
    launchConfetti(80, 1500);

    // Trap de foco
    modal.addEventListener('keydown', trapListener);
  };

  const closeModal = (modal) => {
    modal.setAttribute('aria-hidden', 'true');
    if (modal._prevFocus && typeof modal._prevFocus.focus === 'function') {
      modal._prevFocus.focus();
    }
    document.documentElement.style.overflow = '';
    modal.classList.remove('modal-opened');
    modal.removeEventListener('keydown', trapListener);
  };

  function trapListener(e) {
    if (e.key !== 'Tab') return;
    const modal = e.currentTarget;
    const focusables = Array.from(modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
      .filter(el => !el.disabled && el.offsetParent !== null);
    
    if (!focusables.length) return;
    
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  // Delegated click handler
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-modal]');
    if (btn) {
      const modal = document.getElementById(btn.getAttribute('data-modal'));
      if (modal) openModal(modal);
      return;
    }

    // Botones de cerrar
    const closeBtn = e.target.closest('[data-close], .close');
    if (closeBtn) {
      const modal = closeBtn.closest('.modal');
      if (modal) closeModal(modal);
      return;
    }

    // Clic fuera del contenido del modal
    const clickedModal = e.target.closest('.modal');
    if (clickedModal && e.target === clickedModal) closeModal(clickedModal);

    // Efecto ripple para enlaces
    const tracked = e.target.closest('.track-link');
    if (tracked && tracked.tagName.toLowerCase() === 'a') {
      createRipple(tracked, e);
    }
  });

  // ESC para cerrar
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' || e.key === 'Esc') {
      document.querySelectorAll('.modal[aria-hidden="false"]').forEach(m => closeModal(m));
    }
  });

  // Efecto ripple mejorado
  function createRipple(el, e) {
    if (el.querySelector('.ripple')) return;
    
    const rect = el.getBoundingClientRect();
    const ripple = document.createElement('div');
    ripple.className = 'ripple';
    
    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
    
    el.style.position = el.style.position || 'relative';
    el.appendChild(ripple);
    
    setTimeout(() => {
      if (ripple.parentNode === el) {
        el.removeChild(ripple);
      }
    }, 600);
  }

  // --------------------------
  // Carga de usuario mejorada
  // --------------------------
  async function loadUser() {
    const nameEl = document.getElementById('user-name');
    const greetingEl = document.getElementById('greeting');
    const avatarEl = document.getElementById('user-avatar');
    
    try {
      const res = await fetch('/api/user', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('no auth');
      
      const data = await res.json();
      const name = (data.user && (data.user.name || data.user.username || data.user.email)) || 'Usuario';
      const hour = new Date().getHours();
      const when = hour < 12 ? 'Buen día' : (hour < 18 ? 'Buenas tardes' : 'Buenas noches');
      
      greetingEl.textContent = `${when}, ${name} 👋`;
      nameEl.textContent = name;
      
      // Actualizar avatar si hay información
      if (data.user && data.user.avatar) {
        avatarEl.innerHTML = `<img src="${data.user.avatar}" alt="${name}" />`;
      }
      
    } catch (err) {
      // Fallback al estado por defecto
      nameEl.textContent = 'Usuario';
    }
  }

  // --------------------------
  // Efecto Tilt mejorado
  // --------------------------
  function initTilt() {
    $$('[data-tilt]').forEach(el => {
      let isHovering = false;
      
      el.addEventListener('mouseenter', () => {
        isHovering = true;
      });
      
      el.addEventListener('mouseleave', () => {
        isHovering = false;
        el.style.transform = '';
      });
      
      el.addEventListener('mousemove', (ev) => {
        if (!isHovering) return;
        
        const rect = el.getBoundingClientRect();
        const px = (ev.clientX - rect.left) / rect.width;
        const py = (ev.clientY - rect.top) / rect.height;
        
        const rx = (py - 0.5) * 8; // rotateX
        const ry = (px - 0.5) * -16; // rotateY
        
        el.style.transform = `perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(10px) scale(1.02)`;
      });
    });
  }

  // --------------------------
  // Efectos de sonido (opcional)
  // --------------------------
  function playSound(type) {
    // En una implementación real, aquí cargarías y reproducirías sonidos
    console.log(`Playing sound: ${type}`);
  }

  // --------------------------
  // Inicialización
  // --------------------------
  document.addEventListener('DOMContentLoaded', function() {
    initParticleSystem();
    initTilt();
    loadUser();
    
    // Efecto de aparición escalonada
    const elements = $$('.hero-left, .hero-right, .meta-helpers');
    elements.forEach((el, index) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      
      setTimeout(() => {
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, index * 200);
    });
    
    // Efectos de sonido en interacciones
    document.addEventListener('click', (e) => {
      if (e.target.closest('.main-btn')) {
        playSound('click');
      }
      if (e.target.closest('.track-link')) {
        playSound('link');
      }
    });
  });

  // --------------------------
  // Clean up
  // --------------------------
  window.addEventListener('beforeunload', () => {
    document.documentElement.style.overflow = '';
    if (confettiAnim) cancelAnimationFrame(confettiAnim);
  });

})();