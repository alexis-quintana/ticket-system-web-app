// Contador de la campana: consulta /notificaciones/contador y actualiza el círculo.
const URL_CONTADOR = '/notificaciones/contador';
const INTERVALO_MS = 30000;

async function actualizarContador() {
  const circulo = document.querySelector('#contador-notificaciones');
  if (!circulo) return;
  try {
    const respuesta = await fetch(URL_CONTADOR, { headers: { Accept: 'application/json' } });
    if (!respuesta.ok) return;
    const { no_leidas } = await respuesta.json();
    circulo.textContent = no_leidas > 99 ? '99+' : String(no_leidas);
    circulo.hidden = no_leidas === 0;
    circulo.parentElement.setAttribute('aria-label', 'Notificaciones: ' + no_leidas + ' no leídas');
  } catch (error) {
    // Sin conexión: se conserva el valor anterior.
  }
}

document.addEventListener('DOMContentLoaded', () => {
  actualizarContador();
  setInterval(actualizarContador, INTERVALO_MS);

  // En la lista, los filtros se aplican al cambiar un selector.
  document.querySelector('#notes-filters')?.addEventListener('change', evento => {
    evento.currentTarget.requestSubmit();
  });
});