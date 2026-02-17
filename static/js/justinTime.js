// justinTime.js
// Versión optimizada sin filtro de años en frontend

document.addEventListener("DOMContentLoaded", function () {
  const perPage = 25;
  let currentPage = 1;
  let allData = null;
  
  const tableBody = document.getElementById("jt-body");
  const pagination = document.getElementById("jt-pagination");
  const infoCount = document.getElementById("info-count");
  const loadingSpinner = document.getElementById("loadingSpinner");

  // Inicializar
  init();

  function init() {
    setupEventListeners();
    loadData();
  }

  function setupEventListeners() {
    // Ordenamiento por columnas
    document.querySelectorAll('th[data-sort]').forEach(th => {
      th.style.cursor = 'pointer';
      th.title = 'Click para ordenar';
      th.addEventListener('click', () => {
        const field = th.getAttribute('data-sort');
        sortData(field);
      });
    });
  }

  function loadData(useCache = false) {
    setLoading(true);
    
    const params = new URLSearchParams({
      page: currentPage,
      per_page: perPage
    });

    fetch(`${API_URL}?${params}`)
      .then(response => {
        if (!response.ok) throw new Error('Error en la respuesta del servidor');
        return response.json();
      })
      .then(data => {
        if (!data.success) throw new Error(data.error || 'Error en los datos');
        
        if (useCache && allData) {
          renderFromCache();
        } else {
          renderTable(data.data);
          allData = data.data; // Cachear para ordenamiento
        }
        
        renderPagination(data.page, data.total_pages, data.total);
        updateStats(data.total, data.page, data.total_pages);
      })
      .catch(error => {
        console.error('Error:', error);
        showError(error.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }

  function renderTable(rows) {
    if (!rows || rows.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="14" class="no-data">
            No hay registros para el año 2025 con estado "sale"
          </td>
        </tr>
      `;
      return;
    }

    const fragment = document.createDocumentFragment();
    
    rows.forEach(row => {
      const tr = document.createElement('tr');
      tr.innerHTML = getRowHTML(row);
      fragment.appendChild(tr);
    });

    tableBody.innerHTML = '';
    tableBody.appendChild(fragment);
  }

  function getRowHTML(row) {
    return `
      <td>${escapeHtml(row.ref_interna)}</td>
      <td class="number">${formatNumber(row.price_unit)}</td>
      <td title="${escapeHtml(row.nombre_corto)}">
        ${truncateText(escapeHtml(row.nombre_corto), 50)}
      </td>
      <td class="number">${formatNumber(row.qty_delivered)}</td>
      <td class="number">${formatNumber(row.cantidad)}</td>
      <td class="state state-${escapeHtml(row.state)}">
        ${escapeHtml(row.state)}
      </td>
      <td>${formatDate(row.create_date)}</td>
      <td>${formatDate(row.effective_date)}</td>
      <td>${escapeHtml(row.canal)}</td>
      <td>${escapeHtml(row.fuente)}</td>
      <td>${escapeHtml(row.marca)}</td>
      <td>${escapeHtml(row.orden_fuente)}</td>
      <td>${escapeHtml(row.referencia)}</td>
      <td>${escapeHtml(row.vendedor)}</td>
    `;
  }

  function renderFromCache() {
    if (!allData) return;
    renderTable(allData);
  }

  function renderPagination(page, totalPages, total) {
    pagination.innerHTML = '';

    if (totalPages <= 1) return;

    const createButton = (label, targetPage, disabled = false, className = '') => {
      const button = document.createElement('button');
      button.className = `page-btn ${className}`;
      button.textContent = label;
      button.disabled = disabled;
      if (!disabled && targetPage !== page) {
        button.addEventListener('click', () => {
          currentPage = targetPage;
          loadData(true);
        });
      }
      return button;
    };

    // Botones de navegación
    pagination.appendChild(createButton('«', 1, page === 1));
    pagination.appendChild(createButton('‹', page - 1, page === 1));

    // Rango de páginas
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(totalPages, page + 2);

    for (let p = startPage; p <= endPage; p++) {
      const btn = createButton(p, p, false, p === page ? 'active' : '');
      pagination.appendChild(btn);
    }

    pagination.appendChild(createButton('›', page + 1, page === totalPages));
    pagination.appendChild(createButton('»', totalPages, page === totalPages));
  }

  function sortData(field) {
    if (!allData) return;
    
    allData.sort((a, b) => {
      const aVal = a[field] || '';
      const bVal = b[field] || '';
      
      if (aVal < bVal) return -1;
      if (aVal > bVal) return 1;
      return 0;
    });
    
    renderTable(allData);
  }

  function updateStats(total, page, totalPages) {
    const start = ((page - 1) * perPage) + 1;
    const end = Math.min(page * perPage, total);
    
    infoCount.innerHTML = `
      Mostrando <strong>${start}-${end}</strong> de 
      <strong>${total.toLocaleString()}</strong> registros 
      (Año 2025 - Estado: Sale)
      - Página ${page} de ${totalPages}
    `;
  }

  function setLoading(loading) {
    loadingSpinner.style.display = loading ? 'block' : 'none';
    if (loading) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="14" class="loading-message">
            <div class="spinner"></div>
            Cargando datos del año 2025...
          </td>
        </tr>
      `;
    }
  }

  function showError(message) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="14" class="error-message">
          ❌ Error: ${message}
          <br><button onclick="location.reload()">Reintentar</button>
        </td>
      </tr>
    `;
  }

  // Utilidades
  function escapeHtml(str) {
    if (str == null) return "";
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatNumber(n) {
    if (n == null || isNaN(Number(n))) return "0";
    return Number(n).toLocaleString('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('es-ES');
    } catch {
      return dateStr;
    }
  }

  function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }
});