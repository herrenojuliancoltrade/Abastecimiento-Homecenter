document.addEventListener('DOMContentLoaded', function () {
  const endpointData = '/forecast/data';
  const endpointOptions = '/forecast/options';
  const tbody = document.getElementById('forecast-body');

  const selectCentro = document.getElementById('filter-centro');
  const selectPunto = document.getElementById('filter-punto');
  const selectCanal = document.getElementById('filter-canal');
  const selectMaterial = document.getElementById('filter-material');
  const selectProducto = document.getElementById('filter-producto');
  const selectMarca = document.getElementById('filter-marca');

  const btnApply = document.getElementById('apply-filters');
  const btnClear = document.getElementById('clear-filters');
  const btnRefresh = document.getElementById('refresh-data');
  const btnExport = document.getElementById('export-page');
  const btnToggleFilters = document.getElementById('toggle-filters');
  const btnScrollTop = document.getElementById('scroll-top');
  const btnConfigureColumns = document.getElementById('configure-columns');
  const btnDivideEnvioInventario = document.getElementById('divide-envio-inventario');
  const btnDivideEnvioVentas = document.getElementById('divide-envio-ventas');

  // Pagination controls
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');
  const pageDisplay = document.getElementById('page-display');
  const pageSizeSelect = document.getElementById('page-size-select');
  const divideValueInput = document.getElementById('divide-value');

  const sumaSpan = document.getElementById('suma-sugerido');
  const totalRowsSpan = document.getElementById('total-rows');

  // Modal elements
  const modal = document.getElementById('columns-modal');
  const modalClose = document.querySelector('.modal-close');
  const applyColumnsBtn = document.getElementById('apply-columns');
  const resetColumnsBtn = document.getElementById('reset-columns');

  let currentPage = 1;
  let currentPageSize = parseInt(pageSizeSelect.value || '50');
  let totalPages = 1;
  let lastPayloadRecords = []; // records from last server response (page)
  // sugeridos map keyed by `${Centro Costos}|${Material}`
  let sugeridos = {};
  let unsavedChanges = false;

  // Sorting state
  let currentSortColumn = null;
  let currentSortDirection = null; // 'asc' or 'desc'

  // store previous filters to revert if user cancels
  let previousFilters = {
    centro: [],
    punto: [],
    canal: [],
    material: [],
    producto: [],
    marca: []
  };

  let debounceTimer = null;
  let filtersVisible = true;

  // Column management
  let columnVisibility = {
    'centro-costos': true,
    'material': true,
    'producto': true,
    'marca': false,
    'punto-venta': true,
    'canal-regional': false,
    'ventas-actuales': true,
    'ventas-mes-pasado': true,
    'promedio-3-meses': true,
    'maximo': false,
    'mediana': false,
    'inventario': true,
    'transitos': true,
    'indicador-3-meses': true,
    'indicador-ventas-mes-pasado': true,
    'envio-inventario-3-meses': true,
    'envio-ventas-actuales': true,
    'sugerido': true
  };

  // Default column visibility (for reset)
  const defaultColumnVisibility = {
    'centro-costos': true,
    'material': true,
    'producto': true,
    'marca': false,
    'punto-venta': true,
    'canal-regional': false,
    'ventas-actuales': true,
    'ventas-mes-pasado': true,
    'promedio-3-meses': true,
    'maximo': false,
    'mediana': false,
    'inventario': true,
    'transitos': true,
    'indicador-3-meses': true,
    'indicador-ventas-mes-pasado': true,
    'envio-inventario-3-meses': true,
    'envio-ventas-actuales': true,
    'sugerido': true
  };

  function formatNumber(n) {
    if (n === null || n === undefined || n === '') return '-';
    if (typeof n === 'number') return Number(n).toLocaleString(undefined, {maximumFractionDigits: 2});
    const parsed = Number(n);
    if (isNaN(parsed)) return String(n);
    return parsed.toLocaleString();
  }

  function formatIndicator(v) {
    if (v === null || v === undefined) return '-';
    const num = Number(v);
    if (isNaN(num)) return '-';
    return num.toFixed(4);
  }

  function escapeHtml(text) {
    if (!text && text !== 0) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function populateSelect(selectEl, values, preserveSelected=true) {
    const prevSelected = Array.from(selectEl.selectedOptions || []).map(o => o.value);
    selectEl.innerHTML = '';
    const firstOpt = document.createElement('option');
    firstOpt.value = '';
    firstOpt.text = '(todos)';
    selectEl.appendChild(firstOpt);

    if (!values || values.length === 0) return;
    values.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.text = v;
      selectEl.appendChild(opt);
    });

    if (preserveSelected && prevSelected && prevSelected.length > 0) {
      Array.from(selectEl.options).forEach(opt => {
        if (prevSelected.indexOf(opt.value) !== -1) {
          opt.selected = true;
        }
      });
    }
  }

  function getSelectValues(selectEl) {
    const vals = Array.from(selectEl.selectedOptions).map(o => o.value).filter(v => v !== '');
    return vals;
  }

  function buildQueryParams() {
    const params = new URLSearchParams();
    const centros = getSelectValues(selectCentro);
    const puntos = getSelectValues(selectPunto);
    const canales = getSelectValues(selectCanal);
    const materials = getSelectValues(selectMaterial);
    const productos = getSelectValues(selectProducto);
    const marcas = getSelectValues(selectMarca);

    if (centros.length) params.set('centro', centros.join(','));
    if (puntos.length) params.set('punto', puntos.join(','));
    if (canales.length) params.set('canal', canales.join(','));
    if (materials.length) params.set('material', materials.join(','));
    if (productos.length) params.set('producto', productos.join(','));
    if (marcas.length) params.set('marca', marcas.join(','));
    params.set('page', String(currentPage));
    params.set('page_size', String(currentPageSize));
    return params.toString();
  }

  function keyForRow(row) {
    return `${row['Centro Costos'] || ''}|${row['Material'] || ''}`;
  }

  function updateSuma() {
    let sum = 0;
    let hasNumeric = false;
    Object.values(sugeridos).forEach(v => {
      if (v === null || v === undefined) return;
      const str = String(v).trim();
      if (str === '') return;
      const num = Number(str.replace(',', '.'));
      if (!isNaN(num)) {
        sum += num;
        hasNumeric = true;
      }
    });
    sumaSpan.textContent = hasNumeric ? sum.toLocaleString(undefined, {maximumFractionDigits: 2}) : '0';
  }

  function applyColumnVisibility() {
    const table = document.getElementById('forecast-table');
    const headers = table.querySelectorAll('thead th');
    const rows = table.querySelectorAll('tbody tr');
    
    headers.forEach((header, index) => {
      const columnName = header.getAttribute('data-column');
      if (columnName && columnVisibility.hasOwnProperty(columnName)) {
        if (columnVisibility[columnName]) {
          header.classList.remove('hidden-column');
          // Show this column in all rows
          rows.forEach(row => {
            const cell = row.cells[index];
            if (cell) cell.classList.remove('hidden-column');
          });
        } else {
          header.classList.add('hidden-column');
          // Hide this column in all rows
          rows.forEach(row => {
            const cell = row.cells[index];
            if (cell) cell.classList.add('hidden-column');
          });
        }
      }
    });
  }

  function updateModalColumnIcons() {
    Object.keys(columnVisibility).forEach(columnName => {
      const columnItem = document.querySelector(`.column-item[data-column="${columnName}"]`);
      if (columnItem) {
        const button = columnItem.querySelector('.column-toggle');
        const icon = button.querySelector('i');
        if (columnVisibility[columnName]) {
          icon.className = 'fas fa-eye';
          button.classList.add('active');
        } else {
          icon.className = 'fas fa-eye-slash';
          button.classList.remove('active');
        }
      }
    });
  }

  function setupColumnResizing() {
    const table = document.getElementById('forecast-table');
    const headers = table.querySelectorAll('thead th.resizable');
    let isResizing = false;
    let currentHeader = null;
    let startX = 0;
    let startWidth = 0;

    headers.forEach(header => {
      header.addEventListener('mousedown', function(e) {
        if (e.offsetX > this.offsetWidth - 10) {
          isResizing = true;
          currentHeader = this;
          startX = e.pageX;
          startWidth = this.offsetWidth;
          e.preventDefault();
        }
      });
    });

    document.addEventListener('mousemove', function(e) {
      if (!isResizing || !currentHeader) return;
      
      const width = startWidth + (e.pageX - startX);
      if (width > 50) { // Minimum width
        currentHeader.style.width = width + 'px';
        
        // Update all cells in this column
        const columnIndex = Array.from(currentHeader.parentNode.children).indexOf(currentHeader);
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
          const cell = row.cells[columnIndex];
          if (cell) cell.style.width = width + 'px';
        });
      }
    });

    document.addEventListener('mouseup', function() {
      isResizing = false;
      currentHeader = null;
    });
  }

  function applyEnvioColorCoding() {
    const table = document.getElementById('forecast-table');
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
      // Envío Inventario 3 meses (column 15)
      const envioInventarioCell = row.cells[15];
      if (envioInventarioCell) {
        const value = parseFloat(envioInventarioCell.textContent.replace(/[^\d.-]/g, ''));
        if (!isNaN(value)) {
          envioInventarioCell.classList.remove('envio-positive', 'envio-negative', 'envio-zero');
          if (value < 0) {
            envioInventarioCell.classList.add('envio-negative');
          } else if (value > 0) {
            envioInventarioCell.classList.add('envio-positive');
          } else {
            envioInventarioCell.classList.add('envio-zero');
          }
        }
      }
      
      // Envío Ventas Actuales (column 16)
      const envioVentasCell = row.cells[16];
      if (envioVentasCell) {
        const value = parseFloat(envioVentasCell.textContent.replace(/[^\d.-]/g, ''));
        if (!isNaN(value)) {
          envioVentasCell.classList.remove('envio-positive', 'envio-negative', 'envio-zero');
          if (value < 0) {
            envioVentasCell.classList.add('envio-negative');
          } else if (value > 0) {
            envioVentasCell.classList.add('envio-positive');
          } else {
            envioVentasCell.classList.add('envio-zero');
          }
        }
      }
    });
  }

  function sortTableByColumn(columnIndex, direction) {
    const table = document.getElementById('forecast-table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Remove existing sort classes
    table.querySelectorAll('thead th.sortable').forEach(th => {
      th.classList.remove('asc', 'desc');
    });
    
    // Add sort class to current column
    const currentHeader = table.querySelectorAll('thead th')[columnIndex];
    currentHeader.classList.add(direction);
    
    rows.sort((a, b) => {
      const aCell = a.cells[columnIndex];
      const bCell = b.cells[columnIndex];
      
      let aValue = aCell.textContent.trim();
      let bValue = bCell.textContent.trim();
      
      // Handle numeric values
      aValue = aValue === '-' ? 0 : parseFloat(aValue.replace(/[^\d.-]/g, '')) || 0;
      bValue = bValue === '-' ? 0 : parseFloat(bValue.replace(/[^\d.-]/g, '')) || 0;
      
      if (direction === 'asc') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    });
    
    // Remove all rows
    while (tbody.firstChild) {
      tbody.removeChild(tbody.firstChild);
    }
    
    // Add sorted rows
    rows.forEach(row => tbody.appendChild(row));
    
    // Reapply color coding
    applyEnvioColorCoding();
    
    // Update sorting state
    currentSortColumn = columnIndex;
    currentSortDirection = direction;
  }

  function setupSorting() {
    const table = document.getElementById('forecast-table');
    const sortableHeaders = table.querySelectorAll('thead th.sortable');
    
    sortableHeaders.forEach((header, index) => {
      header.addEventListener('click', function() {
        let direction = 'desc'; // Default to descending (highest first)
        
        // If already sorted by this column, toggle direction
        if (currentSortColumn === index) {
          direction = currentSortDirection === 'desc' ? 'asc' : 'desc';
        }
        
        sortTableByColumn(index, direction);
      });
    });
  }

  function divideEnvioValues(columnIndex) {
    const divideValue = parseFloat(divideValueInput.value);
    
    if (!divideValue || divideValue <= 0) {
      showNotification('Por favor ingrese un número válido mayor a 0', 'warning');
      return;
    }
    
    const table = document.getElementById('forecast-table');
    const rows = table.querySelectorAll('tbody tr');
    let modifiedCount = 0;
    
    rows.forEach(row => {
      const cell = row.cells[columnIndex];
      if (cell && cell.textContent !== '-') {
        const originalValue = parseFloat(cell.textContent.replace(/[^\d.-]/g, ''));
        if (!isNaN(originalValue)) {
          const newValue = originalValue / divideValue;
          cell.textContent = formatNumber(newValue);
          modifiedCount++;
        }
      }
    });
    
    // Reapply color coding
    applyEnvioColorCoding();
    
    showNotification(`Se dividieron ${modifiedCount} valores de ${getColumnName(columnIndex)} por ${divideValue}`, 'success');
  }

  function getColumnName(columnIndex) {
    const headers = [
      'Centro Costos', 'Material', 'Producto', 'Marca', 'Punto de Venta', 'Canal o Regional',
      'Ventas Actuales', 'Ventas Mes pasado', 'Promedio 3 Meses', 'Maximo', 'Mediana',
      'Inventario', 'Transitos', 'Indicador 3 Meses', 'Indicador Ventas Mes Pasado',
      'Envío Inventario 3 meses', 'Envío Ventas Actuales', 'Sugerido'
    ];
    return headers[columnIndex] || `Columna ${columnIndex + 1}`;
  }

  function renderTableFromRecords(records) {
    lastPayloadRecords = records || [];
    tbody.innerHTML = '';
    if (!records || records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="18" class="loading"><div><i class="fas fa-inbox"></i></div><div>No hay datos disponibles</div></td></tr>';
      return;
    }
    records.forEach(row => {
      const key = keyForRow(row);
      const sugeridoValue = (sugeridos.hasOwnProperty(key)) ? sugeridos[key] : '';
      const tr = document.createElement('tr');

      // Maximo is always 0 (user requirement)
      const maximo = 0;

      tr.innerHTML = `
        <td>${escapeHtml(row['Centro Costos'] ?? '')}</td>
        <td>${escapeHtml(row['Material'] ?? '')}</td>
        <td>${escapeHtml(row['Productos'] ?? '')}</td>
        <td>${escapeHtml(row['Marca'] ?? '')}</td>
        <td>${escapeHtml(row['Punto de Venta'] ?? '')}</td>
        <td>${escapeHtml(row['Canal o Regional'] ?? '')}</td>
        <td>${formatNumber(row['Ventas_Mes_Actual'])}</td>
        <td>${formatNumber(row['Ventas_Mes_Pasado'])}</td>
        <td>${formatNumber(row['Ventas_Promedio_3_Meses'])}</td>
        <td>${formatNumber(maximo)}</td>
        <td>${formatNumber(row['Mediana'])}</td>
        <td>${formatNumber(row['Inventario'])}</td>
        <td>${formatNumber(row['Transitos'])}</td>
        <td>${formatIndicator(row['Indicador_3_Meses'])}</td>
        <td>${formatIndicator(row['Indicador_Mes_Pasado'])}</td>
        <td>${formatNumber(row['Envio_3_Meses'])}</td>
        <td>${formatNumber(row['Envio_Pasadas'])}</td>
        <td><input type="number" class="sugerido-input" data-key="${key}" value="${sugeridoValue}" min="0" step="0.01"></td>
      `;
      tbody.appendChild(tr);
    });

    // Apply column visibility after rendering
    applyColumnVisibility();
    
    // Apply color coding to Envio columns
    applyEnvioColorCoding();

    // Attach listeners to inputs
    document.querySelectorAll('.sugerido-input').forEach(inp => {
      inp.addEventListener('input', function (e) {
        const k = e.target.getAttribute('data-key');
        const v = e.target.value;
        if (v === '' || v === null) {
          delete sugeridos[k];
        } else {
          sugeridos[k] = v;
        }
        unsavedChanges = Object.keys(sugeridos).length > 0;
        updateSuma();
      });
    });

    // update suma after rendering (in case inputs came from stored sugeridos)
    updateSuma();
  }

  function updatePaginationDisplay(total, page, page_size, total_pages) {
    currentPage = page;
    currentPageSize = page_size;
    totalPages = total_pages;
    pageDisplay.textContent = `Página ${page} / ${total_pages} — Total: ${total}`;
    totalRowsSpan.textContent = total;
    prevBtn.disabled = (page <= 1);
    nextBtn.disabled = (page >= total_pages);
  }

  function confirmIfUnsavedAndProceed(actionCallback, revertCallback) {
    if (!unsavedChanges) {
      actionCallback();
      return;
    }
    const ok = window.confirm('Tiene cambios sin guardar en "Sugerido". Si continúa esos valores se perderán. ¿Desea continuar?');
    if (ok) {
      sugeridos = {};
      unsavedChanges = false;
      updateSuma();
      actionCallback();
    } else {
      if (typeof revertCallback === 'function') revertCallback();
      return;
    }
  }

  function fetchDataAndRender() {
    tbody.innerHTML = '<tr><td colspan="18" class="loading"><div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i></div><div>Cargando datos...</div></td></tr>';
    const q = buildQueryParams();
    const url = q ? `${endpointData}?${q}` : endpointData;
    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error('Error al obtener datos');
        return res.json();
      })
      .then(payload => {
        const records = payload.records || [];
        renderTableFromRecords(records);
        updatePaginationDisplay(payload.total || 0, payload.page || 1, payload.page_size || currentPageSize, payload.total_pages || 1);
      })
      .catch(err => {
        tbody.innerHTML = `<tr><td colspan="18" class="loading"><div><i class="fas fa-exclamation-triangle"></i></div><div>Error cargando datos: ${err.message}</div></td></tr>`;
        console.error(err);
      });
  }

  // Construye timestamp de Colombia para nombre de archivo: YYYYMMDD_HHMMSS
  function colombiaTimestampForFilename() {
    const now = new Date();
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'America/Bogota',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).formatToParts(now);
    const map = {};
    parts.forEach(p => { map[p.type] = p.value; });
    const y = map.year, m = map.month, d = map.day, hh = map.hour, mm = map.minute, ss = map.second;
    return `${y}${m}${d}_${hh}${mm}${ss}`;
  }

  function exportCurrentPageToExcel() {
    if (!lastPayloadRecords || lastPayloadRecords.length === 0) {
      showNotification('No hay filas en la página actual para exportar.', 'warning');
      return;
    }
    // Filtrar solo filas de la página actual que tengan valor en sugeridos
    const rowsToExport = lastPayloadRecords.filter(r => {
      const k = keyForRow(r);
      return sugeridos.hasOwnProperty(k) && sugestionIsNotEmpty(sugeridos[k]);
    });

    if (!rowsToExport || rowsToExport.length === 0) {
      showNotification('No hay filas con "Sugerido" en la página actual para exportar.', 'warning');
      return;
    }

    // Encabezados y orden solicitados por el usuario (nombres mostrados en Excel)
    const headers = [
      'Centro Costos','Material','Producto','Marca','Punto de Venta','Canal o Regional',
      'Ventas Actuales','Ventas Mes pasado','Promedio 3 Meses','Maximo','Mediana',
      'Inventario','Transitos','Indicador 3 Meses','Indicador Ventas Mes Pasado',
      'Envío Inventario 3 meses','Envío Ventas Actuales','Sugerido'
    ];

    const dataForXLSX = rowsToExport.map(r => {
      const k = keyForRow(r);
      const sugRaw = sugeridos[k];
      // Convertir sugerido a número si es posible
      let sugVal = sugRaw;
      if (sugRaw !== '' && sugRaw !== null && sugRaw !== undefined) {
        const num = Number(String(sugRaw).replace(',', '.'));
        if (!isNaN(num)) sugVal = num;
      }
      return {
        'Centro Costos': r['Centro Costos'] ?? '',
        'Material': r['Material'] ?? '',
        'Producto': r['Productos'] ?? '',
        'Marca': r['Marca'] ?? '',
        'Punto de Venta': r['Punto de Venta'] ?? '',
        'Canal o Regional': r['Canal o Regional'] ?? '',
        'Ventas Actuales': r['Ventas_Mes_Actual'] ?? '',
        'Ventas Mes pasado': r['Ventas_Mes_Pasado'] ?? '',
        'Promedio 3 Meses': r['Ventas_Promedio_3_Meses'] ?? '',
        'Maximo': 0,
        'Mediana': r['Mediana'] ?? '',
        'Inventario': r['Inventario'] ?? '',
        'Transitos': r['Transitos'] ?? '',
        'Indicador 3 Meses': r['Indicador_3_Meses'] ?? '',
        'Indicador Ventas Mes Pasado': r['Indicador_Mes_Pasado'] ?? '',
        'Envío Inventario 3 meses': r['Envio_3_Meses'] ?? '',
        'Envío Ventas Actuales': r['Envio_Pasadas'] ?? '',
        'Sugerido': sugVal ?? ''
      };
    });

    // Usar SheetJS para generar workbook y descargar .xlsx con timestamp Colombia
    try {
      const ws = XLSX.utils.json_to_sheet(dataForXLSX, { header: headers });
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Export');
      const ts = colombiaTimestampForFilename();
      const filename = `forecast_export_${ts}.xlsx`;
      XLSX.writeFile(wb, filename);
      showNotification(`Archivo exportado exitosamente: ${filename}`, 'success');
    } catch (err) {
      console.error('Error exportando a Excel:', err);
      showNotification('Ocurrió un error al generar el archivo Excel.', 'error');
    }
  }

  // helper: determine if suggestion is not empty
  function sugestionIsNotEmpty(v) {
    return v !== null && v !== undefined && String(v).trim() !== '';
  }

  // handle filter change with debounce and dependency reload
  function scheduleFilterApply() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      applyFiltersAuto();
    }, 400);
  }

  function applyFiltersAuto() {
    confirmIfUnsavedAndProceed(function () {
      previousFilters = {
        centro: getSelectValues(selectCentro),
        punto: getSelectValues(selectPunto),
        canal: getSelectValues(selectCanal),
        material: getSelectValues(selectMaterial),
        producto: getSelectValues(selectProducto),
        marca: getSelectValues(selectMarca)
      };
      currentPage = 1;
      loadOptionsAndData();
    }, function () {
      restorePreviousFilters();
    });
  }

  function restorePreviousFilters() {
    function setSelectValues(sel, values) {
      Array.from(sel.options).forEach(opt => {
        opt.selected = values.indexOf(opt.value) !== -1;
      });
    }
    setSelectValues(selectCentro, previousFilters.centro || []);
    setSelectValues(selectPunto, previousFilters.punto || []);
    setSelectValues(selectCanal, previousFilters.canal || []);
    setSelectValues(selectMaterial, previousFilters.material || []);
    setSelectValues(selectProducto, previousFilters.producto || []);
    setSelectValues(selectMarca, previousFilters.marca || []);
  }

  // Función para mostrar notificaciones
  function showNotification(message, type = 'info') {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.className = `notification`;
    
    // Configurar colores según el tipo
    let bgColor, icon;
    switch(type) {
      case 'success':
        bgColor = 'var(--success)';
        icon = 'check-circle';
        break;
      case 'warning':
        bgColor = 'var(--warning)';
        icon = 'exclamation-triangle';
        break;
      case 'error':
        bgColor = 'var(--danger)';
        icon = 'times-circle';
        break;
      default:
        bgColor = 'var(--primary)';
        icon = 'info-circle';
    }
    
    notification.style.background = bgColor;
    notification.style.color = 'white';
    
    notification.innerHTML = `
      <div class="notification-content">
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
      </div>
      <button class="notification-close"><i class="fas fa-times"></i></button>
    `;
    
    // Agregar al documento
    document.body.appendChild(notification);
    
    // Configurar cierre automático
    const autoClose = setTimeout(() => {
      closeNotification(notification);
    }, 5000);
    
    // Configurar cierre manual
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
      clearTimeout(autoClose);
      closeNotification(notification);
    });
    
    function closeNotification(notif) {
      notif.style.animation = 'slideOutRight 0.3s ease-in';
      setTimeout(() => {
        if (notif.parentNode) {
          notif.parentNode.removeChild(notif);
        }
      }, 300);
    }
  }

  // Toggle filters visibility
  function toggleFiltersVisibility() {
    const filtersBody = document.querySelector('#filters');
    const toggleIcon = btnToggleFilters.querySelector('i');
    
    if (filtersVisible) {
      filtersBody.style.display = 'none';
      toggleIcon.className = 'fas fa-chevron-up';
      filtersVisible = false;
    } else {
      filtersBody.style.display = 'flex';
      toggleIcon.className = 'fas fa-chevron-down';
      filtersVisible = true;
    }
  }

  // Scroll to top function
  function scrollToTop() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  }

  // Modal functions
  function openModal() {
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    updateModalColumnIcons();
  }

  function closeModal() {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }

  function toggleColumnInModal(columnName) {
    if (columnVisibility.hasOwnProperty(columnName)) {
      columnVisibility[columnName] = !columnVisibility[columnName];
      updateModalColumnIcons();
    }
  }

  function applyColumnChanges() {
    applyColumnVisibility();
    closeModal();
    showNotification('Configuración de columnas aplicada correctamente', 'success');
  }

  function resetColumnsToDefault() {
    columnVisibility = JSON.parse(JSON.stringify(defaultColumnVisibility));
    updateModalColumnIcons();
    showNotification('Columnas restablecidas a la configuración por defecto', 'info');
  }

  function initializeColumnControls() {
    // Setup column resizing
    setupColumnResizing();
    
    // Setup sorting
    setupSorting();
  }

  // Events and actions (with confirmIfUnsaved)
  btnApply.addEventListener('click', function () {
    confirmIfUnsavedAndProceed(function () {
      currentPage = 1;
      loadOptionsAndData();
    });
  });

  btnClear.addEventListener('click', function () {
    confirmIfUnsavedAndProceed(function () {
      selectCentro.querySelectorAll('option').forEach(o => o.selected = false);
      selectPunto.querySelectorAll('option').forEach(o => o.selected = false);
      selectCanal.querySelectorAll('option').forEach(o => o.selected = false);
      selectMaterial.querySelectorAll('option').forEach(o => o.selected = false);
      selectProducto.querySelectorAll('option').forEach(o => o.selected = false);
      selectMarca.querySelectorAll('option').forEach(o => o.selected = false);
      currentPage = 1;
      loadOptionsAndData();
    });
  });

  btnRefresh.addEventListener('click', function () {
    confirmIfUnsavedAndProceed(function () {
      fetchDataAndRender();
    });
  });

  prevBtn.addEventListener('click', function () {
    confirmIfUnsavedAndProceed(function () {
      if (currentPage > 1) {
        currentPage -= 1;
        fetchDataAndRender();
      }
    });
  });

  nextBtn.addEventListener('click', function () {
    confirmIfUnsavedAndProceed(function () {
      if (currentPage < totalPages) {
        currentPage += 1;
        fetchDataAndRender();
      }
    });
  });

  pageSizeSelect.addEventListener('change', function () {
    confirmIfUnsavedAndProceed(function () {
      currentPageSize = parseInt(pageSizeSelect.value || '50');
      currentPage = 1;
      fetchDataAndRender();
    });
  });

  btnExport.addEventListener('click', function () {
    exportCurrentPageToExcel();
  });

  btnToggleFilters.addEventListener('click', toggleFiltersVisibility);
  btnScrollTop.addEventListener('click', scrollToTop);

  // Divide buttons events
  btnDivideEnvioInventario.addEventListener('click', function() {
    divideEnvioValues(15); // Column index for "Envío Inventario 3 meses"
  });

  btnDivideEnvioVentas.addEventListener('click', function() {
    divideEnvioValues(16); // Column index for "Envío Ventas Actuales"
  });

  // Modal events
  btnConfigureColumns.addEventListener('click', openModal);
  modalClose.addEventListener('click', closeModal);
  applyColumnsBtn.addEventListener('click', applyColumnChanges);
  resetColumnsBtn.addEventListener('click', resetColumnsToDefault);

  // Close modal when clicking outside
  window.addEventListener('click', function(event) {
    if (event.target === modal) {
      closeModal();
    }
  });

  // Add event listeners to column toggle buttons in modal
  document.querySelectorAll('.column-toggle').forEach(button => {
    button.addEventListener('click', function(e) {
      e.stopPropagation();
      const columnItem = this.closest('.column-item');
      const columnName = columnItem.getAttribute('data-column');
      toggleColumnInModal(columnName);
    });
  });

  // Setup listeners for automatic filter application + dependency reloading
  [selectCentro, selectPunto, selectCanal, selectMaterial, selectProducto, selectMarca].forEach(sel => {
    sel.addEventListener('change', function (e) {
      scheduleFilterApply();
    });
  });

  // Warn on closing/reloading if unsaved changes exist
  window.addEventListener('beforeunload', function (e) {
    if (unsavedChanges) {
      const confirmationMessage = 'Tiene cambios sin guardar. ¿Está seguro de salir?';
      e.returnValue = confirmationMessage; // legacy
      return confirmationMessage;
    }
    return undefined;
  });

  // Initialize: load options and first page
  function loadOptionsAndData() {
    const params = new URLSearchParams();
    const marcas = getSelectValues(selectMarca);
    const centros = getSelectValues(selectCentro);
    const puntos = getSelectValues(selectPunto);
    const canales = getSelectValues(selectCanal);

    if (marcas.length) params.set('marca', marcas.join(','));
    if (centros.length) params.set('centro', centros.join(','));
    if (puntos.length) params.set('punto', puntos.join(','));
    if (canales.length) params.set('canal', canales.join(','));

    const url = params.toString() ? `${endpointOptions}?${params.toString()}` : endpointOptions;

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error('Error al obtener opciones');
        return res.json();
      })
      .then(opts => {
        populateSelect(selectCentro, opts.centros || []);
        populateSelect(selectPunto, opts.puntos || []);
        populateSelect(selectCanal, opts.canales || []);
        populateSelect(selectMaterial, opts.materials || []);
        populateSelect(selectProducto, opts.productos || []);
        populateSelect(selectMarca, opts.marcas || []);
      })
      .catch(err => {
        console.error('Error cargando opciones:', err);
        showNotification('Error cargando opciones de filtro', 'error');
      })
      .finally(() => {
        fetchDataAndRender();
      });
  }

  previousFilters = {
    centro: [],
    punto: [],
    canal: [],
    material: [],
    producto: [],
    marca: []
  };

  // Initialize the application
  loadOptionsAndData();
  initializeColumnControls();
});