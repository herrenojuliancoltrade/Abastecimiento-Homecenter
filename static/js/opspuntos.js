// static/js/opspuntos.js
const API_BASE = "/opspuntos/api";

const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];

function showMessage(text, type="info", timeout=5000) {
  const el = $("#message");
  el.textContent = text;
  el.className = "message " + type;
  if (timeout) {
    setTimeout(()=> { el.textContent=""; el.className="message"; }, timeout);
  }
}

async function fetchPuntos() {
  const res = await fetch(`${API_BASE}/puntos`);
  if (!res.ok) { showMessage("Error al obtener datos", "error"); return []; }
  return await res.json();
}

function renderTable(items) {
  const tbody = $("#puntos-table tbody");
  tbody.innerHTML = "";
  items.forEach(it => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${it["Centro Costos"] || ""}</td>
      <td>${it["Punto de Venta"] || ""}</td>
      <td>${it["Canal o Regional"] || ""}</td>
      <td>${it["Tipo"] || ""}</td>
      <td>
        <button class="edit" data-centro="${encodeURIComponent(it["Centro Costos"] || "")}">Editar</button>
        <button class="delete" data-centro="${encodeURIComponent(it["Centro Costos"] || "")}">Borrar</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // attach handlers
  $$(".edit").forEach(b => b.addEventListener("click", onEdit));
  $$(".delete").forEach(b => b.addEventListener("click", onDelete));
}

async function refresh() {
  const data = await fetchPuntos();
  renderTable(data);
}

async function onEdit(e) {
  // dataset has centro encoded; decode for display
  const centro = decodeURIComponent(e.currentTarget.dataset.centro);
  const res = await fetch(`${API_BASE}/puntos`);
  const items = await res.json();
  const item = items.find(x => String(x["Centro Costos"]) === String(centro));
  if (!item) { showMessage("Elemento no encontrado", "error"); return; }
  $("#input-centro").value = item["Centro Costos"] || "";
  $("#input-punto").value = item["Punto de Venta"] || "";
  $("#input-canal").value = item["Canal o Regional"] || "";
  $("#input-tipo").value = item["Tipo"] || "";
  $("#editing-original-centro").value = item["Centro Costos"] || "";
}

async function onDelete(e) {
  const centro = decodeURIComponent(e.currentTarget.dataset.centro);
  if (!confirm(`¿Borrar punto con Centro Costos ${centro}?`)) return;
  const resp = await fetch(`${API_BASE}/puntos/${encodeURIComponent(centro)}`, { method: "DELETE" });
  if (resp.ok) {
    showMessage("Borrado exitoso", "success");
    refresh();
  } else {
    let j = {};
    try { j = await resp.json(); } catch (err) {}
    showMessage(j.error || "Error al borrar", "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  refresh();

  $("#btn-refresh").addEventListener("click", refresh);

  $("#punto-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const centro = $("#input-centro").value.trim();
    const punto = $("#input-punto").value.trim();
    const canal = $("#input-canal").value.trim();
    const tipo = $("#input-tipo").value.trim();
    const original = $("#editing-original-centro").value;

    const payload = {
      "Centro Costos": centro,
      "Punto de Venta": punto,
      "Canal o Regional": canal,
      "Tipo": tipo
    };

    if (!centro) { showMessage("El Centro Costos es obligatorio", "error"); return; }

    if (original) {
      // editar
      const res = await fetch(`${API_BASE}/puntos/${encodeURIComponent(original)}`, {
        method: "PUT",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showMessage("Actualizado correctamente", "success");
        $("#editing-original-centro").value = "";
        $("#punto-form").reset();
        refresh();
      } else {
        const j = await res.json();
        showMessage(j.error || "Error al actualizar", "error");
      }
    } else {
      // crear
      const res = await fetch(`${API_BASE}/puntos`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showMessage("Creado correctamente", "success");
        $("#punto-form").reset();
        refresh();
      } else {
        const j = await res.json();
        showMessage(j.error || "Error al crear", "error");
      }
    }
  });

  $("#btn-cancel-edit").addEventListener("click", () => {
    $("#editing-original-centro").value = "";
    $("#punto-form").reset();
  });

  // Exportar Excel
  $("#btn-export-excel").addEventListener("click", () => {
    window.location = `${API_BASE}/export?format=excel`;
  });

  // Exportar JSON por compatibilidad
  $("#btn-export-json").addEventListener("click", () => {
    window.location = `${API_BASE}/export?format=json`;
  });

  $("#btn-import").addEventListener("click", async () => {
    const f = $("#file-import").files[0];
    if (!f) { showMessage("Selecciona un archivo (.xlsx, .xls o .json) para importar", "error"); return; }
    const fd = new FormData();
    fd.append("file", f);
    const res = await fetch(`${API_BASE}/import`, { method: "POST", body: fd });
    if (res.ok) {
      const j = await res.json();
      showMessage(`Importado: ${j.added} nuevos. Total: ${j.total_after}`, "success");
      refresh();
    } else {
      const contentType = res.headers.get("content-type") || "";
      let j = {};
      try { if (contentType.includes("application/json")) j = await res.json(); } catch(e){ }
      showMessage(j.error || "Error al importar: " + (j.detail || ""), "error");
    }
  });

  $("#btn-delete-all").addEventListener("click", async () => {
    // Confirmación triple: se muestran 3 dialogs seguidos
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
      const j = await res.json();
      showMessage(j.error || "Error al eliminar todo", "error");
    }
  });

});
