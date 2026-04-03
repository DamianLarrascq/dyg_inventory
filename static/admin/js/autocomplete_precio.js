/**
 * autocomplete_precio.js
 * Al seleccionar un servicio en el inline de AtencionServicio,
 * autocompleta el campo precio_aplicado con el precio actual del servicio.
 *
 * Requiere que la URL /admin/core/servicio/<id>/change/ devuelva el precio
 * en el título. Como alternativa simple, exponemos los precios via data-precio
 * en el select usando un widget personalizado, o hacemos un fetch a la API
 * del admin. Aquí usamos un fetch ligero al endpoint de change para extraer
 * el precio desde el campo readonly del form.
 *
 * Solución más robusta: agregar una vista JSON mínima.
 * Por simplicidad se usa el atributo data-precio que Django inyecta
 * si se usa autocomplete_fields. Este script funciona con selects normales.
 */
(function () {
  "use strict";

  function getPrecioServicio(servicioId, callback) {
    // Fetch al endpoint de cambio del servicio para leer el precio
    fetch(`/admin/core/servicio/${servicioId}/change/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((r) => r.text())
      .then((html) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");
        const precioInput = doc.querySelector("#id_precio");
        if (precioInput) {
          callback(precioInput.value);
        }
      })
      .catch(() => {});
  }

  function bindServicioSelects() {
    document.querySelectorAll("[id$='-servicio']").forEach((select) => {
      if (select.dataset.autoPrecioBound) return;
      select.dataset.autoPrecioBound = "1";

      select.addEventListener("change", function () {
        const servicioId = this.value;
        if (!servicioId) return;

        // Encontrar el input precio_aplicado en la misma fila
        const row = this.closest("tr");
        if (!row) return;
        const precioInput = row.querySelector("[id$='-precio_aplicado']");
        if (!precioInput || precioInput.value) return; // no sobreescribir si ya tiene valor

        getPrecioServicio(servicioId, (precio) => {
          precioInput.value = precio;
        });
      });
    });
  }

  // Ejecutar al cargar y también cuando Django agrega filas dinámicas al inline
  document.addEventListener("DOMContentLoaded", bindServicioSelects);
  document.addEventListener("formset:added", bindServicioSelects);
})();
