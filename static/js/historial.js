// Módulo 3: cambiar estado (comentario obligatorio), asignar técnico y quitar la asignación.
// Mismo patrón de clase: validar en JS + fetch a Flask + mostrar respuesta.
const $ = id => document.getElementById(id);
const formEstado = $('form-estado');
const formAsignar = $('form-asignar');   // solo existe para el Administrador
const formQuitar = $('form-quitar');     // solo existe para el Administrador
let ticketActual = null;

// ---------- utilidades de validación (mismas clases que usuarios.js) ----------
const showError = (input, msg) => {
    const f = input.closest('.form-field');
    f.classList.remove('success'); f.classList.add('error');
    f.querySelector('small').textContent = msg;
};
const showSuccess = input => {
    const f = input.closest('.form-field');
    f.classList.remove('error'); f.classList.add('success');
    f.querySelector('small').textContent = '';
};
const clearField = input => {
    const f = input.closest('.form-field');
    f.classList.remove('error', 'success');
    f.querySelector('small').textContent = '';
};
// El mensaje viene del servidor e incluye nombres: se pone como texto, nunca como HTML
const mostrar = (el, texto, tipo) => {
    const aviso = document.createElement('div');
    aviso.className = `alert alert-${tipo} mb-0`;
    aviso.textContent = texto;
    el.replaceChildren(aviso);
};
const debounce = (fn, delay = 400) => {
    let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), delay); };
};

// Envío con botón bloqueado y texto "Guardando…" (conserva el ancho)
async function enviar(url, form, boton, destino, textoOriginal) {
    boton.disabled = true; boton.textContent = 'Guardando…';
    try {
        const r = await fetch(url, { method: 'POST', body: new FormData(form) });
        const d = await r.json();
        if (d.ok) {
            mostrar(destino, d.mensaje, 'success');
            setTimeout(() => location.reload(), 800);
            return;                      // el botón queda bloqueado hasta recargar
        }
        mostrar(destino, d.mensaje, 'danger');   // no se cierra el modal si falla
    } catch (err) {
        console.error(err);
        mostrar(destino, 'Error al conectar con el servidor.', 'danger');
    }
    boton.disabled = false; boton.textContent = textoOriginal;
}

// ---------- Cambiar estado ----------
const estadoNuevo = $('estado-nuevo'), estadoComentario = $('estado-comentario');

const checkEstadoNuevo = () => {
    if (!estadoNuevo.value) { showError(estadoNuevo, 'Selecciona el nuevo estado.'); return false; }
    showSuccess(estadoNuevo); return true;
};
const checkComentario = () => {
    const v = estadoComentario.value.trim();
    if (v === '') showError(estadoComentario, 'Escribe un comentario para cambiar el estado.');
    else if (v.length < 5) showError(estadoComentario, 'Escribe al menos 5 caracteres.');
    else { showSuccess(estadoComentario); return true; }
    return false;
};

document.querySelectorAll('.btn-estado').forEach(b => b.addEventListener('click', () => {
    ticketActual = b.dataset.id;
    formEstado.reset();
    [estadoNuevo, estadoComentario].forEach(clearField);
    $('estado-mensaje').innerHTML = '';
    $('estado-ticket').textContent = `TK-${String(b.dataset.id).padStart(4, '0')} · ${b.dataset.asunto}`;
    const actual = $('estado-actual');
    actual.textContent = b.dataset.estado; actual.dataset.state = b.dataset.estado;
    // Para el Solicitante se explica qué significa cada opción (el valor enviado sigue siendo el estado)
    const textos = b.dataset.modo === 'solicitante'
        ? { 'Cerrado': 'Cerrado — ya funciona, confirmo la solución',
            'En proceso': 'En proceso — el problema sigue, reabrir' }
        : {};
    estadoNuevo.innerHTML = '<option value="">— Selecciona —</option>' +
        b.dataset.siguientes.split(',').map(s => `<option value="${s}">${textos[s] || s}</option>`).join('');
}));

formEstado.addEventListener('submit', e => {
    e.preventDefault();
    if (![checkEstadoNuevo(), checkComentario()].every(Boolean)) {
        // lleva el foco al primer error
        formEstado.querySelector('.form-field.error select, .form-field.error textarea')?.focus();
        return;
    }
    enviar(`/tickets/${ticketActual}/estado`, formEstado, $('estado-guardar'),
        $('estado-mensaje'), 'Confirmar cambio');
});
formEstado.addEventListener('input', debounce(e => {
    if (e.target === estadoNuevo) checkEstadoNuevo();
    if (e.target === estadoComentario) checkComentario();
}));

