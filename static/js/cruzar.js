// static/js/cruzar.js
document.addEventListener('DOMContentLoaded', function () {
  const statusEl = document.getElementById('status');
  const tbody = document.querySelector('#cruzar-table tbody');
  const btnRefresh = document.getElementById('btn-refresh');
  const btnExport = document.getElementById('btn-export');

  async function loadData() {
    statusEl.textContent = 'Cargando datos...';
    tbody.innerHTML = '';
    try {
      const res = await fetch('/cruzar/api/data');
      const json = await res.json();
      if (json.status !== 'ok') throw new Error(json.message || 'Error al obtener datos');
      const rows = json.data || [];
      if (!rows.length) {
        statusEl.textContent = 'No se encontraron registros.';
        return;
      }
      statusEl.textContent = `Registros: ${rows.length}`;
      for (const r of rows) {
        const tr = document.createElement('tr');

        const cols = [
          'Material','Producto','Marca','Centro Costos','Punto de Venta',
          'Sugerido Claro','Inventario','Transitos','Ventas Actuales',
          'Envío Inventario 3 meses','Sugerido Coltrade','Promedio 3 Meses','Sugerido Final'
        ];

        for (const c of cols) {
          const td = document.createElement('td');
          const val = (r[c] === null || r[c] === undefined) ? '' : String(r[c]);
          td.textContent = val;

          // estilo condicional: columnas Inventario, Transitos, Ventas Actuales, Envío Inventario 3 meses
          if (['Inventario','Transitos','Ventas Actuales','Envío Inventario 3 meses'].includes(c)) {
            const n = parseFloat(val.toString().replace(',', '.'));
            if (!isNaN(n)) {
              if (n >= 0) td.classList.add('cell-positive');
              else td.classList.add('cell-negative');
            }
          }

          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }
    } catch (err) {
      console.error(err);
      statusEl.textContent = 'Error cargando datos: ' + err.message;
    }
  }

  btnRefresh.addEventListener('click', loadData);

  btnExport.addEventListener('click', function () {
    window.location.href = '/cruzar/api/export';
  });

  // carga inicial
  loadData();
});