// static/js/compras.js
document.addEventListener('DOMContentLoaded', function () {
  const tableBody = document.querySelector('#compras-table tbody');
  const statusEl = document.getElementById('status');
  const refreshBtn = document.getElementById('refresh-btn');
  const exportBtn = document.getElementById('export-btn');
  const searchInput = document.getElementById('search-input');
  const importForm = document.getElementById('import-form');
  const fileInput = document.getElementById('file-input');

  // rutas relativas
  const API_LIST = 'api/compras';
  const API_IMPORT = 'api/import';
  const API_EXPORT_XLSX = 'api/export_excel';
  const API_UPDATE = 'api/update';

  let lastData = [];

  async function fetchCompras(showStatus = true) {
    if (showStatus) setStatus('Cargando...');
    try {
      const res = await fetch(API_LIST, {cache: 'no-store'});
      if (!res.ok) {
        const err = await res.json().catch(()=>({}));
        throw new Error(err.error || res.statusText || 'Error al obtener datos');
      }
      const data = await res.json();
      lastData = data;
      if (showStatus) setStatus(`Cargados ${data.length} registros.`);
      renderTable(data);
      return data;
    } catch (err) {
      console.error(err);
      setStatus('Error: ' + (err.message || err));
      tableBody.innerHTML = '';
      return [];
    }
  }

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function renderTable(items) {
    tableBody.innerHTML = '';
    const q = (searchInput.value || '').trim().toLowerCase();
    const filtered = items.filter(it => {
      if (!q) return true;
      return (String(it.Material || '') + ' ' + String(it.Producto || '') + ' ' + String(it.Marca || '')).toLowerCase().includes(q);
    });

    if (filtered.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" style="padding:14px; color:#666;">No hay registros</td></tr>`;
      return;
    }

    const frag = document.createDocumentFragment();
    filtered.forEach(it => {
      const tr = document.createElement('tr');

      const tdMat = document.createElement('td');
      tdMat.textContent = it.Material || '';
      tr.appendChild(tdMat);

      const tdProd = document.createElement('td');
      tdProd.textContent = it.Producto || '';
      tr.appendChild(tdProd);

      const tdMarca = document.createElement('td');
      tdMarca.textContent = it.Marca || '';
      tr.appendChild(tdMarca);

      const tdSug = document.createElement('td');
      tdSug.textContent = it.Sugerido !== undefined ? String(it.Sugerido) : '';
      tr.appendChild(tdSug);

      // Confirmar: checkbox editable
      const tdConf = document.createElement('td');
      tdConf.classList.add('center-cell');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = !!it.Confirmar;
      cb.dataset.material = it.Material || '';
      cb.title = 'Marcar para confirmar (Aprobado)';
      cb.addEventListener('change', onConfirmChange);
      tdConf.appendChild(cb);
      tr.appendChild(tdConf);

      // Observacion: textarea/input + spellcheck enabled
      const tdObs = document.createElement('td');
      const txt = document.createElement('input');
      txt.type = 'text';
      txt.className = 'obs-input';
      txt.spellcheck = true; // habilita corrección ortográfica del navegador
      txt.value = it.Observacion || '';
      txt.placeholder = 'Escribe observación...';
      txt.dataset.material = it.Material || '';
      tdObs.appendChild(txt);
      tr.appendChild(tdObs);

      // Acciones: guardar comentario
      const tdAcc = document.createElement('td');
      tdAcc.className = 'row-actions';
      const saveBtn = document.createElement('button');
      saveBtn.className = 'save-btn';
      saveBtn.textContent = 'Guardar';
      saveBtn.dataset.material = it.Material || '';
      saveBtn.addEventListener('click', onSaveComment);
      tdAcc.appendChild(saveBtn);

      tr.appendChild(tdAcc);

      frag.appendChild(tr);
    });

    tableBody.appendChild(frag);
  }

  // Evento cuando se cambia la casilla Confirmar
  async function onConfirmChange(ev) {
    const cb = ev.target;
    const material = cb.dataset.material;
    const confirmar = cb.checked;
    setStatus(`Actualizando estado para ${material}...`);
    try {
      const res = await fetch(API_UPDATE, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({Material: material, Confirmar: confirmar})
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));
      setStatus(`Estado actualizado: ${material} -> ${confirmar ? 'Aprobado' : 'No aprobado'}`);
    } catch (err) {
      console.error(err);
      setStatus('Error actualizando estado: ' + (err.message || err));
      // re-hacer toggle visual si falla
      cb.checked = !confirmar;
    }
  }

  // Evento para guardar comentario (Observacion)
  async function onSaveComment(ev) {
    ev.preventDefault();
    const btn = ev.target;
    const material = btn.dataset.material;
    // encontrar el input asociado (en la misma fila)
    const row = btn.closest('tr');
    if (!row) return;
    const input = row.querySelector('.obs-input');
    const observ = input ? input.value : '';
    setStatus(`Guardando observación para ${material}...`);
    try {
      const res = await fetch(API_UPDATE, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({Material: material, Observacion: observ})
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));
      setStatus(`Observación guardada para ${material}`);
    } catch (err) {
      console.error(err);
      setStatus('Error guardando observación: ' + (err.message || err));
    }
  }

  refreshBtn.addEventListener('click', () => fetchCompras());

  searchInput.addEventListener('input', () => {
    // filtrar con último dataset si lo tenemos, para responsividad
    if (lastData.length > 0) {
      renderTable(lastData);
    } else {
      fetchCompras(false);
    }
  });

  exportBtn.addEventListener('click', async () => {
    setStatus('Generando Excel...');
    try {
      const res = await fetch(API_EXPORT_XLSX, {cache: 'no-store'});
      if (!res.ok) {
        const err = await res.json().catch(()=>({}));
        throw new Error(err.error || res.statusText || 'Error al exportar');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'compras.xlsx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatus('Excel generado');
    } catch (err) {
      console.error(err);
      setStatus('Error exportando Excel: ' + (err.message || err));
    }
  });

  importForm.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      setStatus('Seleccione un archivo para importar (.xlsx, .xls, .csv, .json)');
      return;
    }
    setStatus('Importando archivo...');
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch(API_IMPORT, {
        method: 'POST',
        body: fd
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || JSON.stringify(data));
      }
      setStatus(`Import OK — agregados: ${data.added}, actualizados: ${data.updated}. Total después: ${data.total_after}`);
      await fetchCompras();
      fileInput.value = "";
    } catch (err) {
      console.error(err);
      setStatus('Error en import: ' + (err.message || err));
    }
  });

  // cargar inicialmente
  fetchCompras();
});