// ---------- Asignar técnico ----------
if (formAsignar) {
    const tecnico = $('asignar-tecnico');
    const checkTecnico = () => {
        if (!tecnico.value) { showError(tecnico, 'Selecciona un técnico.'); return false; }
        showSuccess(tecnico); return true;
    };
    const prioridad = $('asignar-prioridad'), comentarioAsignar = $('asignar-comentario');
    let prioridadActual = '';
    // Si el administrador cambia la prioridad, el comentario (motivo) pasa a ser obligatorio
    const checkMotivo = () => {
        if (prioridad.value !== prioridadActual && !comentarioAsignar.value.trim()) {
            showError(comentarioAsignar, 'Escribe por qué cambias la prioridad.'); return false;
        }
        clearField(comentarioAsignar); return true;
    };
    let botonAsignar = null;   // botón de la fila que abrió el modal (para "Quitar asignación")
    document.querySelectorAll('.btn-asignar').forEach(b => b.addEventListener('click', () => {
        botonAsignar = b;
        ticketActual = b.dataset.id;
        formAsignar.reset();
        clearField(tecnico);
        $('asignar-mensaje').innerHTML = '';
        $('modal-asignar-titulo').textContent = b.dataset.tecnico ? 'Reasignar ticket' : 'Asignar ticket';
        $('asignar-ticket').textContent = `TK-${String(b.dataset.id).padStart(4, '0')} · ${b.dataset.asunto}`;
        tecnico.value = b.dataset.tecnico || '';
        clearField(comentarioAsignar);
        prioridadActual = b.dataset.prioridad || '';
        prioridad.value = prioridadActual;
        $('asignar-prioridad-ayuda').textContent = 'Indicada por el solicitante: ' + prioridadActual
            + '. Confírmala o ajústala según el impacto real.';
        $('asignar-quitar-zona').hidden = !b.dataset.puedeQuitar;
    }));
    // Desde el modal de Reasignar se pasa al de Quitar asignación con los mismos datos del ticket
    $('asignar-quitar').addEventListener('click', () => {
        const b = botonAsignar;
        const modalAsignar = bootstrap.Modal.getOrCreateInstance($('modal-asignar'));
        $('modal-asignar').addEventListener('hidden.bs.modal', () => {
            prepararQuitar(b.dataset.id, b.dataset.asunto, b.dataset.nombreTecnico);
            bootstrap.Modal.getOrCreateInstance($('modal-quitar')).show();
        }, { once: true });
        modalAsignar.hide();
    });
    formAsignar.addEventListener('submit', e => {
        e.preventDefault();
        if (!checkTecnico()) { tecnico.focus(); return; }
        if (!checkMotivo()) { comentarioAsignar.focus(); return; }
        enviar(`/tickets/${ticketActual}/asignar`, formAsignar, $('asignar-guardar'),
            $('asignar-mensaje'), 'Asignar ticket');
    });
    tecnico.addEventListener('change', checkTecnico);
    prioridad.addEventListener('change', checkMotivo);
    comentarioAsignar.addEventListener('input', debounce(checkMotivo));
}

// ---------- Quitar asignación (el comentario es opcional) ----------
if (formQuitar) {
    const quitarComentario = $('quitar-comentario');
    document.querySelectorAll('.btn-quitar').forEach(b => b.addEventListener('click', () =>
        prepararQuitar(b.dataset.id, b.dataset.asunto, b.dataset.tecnico)));
    formQuitar.addEventListener('submit', e => {
        e.preventDefault();
        enviar(`/tickets/${ticketActual}/quitar_asignacion`, formQuitar, $('quitar-guardar'),
            $('quitar-mensaje'), 'Quitar asignación');
    });
}

// Deja listo el modal de Quitar asignación (lo usan el botón del detalle y el modal de Reasignar)
function prepararQuitar(id, asunto, nombreTecnico) {
    ticketActual = id;
    $('form-quitar').reset();
    clearField($('quitar-comentario'));
    $('quitar-mensaje').innerHTML = '';
    $('quitar-ticket').textContent =
        `TK-${String(id).padStart(4, '0')} · ${asunto} · Técnico: ${nombreTecnico}`;
}
