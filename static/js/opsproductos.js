// static/js/opsproductos.js
const API_BASE = "/opsproductos/api";

const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];

function showMessage(text, type="info", timeout=4000) {
  const el = $("#message");
  el.textContent = text;
  el.className = "message " + type;
  if (timeout) {
    setTimeout(()=> { el.textContent=""; el.className="message"; }, timeout);
  }
}

async function fetchProducts() {
  const res = await fetch(`${API_BASE}/products`);
  if (!res.ok) { showMessage("Error al obtener datos", "error"); return []; }
  return await res.json();
}

function renderTable(items) {
  const tbody = $("#products-table tbody");
  tbody.innerHTML = "";
  items.forEach(it => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${it.Material}</td>
      <td>${it.Producto || ""}</td>
      <td>${it.Marca || ""}</td>
      <td>
        <button class="edit" data-material="${it.Material}">Editar</button>
        <button class="delete" data-material="${it.Material}">Borrar</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // attach handlers
  $$(".edit").forEach(b => b.addEventListener("click", onEdit));
  $$(".delete").forEach(b => b.addEventListener("click", onDelete));
}

async function refresh() {
  const data = await fetchProducts();
  renderTable(data);
}

async function onEdit(e) {
  const mat = e.currentTarget.dataset.material;
  const res = await fetch(`${API_BASE}/products`);
  const items = await res.json();
  const item = items.find(x => String(x.Material) === String(mat));
  if (!item) { showMessage("Elemento no encontrado", "error"); return; }
  $("#input-material").value = item.Material;
  $("#input-producto").value = item.Producto || "";
  $("#input-marca").value = item.Marca || "";
  $("#editing-original-material").value = item.Material;
}

async function onDelete(e) {
  const mat = e.currentTarget.dataset.material;
  if (!confirm(`¿Borrar producto Material ${mat}?`)) return;
  const resp = await fetch(`${API_BASE}/products/${encodeURIComponent(mat)}`, { method: "DELETE" });
  if (resp.ok) {
    showMessage("Borrado exitoso", "success");
    refresh();
  } else {
    const j = await resp.json();
    showMessage(j.error || "Error al borrar", "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  refresh();

  $("#btn-refresh").addEventListener("click", refresh);

  $("#product-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const material = $("#input-material").value.trim();
    const producto = $("#input-producto").value.trim();
    const marca = $("#input-marca").value.trim();
    const original = $("#editing-original-material").value;

    const payload = { Material: material, Producto: producto, Marca: marca };

    if (!material) { showMessage("El Material es obligatorio", "error"); return; }

    if (original) {
      // editar
      const res = await fetch(`${API_BASE}/products/${encodeURIComponent(original)}`, {
        method: "PUT",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showMessage("Actualizado correctamente", "success");
        $("#editing-original-material").value = "";
        $("#product-form").reset();
        refresh();
      } else {
        const j = await res.json();
        showMessage(j.error || "Error al actualizar", "error");
      }
    } else {
      // crear
      const res = await fetch(`${API_BASE}/products`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showMessage("Creado correctamente", "success");
        $("#product-form").reset();
        refresh();
      } else {
        const j = await res.json();
        showMessage(j.error || "Error al crear", "error");
      }
    }
  });

  $("#btn-cancel-edit").addEventListener("click", () => {
    $("#editing-original-material").value = "";
    $("#product-form").reset();
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
    if (!f) { showMessage("Selecciona un archivo (.xlsx o .json) para importar", "error"); return; }
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
      showMessage(j.error || "Error al importar", "error");
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
