// Campana de notificaciones: contador, desplegable con las últimas y marcado sin recargar.
const URL_CONTADOR = '/notificaciones/contador';
const URL_RECIENTES = '/notificaciones/recientes';
const URL_TODAS = '/notificaciones/leer-todas';
const INTERVALO_MS = 30000;
const CABECERAS_AJAX = { Accept: 'application/json', 'X-Requested-With': 'fetch' };

const ICONOS = { asignacion: 'person-check', cambio_estado: 'arrow-repeat', comentario: 'chat-left-text' };

function pintarContador(noLeidas) {
  const circulo = document.querySelector('#contador-notificaciones');
  if (circulo) {
    circulo.textContent = noLeidas > 99 ? '99+' : String(noLeidas);
    circulo.hidden = noLeidas === 0;
    const boton = circulo.parentElement;
    boton.setAttribute('aria-label', 'Notificaciones: ' + noLeidas + ' no leídas');
  }
  const lectura = document.querySelector('#notif-read-all');
  if (lectura) lectura.disabled = noLeidas === 0;
}

async function actualizarContador() {
  if (!document.querySelector('#contador-notificaciones')) return;
  try {
    const respuesta = await fetch(URL_CONTADOR, { headers: { Accept: 'application/json' } });
    if (!respuesta.ok) return;
    const { no_leidas } = await respuesta.json();
    pintarContador(no_leidas);
  } catch (error) {
    // Sin conexión: se conserva el valor anterior.
  }
}

/* ---------- Desplegable ---------- */
function elemento(etiqueta, clase, texto) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

function crearItem(n) {
  const li = elemento('li');
  const enlace = elemento('a', 'notif-item' + (n.leida ? '' : ' is-unread'));
  enlace.href = n.url;
  enlace.dataset.id = n.id;
  enlace.dataset.leida = n.leida ? '1' : '0';
  const icono = elemento('i', 'bi bi-' + (ICONOS[n.tipo] || 'bell') + ' notif-icon');
  icono.setAttribute('aria-hidden', 'true');
  const cuerpo = elemento('span', 'notif-body');
  cuerpo.append(elemento('strong', '', n.titulo), elemento('span', 'notif-text', n.mensaje), elemento('small', '', n.hace));
  enlace.append(icono, cuerpo);
  if (!n.leida) enlace.append(elemento('span', 'notif-dot'));
  li.append(enlace);
  return li;
}

async function cargarRecientes() {
  const lista = document.querySelector('#notif-list');
  if (!lista) return;
  try {
    const respuesta = await fetch(URL_RECIENTES, { headers: { Accept: 'application/json' } });
    if (!respuesta.ok) return;
    const datos = await respuesta.json();
    lista.replaceChildren();
    if (!datos.items.length) {
      lista.append(elemento('li', 'notif-empty', 'No tienes notificaciones.'));
    } else {
      datos.items.forEach(n => lista.append(crearItem(n)));
    }
    pintarContador(datos.no_leidas);
  } catch (error) {
    lista.replaceChildren(elemento('li', 'notif-empty', 'No se pudieron cargar las notificaciones.'));
  }
}

async function enviar(url) {
  const respuesta = await fetch(url, { method: 'POST', headers: CABECERAS_AJAX });
  if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
  return respuesta.json();
}

