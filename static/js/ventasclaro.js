const API_BASE = "/ventasclaro/api";

const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];

function showMessage(text, type="info", timeout=5000) {
  const el = $("#message");
  if (!el) return;
  el.textContent = text;
  el.className = "message " + type;
  if (timeout) {
    setTimeout(()=> { if (el) { el.textContent=""; el.className="message"; } }, timeout);
  }
}

let allData = [];      // datos crudos desde backend
let filteredData = []; // datos mostrados según filtro
let currentFilters = { start: null, end: null }; // fechas ISO: YYYY-MM-DD
let isImporting = false; // Bandera para controlar estado de importación

async function fetchVentas() {
  const res = await fetch(`${API_BASE}/ventas`);
  if (!res.ok) { showMessage("Error al obtener datos", "error"); return []; }
  return await res.json();
}

function renderTable(items) {
  const tbody = $("#ventas-table tbody");
  tbody.innerHTML = "";
  items.forEach((it, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx}</td>
      <td>${it["Centro Costos"] || ""}</td>
      <td>${it["Material"] || ""}</td>
      <td>${it["Fecha Venta"] || ""}</td>
      <td>${it["Cantidad"] != null ? it["Cantidad"] : ""}</td>
      <td>
        <button class="edit" data-idx="${idx}">Editar</button>
        <button class="delete" data-idx="${idx}">Borrar</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  $$(".edit").forEach(b => b.addEventListener("click", onEdit));
  $$(".delete").forEach(b => b.addEventListener("click", onDelete));
}

function applyDateFilterToData(data, start, end) {
  if (!start && !end) return [...data];
  const s = start ? new Date(start + 'T00:00:00') : null;
  const e = end ? new Date(end + 'T23:59:59') : null;
  return data.filter(d => {
    const f = d["Fecha Venta"];
    if (!f) return false; // entradas sin fecha no se muestran en el filtro
    // try parse ISO yyyy-mm-dd
    const dt = new Date(f + 'T00:00:00');
    if (isNaN(dt.getTime())) return false;
    if (s && dt < s) return false;
    if (e && dt > e) return false;
    return true;
  });
}

async function refresh() {
  allData = await fetchVentas();
  // aplicar filtro actual
  filteredData = applyDateFilterToData(allData, currentFilters.start, currentFilters.end);
  renderTable(filteredData);
}

/* --- Edición / borrado --- */
async function onEdit(e) {
  const idx = Number(e.currentTarget.dataset.idx);
  const item = filteredData[idx];
  if (!item) { showMessage("Elemento no encontrado", "error"); return; }
  $("#input-centro").value = item["Centro Costos"] || "";
  $("#input-material").value = item["Material"] || "";
  $("#input-fecha").value = item["Fecha Venta"] || "";
  $("#input-cantidad").value = item["Cantidad"] != null ? item["Cantidad"] : 0;
  // store original index relative to the complete dataset: find global index
  const globalIdx = allData.findIndex(d => {
    return d["Centro Costos"] === item["Centro Costos"]
      && d["Material"] === item["Material"]
      && (d["Fecha Venta"] || "") === (item["Fecha Venta"] || "")
      && String(d["Cantidad"]) === String(item["Cantidad"]);
  });
  $("#editing-original-idx").value = globalIdx >= 0 ? String(globalIdx) : "";
}

async function onDelete(e) {
  const idx = Number(e.currentTarget.dataset.idx);
  const item = filteredData[idx];
  if (!item) { showMessage("Elemento no encontrado", "error"); return; }
  // find global index
  const globalIdx = allData.findIndex(d => {
    return d["Centro Costos"] === item["Centro Costos"]
      && d["Material"] === item["Material"]
      && (d["Fecha Venta"] || "") === (item["Fecha Venta"] || "")
      && String(d["Cantidad"]) === String(item["Cantidad"]);
  });
  if (globalIdx < 0) {
    showMessage("No se pudo determinar el índice global para borrado", "error");
    return;
  }
  if (!confirm(`¿Borrar venta en la fila #${globalIdx}?`)) return;
  const resp = await fetch(`${API_BASE}/ventas/${encodeURIComponent(globalIdx)}`, { method: "DELETE" });
  if (resp.ok) {
    showMessage("Borrado exitoso", "success");
    await refresh();
  } else {
    let j = {};
    try { j = await resp.json(); } catch (err) {}
    showMessage(j.error || "Error al borrar", "error");
  }
}

/* --- Modal pendientes --- */
function openPendingModal(materials = [], centros = []) {
  const modal = $("#pending-modal");
  if (!modal) return;
  const uniqMats = Array.from(new Set((materials || []).map(m => String(m).trim()).filter(Boolean))).sort();
  const uniqCents = Array.from(new Set((centros || []).map(c => String(c).trim()).filter(Boolean))).sort();
  const mlist = $("#modal-materials-list");
  const clist = $("#modal-centros-list");
  mlist.innerHTML = "";
  clist.innerHTML = "";
  if (uniqCents.length === 0) {
    const li = document.createElement("li"); li.textContent = "(ninguno)"; clist.appendChild(li);
  } else {
    uniqCents.forEach(c => {
      const li = document.createElement("li"); li.textContent = c; clist.appendChild(li);
    });
  }
  if (uniqMats.length === 0) {
    const li = document.createElement("li"); li.textContent = "(ninguno)"; mlist.appendChild(li);
  } else {
    uniqMats.forEach(m => {
      const li = document.createElement("li"); li.textContent = m; mlist.appendChild(li);
    });
  }

  modal.style.display = "flex";

  const close = () => { modal.style.display = "none"; };
  $("#modal-close").onclick = close;
  $("#modal-close-btn").onclick = close;
  $("#modal-backdrop").onclick = close;
}

async function fetchPendingAndOpenModal() {
  try {
    const res = await fetch(`${API_BASE}/pending`);
    if (!res.ok) {
      showMessage("No se pudo obtener pendientes", "error");
      return;
    }
    const j = await res.json();
    const mats = j.missing_materials || [];
    const cents = j.missing_centros || [];
    openPendingModal(mats, cents);
  } catch (e) {
    showMessage("Error al obtener pendientes", "error");
  }
}

/* --- Meses (summary + modal) --- */
async function loadMonthsAndPreview() {
  try {
    const res = await fetch(`${API_BASE}/months`);
    if (!res.ok) { 
      $("#months-preview").textContent = "(no disponible)"; 
      return; 
    }
    const j = await res.json();
    const months = j.months || [];
    $("#months-preview").textContent = months.length ? months.slice(0,3).join(", ") + (months.length > 3 ? "..." : "") : "(sin ventas)";
    const list = $("#months-list");
    list.innerHTML = "";
    if (months.length === 0) {
      const li = document.createElement("li"); 
      li.textContent = "(sin ventas)"; 
      list.appendChild(li);
    } else {
      months.forEach(m => {
        const li = document.createElement("li"); 
        li.textContent = m; 
        list.appendChild(li);
      });
    }
  } catch (e) {
    console.error("Error loading months:", e);
    $("#months-preview").textContent = "(error)";
  }
}

function openMonthsModal() {
  const modal = $("#months-modal");
  if (!modal) return;
  modal.style.display = "flex";
  const close = () => { modal.style.display = "none"; };
  $("#months-close").onclick = close;
  $("#months-close-btn").onclick = close;
  $("#months-backdrop").onclick = close;
}

/* --- filtros: aplicar / limpiar / borrar filtrados --- */
function readFilterInputs() {
  const s = $("#filter-start").value || null;
  const e = $("#filter-end").value || null;
  return { start: s, end: e };
}

async function onApplyFilter() {
  const f = readFilterInputs();
  currentFilters.start = f.start;
  currentFilters.end = f.end;
  filteredData = applyDateFilterToData(allData, currentFilters.start, currentFilters.end);
  renderTable(filteredData);
  showMessage("Filtro aplicado", "success", 2000);
}

async function onClearFilter() {
  currentFilters.start = null;
  currentFilters.end = null;
  $("#filter-start").value = "";
  $("#filter-end").value = "";
  filteredData = [...allData];
  renderTable(filteredData);
  showMessage("Filtros borrados", "info", 2000);
}

async function onDeleteFiltered() {
  // require at least one filter value to avoid accidental delete-all
  if (!currentFilters.start && !currentFilters.end) {
    showMessage("Aplica un filtro por fecha antes de borrar filtrados.", "error", 4000);
    return;
  }
  
  const filteredCount = applyDateFilterToData(allData, currentFilters.start, currentFilters.end).length;
  if (filteredCount === 0) {
    showMessage("No hay registros que coincidan con el filtro actual.", "warning", 4000);
    return;
  }
  
  if (!confirm(`ADVERTENCIA: Esto borrará ${filteredCount} registro(s) que coinciden con el filtro de fecha. ¿Deseas continuar?`)) return;
  
  try {
    const res = await fetch(`${API_BASE}/delete_filtered`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ 
        start_date: currentFilters.start, 
        end_date: currentFilters.end 
      })
    });
    const j = await res.json().catch(()=>({}));
    if (res.ok) {
      showMessage(`Eliminados: ${j.deleted || 0}. Restantes: ${j.remaining || 0}`, "success", 5000);
      // refrescar datos
      await refresh();
      await loadMonthsAndPreview();
    } else {
      showMessage(j.error || "Error al borrar filtrados", "error", 4000);
    }
  } catch (e) {
    showMessage("Error al borrar filtrados", "error");
  }
}

