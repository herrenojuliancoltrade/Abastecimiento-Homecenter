const API_BASE = "/inventario/api";
const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];

function showMessage(text, type="info", timeout=4000) {
  const el = $("#message");
  if (!el) return;
  el.textContent = text;
  el.className = "message " + type;
  if (timeout) {
    setTimeout(()=> {
      if (el) {
        el.textContent="";
        el.className="message";
      }
    }, timeout);
  }
}

async function fetchItems() {
  const res = await fetch(`${API_BASE}/items`);
  if (!res.ok) {
    showMessage("Error al obtener datos", "error");
    return [];
  }
  return await res.json();
}

function renderTable(items) {
  const tbody = $("#items-table tbody");
  tbody.innerHTML = "";
  items.forEach((it, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx}</td>
      <td>${it["Centro Costos"] || ""}</td>
      <td>${it["Material"] || ""}</td>
      <td>${it["Inventario"] != null ? it["Inventario"] : ""}</td>
      <td>
        <button class="edit" data-index="${idx}">Editar</button>
        <button class="delete" data-index="${idx}">Borrar</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
  $$(".edit").forEach(b => b.addEventListener("click", onEdit));
  $$(".delete").forEach(b => b.addEventListener("click", onDelete));
}

async function refresh() {
  const data = await fetchItems();
  renderTable(data);
}

async function onEdit(e) {
  const idx = Number(e.currentTarget.dataset.index);
  const res = await fetch(`${API_BASE}/items`);
  const items = await res.json();
  const item = items[idx];
  if (!item) {
    showMessage("Elemento no encontrado", "error");
    return;
  }
  $("#input-centro").value = item["Centro Costos"] || "";
  $("#input-material").value = item["Material"] || "";
  $("#input-inventario").value = item["Inventario"] != null ? item["Inventario"] : 0;
  $("#editing-index").value = idx;
}

async function onDelete(e) {
  const idx = Number(e.currentTarget.dataset.index);
  if (!confirm(`¿Borrar registro #${idx}?`)) return;
  const resp = await fetch(`${API_BASE}/items/${encodeURIComponent(idx)}`, { method: "DELETE" });
  if (resp.ok) {
    showMessage("Borrado exitoso", "success");
    refresh();
  } else {
    const j = await resp.json().catch(()=>({}));
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

  // close handlers
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

/* --- DOM ready --- */
document.addEventListener("DOMContentLoaded", () => {
  refresh();

  const btnRefresh = $("#btn-refresh");
  if (btnRefresh) btnRefresh.addEventListener("click", refresh);

  const btnPending = $("#btn-view-pending");
  if (btnPending) btnPending.addEventListener("click", fetchPendingAndOpenModal);

  // Export buttons (Excel / JSON)
  const btnExportExcel = $("#btn-export-excel");
  if (btnExportExcel) btnExportExcel.addEventListener("click", () => {
    window.location = `${API_BASE}/export?format=excel`;
  });
  const btnExportJson = $("#btn-export-json");
  if (btnExportJson) btnExportJson.addEventListener("click", () => {
    window.location = `${API_BASE}/export?format=json`;
  });

  const form = $("#item-form");
  if (form) {
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const centro = $("#input-centro").value.trim();
      const material = $("#input-material").value.trim();
      const inventario = Number($("#input-inventario").value || 0);
      const editing = $("#editing-index").value;
      const payload = { "Centro Costos": centro, "Material": material, "Inventario": inventario };
      if (!material) { showMessage("El Material es obligatorio", "error"); return; }
      if (editing !== "") {
        // editar
        const res = await fetch(`${API_BASE}/items/${encodeURIComponent(editing)}`, {
          method: "PUT",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          showMessage("Actualizado correctamente", "success");
          $("#editing-index").value = "";
          $("#item-form").reset();
          refresh();
        } else {
          const j = await res.json().catch(()=>({}));
          showMessage(j.error || "Error al actualizar", "error");
        }
      } else {
        // crear (permitir duplicados)
        const res = await fetch(`${API_BASE}/items`, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          showMessage("Creado correctamente", "success");
          $("#item-form").reset();
          refresh();
        } else {
          const j = await res.json().catch(()=>({}));
          showMessage(j.error || "Error al crear", "error");
        }
      }
    });
  }

  const btnCancel = $("#btn-cancel-edit");
  if (btnCancel) btnCancel.addEventListener("click", () => {
    $("#editing-index").value = "";
    $("#item-form").reset();
  });

  // Importar
  const btnImport = $("#btn-import");
  if (btnImport) btnImport.addEventListener("click", async () => {
    const f = $("#file-import").files[0];
    if (!f) { showMessage("Selecciona un archivo (.xlsx o .json) para importar", "error"); return; }
    const fd = new FormData();
    fd.append("file", f);
    const res = await fetch(`${API_BASE}/import`, { method: "POST", body: fd });
    const j = await res.json().catch(()=>({}));
    if (res.ok) {
      showMessage(`Importado: ${j.added} nuevos. Total: ${j.total_after}`, "success");
      $("#file-import").value = "";
      refresh();
    } else {
      showMessage(j.error || "Error al importar", "error");
    }
  });

  // Eliminar todo (confirmación triple)
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
      refresh();
    } else {
      const j = await res.json().catch(()=>({}));
      showMessage(j.error || "Error al eliminar todo", "error");
    }
  });
});
