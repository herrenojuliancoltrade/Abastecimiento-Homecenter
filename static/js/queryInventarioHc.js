document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('excel-file');
  const previewButton = document.getElementById('btn-preview');
  const downloadButton = document.getElementById('btn-download');
  const statusMessage = document.getElementById('status-message');
  const previewContainer = document.getElementById('preview-container');
  const previewMeta = document.getElementById('preview-meta');
  const tableHead = document.querySelector('#preview-table thead');
  const tableBody = document.querySelector('#preview-table tbody');

  const config = window.queryInventarioHcConfig || {};
  const previewUrl = config.previewUrl;
  const processUrl = config.processUrl;

  const showMessage = (message, type = 'info') => {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
  };

  const getSelectedFile = () => {
    if (!fileInput.files || !fileInput.files.length) {
      showMessage('Selecciona un archivo Excel antes de continuar.', 'error');
      return null;
    }
    return fileInput.files[0];
  };

  const renderPreviewTable = (columns, rows) => {
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';

    const headerRow = document.createElement('tr');
    columns.forEach((column) => {
      const th = document.createElement('th');
      th.textContent = column;
      headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);

    rows.forEach((row) => {
      const tr = document.createElement('tr');
      columns.forEach((column) => {
        const td = document.createElement('td');
        td.textContent = row[column] ?? '';
        tr.appendChild(td);
      });
      tableBody.appendChild(tr);
    });
  };

  previewButton.addEventListener('click', async () => {
    const file = getSelectedFile();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    previewButton.disabled = true;
    showMessage('Procesando vista previa...', 'info');

    try {
      const response = await fetch(previewUrl, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'No fue posible previsualizar el archivo.');
      }

      renderPreviewTable(data.columns || [], data.rows || []);
      previewMeta.textContent = `Filas filtradas encontradas: ${data.total_rows ?? 0}`;
      previewContainer.classList.remove('hidden');
      showMessage('Vista previa cargada correctamente.', 'success');
    } catch (error) {
      previewContainer.classList.add('hidden');
      showMessage(error.message || 'Error inesperado al generar vista previa.', 'error');
    } finally {
      previewButton.disabled = false;
    }
  });

  downloadButton.addEventListener('click', async () => {
    const file = getSelectedFile();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    downloadButton.disabled = true;
    showMessage('Generando archivo para descarga...', 'info');

    try {
      const response = await fetch(processUrl, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'No fue posible procesar el archivo.');
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get('Content-Disposition') || '';
      let filename = 'inventario_hc_filtrado.xlsx';

      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }

      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);

      showMessage('Archivo filtrado generado y descargado.', 'success');
    } catch (error) {
      showMessage(error.message || 'Error inesperado al procesar el archivo.', 'error');
    } finally {
      downloadButton.disabled = false;
    }
  });
});