/* --- Importación con protección --- */
async function handleImport() {
  if (isImporting) {
    showMessage("Ya hay una importación en proceso. Espere a que termine.", "error", 3000);
    return;
  }

  const f = $("#file-import").files[0];
  if (!f) { 
    showMessage("Selecciona un archivo (.xlsx, .xls o .json) para importar", "error"); 
    return; 
  }

  // Deshabilitar el botón de importación
  isImporting = true;
  const btnImport = $("#btn-import");
  const originalText = btnImport.textContent;
  btnImport.textContent = "Importando...";
  btnImport.disabled = true;

  try {
    const fd = new FormData();
    fd.append("file", f);
    const res = await fetch(`${API_BASE}/import`, { method: "POST", body: fd });
    const j = await res.json().catch(()=>({}));
    
    if (res.ok) {
      showMessage(`Importado: ${j.added} nuevos. Total: ${j.total_after}`, "success", 5000);
      $("#file-import").value = "";
      await refresh();
      await loadMonthsAndPreview();
    } else if (res.status === 429) {
      // Error 429: En proceso de importación
      showMessage(j.error || "En proceso de importación, espere antes de intentar nuevamente", "error", 5000);
    } else {
      showMessage(j.error || "Error al importar: " + (j.detail || ""), "error");
    }
  } catch (e) {
    showMessage("Error de conexión al importar", "error");
  } finally {
    // Rehabilitar el botón después de 30 segundos (o inmediatamente si no fue un error 429)
    setTimeout(() => {
      isImporting = false;
      btnImport.textContent = originalText;
      btnImport.disabled = false;
    }, 30000); // 30 segundos
  }
}

