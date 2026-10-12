// Módulo 3: cambiar estado (comentario obligatorio) y asignar técnico.
// Mismo patrón de clase: validar en JS + fetch a Flask + mostrar respuesta.
const $ = id => document.getElementById(id);
const formEstado = $('form-estado');
const formAsignar = $('form-asignar');   // solo existe para el Administrador
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
const mostrar = (el, texto, tipo) =>
    el.innerHTML = `<div class="alert alert-${tipo} mb-0">${texto}</div>`;
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
    estadoNuevo.innerHTML = '<option value="">— Selecciona —</option>' +
        b.dataset.siguientes.split(',').map(s => `<option>${s}</option>`).join('');
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
    document.querySelectorAll('.btn-asignar').forEach(b => b.addEventListener('click', () => {
        ticketActual = b.dataset.id;
        formAsignar.reset();
        clearField(tecnico);
        $('asignar-mensaje').innerHTML = '';
        $('asignar-ticket').textContent = `TK-${String(b.dataset.id).padStart(4, '0')} · ${b.dataset.asunto}`;
        tecnico.value = b.dataset.tecnico || '';
    }));
    formAsignar.addEventListener('submit', e => {
        e.preventDefault();
        if (!checkTecnico()) { tecnico.focus(); return; }
        enviar(`/tickets/${ticketActual}/asignar`, formAsignar, $('asignar-guardar'),
            $('asignar-mensaje'), 'Asignar ticket');
    });
    tecnico.addEventListener('change', checkTecnico);
}