function iniciarDesplegable() {
  const boton = document.querySelector('#notif-toggle');
  const panel = document.querySelector('#notif-panel');
  if (!boton || !panel) return;

  const abrir = abierto => {
    panel.hidden = !abierto;
    boton.setAttribute('aria-expanded', String(abierto));
    if (abierto) cargarRecientes();
  };

  boton.addEventListener('click', evento => {
    evento.stopPropagation();
    abrir(panel.hidden);
  });
  document.addEventListener('click', evento => {
    if (!panel.hidden && !panel.contains(evento.target)) abrir(false);
  });
  document.addEventListener('keydown', evento => {
    if (evento.key === 'Escape' && !panel.hidden) {
      abrir(false);
      boton.focus();
    }
  });

  // Abrir una notificación la marca como leída y lleva al ticket.
  panel.querySelector('#notif-list').addEventListener('click', async evento => {
    const enlace = evento.target.closest('a.notif-item');
    if (!enlace) return;
    if (enlace.dataset.leida === '1') return;
    evento.preventDefault();
    try {
      await enviar('/notificaciones/' + enlace.dataset.id + '/leer');
    } catch (error) {
      // Si falla el marcado igual se navega: el aviso seguirá como no leído.
    }
    window.location.href = enlace.href;
  });

  panel.querySelector('#notif-read-all').addEventListener('click', async () => {
    try {
      const datos = await enviar(URL_TODAS);
      pintarContador(datos.no_leidas);
      cargarRecientes();
    } catch (error) {
      // Se conserva el estado anterior.
    }
  });
}

/* ---------- Página /notificaciones ---------- */
function marcarTarjeta(tarjeta) {
  tarjeta.classList.remove('is-unread');
  const estado = tarjeta.querySelector('.note-status');
  if (estado) estado.textContent = 'Leída';
  tarjeta.querySelector('form[data-ajax="una"]')?.remove();
}

function actualizarResumen(noLeidas) {
  const total = document.querySelector('#notes-unread');
  if (total) total.textContent = String(noLeidas);
  const todas = document.querySelector('#notes-read-all');
  if (todas) todas.disabled = noLeidas === 0;
}

function iniciarEliminarLeidas(formulario) {
  const boton = formulario.querySelector('button');
  let temporizador;
  formulario.addEventListener('submit', async evento => {
    evento.preventDefault();
    // Primer clic: pide confirmación en el mismo botón. Segundo clic: elimina.
    if (!boton.dataset.confirmar) {
      boton.dataset.confirmar = '1';
      boton.textContent = 'Confirmar: eliminar leídas';
      boton.classList.add('danger');
      temporizador = setTimeout(() => {
        delete boton.dataset.confirmar;
        boton.textContent = boton.dataset.texto;
        boton.classList.remove('danger');
      }, 4000);
      return;
    }
    clearTimeout(temporizador);
    try {
      const datos = await enviar(formulario.action);
      document.querySelectorAll('.note-card:not(.is-unread)').forEach(t => t.remove());
      actualizarResumen(datos.no_leidas);
      pintarContador(datos.no_leidas);
      location.reload();
    } catch (error) {
      formulario.submit();
    }
  });
}

function iniciarLista() {
  document.querySelectorAll('form[data-ajax]').forEach(formulario => {
    if (formulario.dataset.ajax === 'eliminar-leidas') {
      iniciarEliminarLeidas(formulario);
      return;
    }
    formulario.addEventListener('submit', async evento => {
      evento.preventDefault();
      try {
        const datos = await enviar(formulario.action);
        if (formulario.dataset.ajax === 'una') {
          marcarTarjeta(formulario.closest('.note-card'));
        } else if (formulario.dataset.ajax === 'eliminar') {
          formulario.closest('.note-card').remove();
        } else {
          document.querySelectorAll('.note-card.is-unread').forEach(marcarTarjeta);
        }
        actualizarResumen(datos.no_leidas);
        pintarContador(datos.no_leidas);
        if (formulario.dataset.ajax === 'eliminar') {
          location.reload(); // refresca el resumen "X de Y" y el estado vacío
          return;
        }
        // Con el filtro "No leídas" la tarjeta ya no corresponde: se recarga para reflejarlo.
        if (new URLSearchParams(location.search).get('lectura') === 'no_leidas') location.reload();
      } catch (error) {
        formulario.submit();
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  actualizarContador();
  setInterval(actualizarContador, INTERVALO_MS);
  iniciarDesplegable();
  iniciarLista();

  // En la lista, los filtros se aplican al cambiar un selector.
  document.querySelector('#notes-filters')?.addEventListener('change', evento => {
    evento.currentTarget.requestSubmit();
  });
});