/* --- DOM ready --- */
document.addEventListener("DOMContentLoaded", () => {
  refresh();
  loadMonthsAndPreview();

  // refrescar
  const btnRefresh = $("#btn-refresh");
  if (btnRefresh) btnRefresh.addEventListener("click", () => {
    refresh();
    loadMonthsAndPreview();
  });

  // ver pendientes
  const btnPending = $("#btn-view-pending");
  if (btnPending) btnPending.addEventListener("click", fetchPendingAndOpenModal);

  // ver meses
  const btnMonths = $("#btn-view-months");
  if (btnMonths) btnMonths.addEventListener("click", openMonthsModal);

  // export buttons (Excel / JSON)
  const btnExportExcel = $("#btn-export-excel");
  if (btnExportExcel) btnExportExcel.addEventListener("click", () => {
    window.location = `${API_BASE}/export?format=excel`;
  });
  const btnExportJson = $("#btn-export-json");
  if (btnExportJson) btnExportJson.addEventListener("click", () => {
    window.location = `${API_BASE}/export?format=json`;
  });

  // formulario (crear / editar)
  const ventaForm = $("#venta-form");
  if (ventaForm) {
    ventaForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();

      const centro = $("#input-centro").value.trim();
      const material = $("#input-material").value.trim();
      const fecha = $("#input-fecha").value;
      const cantidad_raw = $("#input-cantidad").value;
      const original = $("#editing-original-idx").value;

      if (!centro || !material) {
        showMessage("Centro Costos y Material son obligatorios", "error");
        return;
      }

      let cantidad = 0;
      try {
        cantidad = cantidad_raw === "" ? 0 : Number(cantidad_raw);
        if (Number.isNaN(cantidad)) throw new Error("NaN");
      } catch (e) {
        showMessage("Cantidad inválida", "error");
        return;
      }

      const payload = {
        "Centro Costos": centro,
        "Material": material,
        "Fecha Venta": fecha,
        "Cantidad": cantidad
      };

      if (original !== "") {
        const idx = Number(original);
        const res = await fetch(`${API_BASE}/ventas/${encodeURIComponent(idx)}`, {
          method: "PUT",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify(payload)
        });
        const j = await res.json().catch(()=>({}));
        if (res.ok) {
          showMessage("Actualizado correctamente", "success");
          $("#editing-original-idx").value = "";
          $("#venta-form").reset();
          await refresh();
          await loadMonthsAndPreview();
        } else {
          showMessage(j.error || "Error al actualizar", "error");
        }
      } else {
        const res = await fetch(`${API_BASE}/ventas`, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify(payload)
        });
        const j = await res.json().catch(()=>({}));
        if (res.ok) {
          showMessage("Creado correctamente", "success", 4000);
          $("#venta-form").reset();
          await refresh();
          await loadMonthsAndPreview();
        } else {
          showMessage(j.error || "Error al crear", "error");
        }
      }
    });
  }

  // cancelar edición
  const btnCancel = $("#btn-cancel-edit");
  if (btnCancel) btnCancel.addEventListener("click", () => {
    $("#editing-original-idx").value = "";
    $("#venta-form").reset();
  });

  // import - usando la nueva función protegida
  const btnImport = $("#btn-import");
  if (btnImport) btnImport.addEventListener("click", handleImport);

  // borrar todo (confirmación triple)
  const btnDeleteAll = $("#btn-delete-all");
  if (btnDeleteAll) btnDeleteAll.addEventListener("click", async () => {
    if (!confirm("ADVERTENCIA: Esto eliminará TODOS los datos. ¿Estás seguro?")) return;
    if (!confirm("ESTA ACCIÓN ES IRREVERSIBLE. ¿Confirmas que deseas continuar?")) return;
    if (!confirm("ÚLTIMA CONFIRMACIÓN: ¿Deseas eliminar TODO ahora?")) return;

    const res = await fetch(`${API_BASE}/delete_all`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ confirmaciones: 3 })
    });
    if (res.ok) {
      showMessage("Todos los datos eliminados", "success");
      await refresh();
      await loadMonthsAndPreview();
    } else {
      const j = await res.json().catch(()=>({}));
      showMessage(j.error || "Error al eliminar todo", "error");
    }
  });

  // filtros: apply / clear / delete filtered
  const btnApply = $("#btn-apply-filter");
  if (btnApply) btnApply.addEventListener("click", onApplyFilter);
  const btnClear = $("#btn-clear-filter");
  if (btnClear) btnClear.addEventListener("click", onClearFilter);
  const btnDeleteFiltered = $("#btn-delete-filtered");
  if (btnDeleteFiltered) btnDeleteFiltered.addEventListener("click", onDeleteFiltered);
});