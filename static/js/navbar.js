document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobile-menu');
    const navbarMenu = document.getElementById('navbar-menu');
    
    mobileMenuBtn.addEventListener('click', function() {
        this.classList.toggle('active');
        navbarMenu.classList.toggle('active');
        
        if (navbarMenu.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    });
    
    // Dropdown functionality for mobile
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                const dropdown = this.closest('.dropdown');
                dropdown.classList.toggle('active');
            }
        });
    });
    
    // Close menu when clicking on a link (for mobile)
    const navLinks = document.querySelectorAll('.nav-link:not(.dropdown-toggle)');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                mobileMenuBtn.classList.remove('active');
                navbarMenu.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });
    
    // Set current year in footer
    document.getElementById('current-year').textContent = new Date().getFullYear();
    
    // Navbar scroll effect
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 50) {
            navbar.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
            navbar.style.height = '60px';
        } else {
            navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
            navbar.style.height = '70px';
        }
    });
    
    // Desktop dropdown hover effect
    if (window.innerWidth > 768) {
        document.querySelectorAll('.dropdown').forEach(dropdown => {
            dropdown.addEventListener('mouseenter', function() {
                this.querySelector('.dropdown-menu').style.opacity = '1';
                this.querySelector('.dropdown-menu').style.visibility = 'visible';
                this.querySelector('.dropdown-menu').style.transform = 'translateY(0)';
            });
            
            dropdown.addEventListener('mouseleave', function() {
                this.querySelector('.dropdown-menu').style.opacity = '0';
                this.querySelector('.dropdown-menu').style.visibility = 'hidden';
                this.querySelector('.dropdown-menu').style.transform = 'translateY(10px)';
            });
        });
    }
    
    // Highlight active link based on current URL
    function highlightActiveLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link, .dropdown-link');
        
        navLinks.forEach(link => {
            const linkPath = link.getAttribute('href');
            
            // Check if the link matches the current path
            if (linkPath === currentPath) {
                link.classList.add('active');
                
                // If it's a dropdown item, also highlight its parent
                if (link.classList.contains('dropdown-link')) {
                    const dropdown = link.closest('.dropdown');
                    if (dropdown) {
                        dropdown.querySelector('.dropdown-toggle').classList.add('active');
                    }
                }
            }
        });
    }
    
    highlightActiveLink();
});


document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobile-menu');
    const navbarMenu = document.getElementById('navbar-menu');
    
    mobileMenuBtn.addEventListener('click', function() {
        this.classList.toggle('active');
        navbarMenu.classList.toggle('active');
        
        if (navbarMenu.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    });
    
    // Dropdown functionality for mobile
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                const dropdown = this.closest('.dropdown');
                dropdown.classList.toggle('active');
            }
        });
    });
    
    // Close menu when clicking on a link (for mobile)
    const navLinks = document.querySelectorAll('.nav-link:not(.dropdown-toggle)');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                mobileMenuBtn.classList.remove('active');
                navbarMenu.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });
    
    // Set current year in footer (si existe el elemento)
    const yearEl = document.getElementById('current-year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();
    
    // Navbar scroll effect
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 50) {
            navbar.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
            navbar.style.height = '60px';
        } else {
            navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
            navbar.style.height = '70px';
        }
    });
    
    // Desktop dropdown hover effect
    if (window.innerWidth > 768) {
        document.querySelectorAll('.dropdown').forEach(dropdown => {
            dropdown.addEventListener('mouseenter', function() {
                this.querySelector('.dropdown-menu').style.opacity = '1';
                this.querySelector('.dropdown-menu').style.visibility = 'visible';
                this.querySelector('.dropdown-menu').style.transform = 'translateY(0)';
            });
            
            dropdown.addEventListener('mouseleave', function() {
                this.querySelector('.dropdown-menu').style.opacity = '0';
                this.querySelector('.dropdown-menu').style.visibility = 'hidden';
                this.querySelector('.dropdown-menu').style.transform = 'translateY(10px)';
            });
        });
    }
    
    // Highlight active link based on current URL
    function highlightActiveLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link, .dropdown-link');
        
        navLinks.forEach(link => {
            const linkPath = link.getAttribute('href');
            
            // Check if the link matches the current path
            if (linkPath === currentPath) {
                link.classList.add('active');
                
                // If it's a dropdown item, also highlight its parent
                if (link.classList.contains('dropdown-link')) {
                    const dropdown = link.closest('.dropdown');
                    if (dropdown) {
                        dropdown.querySelector('.dropdown-toggle').classList.add('active');
                    }
                }
            }
        });
    }
    
    highlightActiveLink();

    // --- LOGOUT: enviar POST a /api/logout usando cookies ---
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function (e) {
            e.preventDefault();
            try {
                const response = await fetch('/api/logout', {
                    method: 'POST',
                    credentials: 'include', // importante: enviar cookies HttpOnly
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({}) // cuerpo vacío
                });

                // Si la API devuelve 200 o 401 (ya no auth), redirigimos a /inicio/
                if (response.ok) {
                    // opcional: leer msg
                    // const data = await response.json();
                    window.location.href = '/inicio/';
                    return;
                } else {
                    // si falla por token expirado/revocado, igual forzamos redirect al login
                    window.location.href = '/inicio/';
                    return;
                }
            } catch (err) {
                // en caso de error de red, redirigimos también y logueamos
                console.error('Error logout:', err);
                window.location.href = '/inicio/';
            }
        });
    }
});
