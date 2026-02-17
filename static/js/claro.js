// static/js/claro.js
const API_BASE = "/claro/api";

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

async function fetchItems() {
  const res = await fetch(`${API_BASE}/items`);
  if (!res.ok) { showMessage("Error al obtener datos", "error"); return []; }
  return await res.json();
}

function renderTable(items) {
  const tbody = $("#items-table tbody");
  tbody.innerHTML = "";
  items.forEach(it => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${it["Material"] ?? ""}</td>
      <td>${it["Producto"] ?? ""}</td>
      <td>${it["Centro Costos"] ?? ""}</td>
      <td>${it["Nombre del Punto"] ?? ""}</td>
      <td>${it["Inventario Claro"] ?? ""}</td>
      <td>${it["Transito Claro"] ?? ""}</td>
      <td>${it["Ventas Pasadas Claro"] ?? ""}</td>
      <td>${it["Ventas Actuales Claro"] ?? ""}</td>
      <td>${it["Sugerido Claro"] ?? ""}</td>
      <td>
        <button class="edit" data-id="${encodeURIComponent(it["id"] || "")}">Editar</button>
        <button class="delete" data-id="${encodeURIComponent(it["id"] || "")}">Borrar</button>
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
  const id = decodeURIComponent(e.currentTarget.dataset.id);
  const res = await fetch(`${API_BASE}/items`);
  const items = await res.json();
  const item = items.find(x => String(x["id"]) === String(id));
  if (!item) { showMessage("Elemento no encontrado", "error"); return; }
  $("#input-material").value = item["Material"] || "";
  $("#input-producto").value = item["Producto"] || "";
  $("#input-centro").value = item["Centro Costos"] || "";
  $("#input-nombre").value = item["Nombre del Punto"] || "";
  $("#input-inventario").value = item["Inventario Claro"] || "";
  $("#input-transito").value = item["Transito Claro"] || "";
  $("#input-vpast").value = item["Ventas Pasadas Claro"] || "";
  $("#input-vactual").value = item["Ventas Actuales Claro"] || "";
  $("#input-sugerido").value = item["Sugerido Claro"] || "";
  $("#editing-original-id").value = item["id"] || "";
}

async function onDelete(e) {
  const id = decodeURIComponent(e.currentTarget.dataset.id);
  if (!confirm(`¿Borrar este registro? (ID: ${id})`)) return;
  const resp = await fetch(`${API_BASE}/items/${encodeURIComponent(id)}`, { method: "DELETE" });
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

  $("#item-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const material = $("#input-material").value.trim();
    const producto = $("#input-producto").value.trim();
    const centro = $("#input-centro").value.trim();
    const nombre = $("#input-nombre").value.trim();
    const inventario = $("#input-inventario").value.trim();
    const transito = $("#input-transito").value.trim();
    const vpast = $("#input-vpast").value.trim();
    const vactual = $("#input-vactual").value.trim();
    const sugerido = $("#input-sugerido").value.trim();
    const originalId = $("#editing-original-id").value;

    // Normalización cliente-side: campos vacíos => 0
    const payload = {
      "Material": material,
      "Producto": producto === "" ? 0 : producto,
      "Centro Costos": centro === "" ? 0 : centro,
      "Nombre del Punto": nombre === "" ? 0 : nombre,
      "Inventario Claro": inventario === "" ? 0 : inventario,
      "Transito Claro": transito === "" ? 0 : transito,
      "Ventas Pasadas Claro": vpast === "" ? 0 : vpast,
      "Ventas Actuales Claro": vactual === "" ? 0 : vactual,
      "Sugerido Claro": sugerido === "" ? 0 : sugerido
    };

    if (!material) { showMessage("El Material es obligatorio", "error"); return; }

    if (originalId) {
      const res = await fetch(`${API_BASE}/items/${encodeURIComponent(originalId)}`, {
        method: "PUT",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showMessage("Actualizado correctamente", "success");
        $("#editing-original-id").value = "";
        $("#item-form").reset();
        refresh();
      } else {
        const j = await res.json();
        showMessage(j.error || "Error al actualizar", "error");
      }
    } else {
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
        const j = await res.json();
        showMessage(j.error || "Error al crear", "error");
      }
    }
  });

  $("#btn-cancel-edit").addEventListener("click", () => {
    $("#editing-original-id").value = "";
    $("#item-form").reset();
  });

  $("#btn-export-excel").addEventListener("click", () => {
    window.location = `${API_BASE}/export?format=excel`;
  });
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
      if (j.added_materials && j.added_materials.length) {
        console.log("Materiales importados:", j.added_materials);
      }
      refresh();
    } else {
      const contentType = res.headers.get("content-type") || "";
      let j = {};
      try { if (contentType.includes("application/json")) j = await res.json(); } catch(e){ }
      showMessage(j.error || "Error al importar: " + (j.detail || ""), "error");
    }
  });

  $("#btn-delete-all").addEventListener("click", async () => {
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
