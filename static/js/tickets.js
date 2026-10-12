const $ = id => document.getElementById(id);
const form = $('form-ticket');
const asuntoEl = $('asunto'), descripcionEl = $('descripcion'), categoriaEl = $('categoria'), prioridadEl = $('prioridad');
const confirmModal = $('confirmModal');

const isRequired = value => value !== '';
const isBetween = (length, min, max) => !(length < min || length > max);

const showError = (input, message) => {
    const f = input.closest('.form-field');
    f.classList.remove('success'); f.classList.add('error');
    f.querySelector('small').textContent = message;
};
const showSuccess = input => {
    const f = input.closest('.form-field');
    f.classList.remove('error'); f.classList.add('success');
    f.querySelector('small').textContent = '';
};

const checkAsunto = () => {
    const v = asuntoEl.value.trim();
    if (!isRequired(v)) showError(asuntoEl, 'El asunto no puede estar vacío.');
    else if (!isBetween(v.length, 5, 120)) showError(asuntoEl, 'Entre 5 y 120 caracteres.');
    else { showSuccess(asuntoEl); return true; }
    return false;
};
const checkDescripcion = () => {
    const v = descripcionEl.value.trim();
    if (!isRequired(v)) showError(descripcionEl, 'La descripción no puede estar vacía.');
    else if (!isBetween(v.length, 10, 2000)) showError(descripcionEl, 'Entre 10 y 2000 caracteres.');
    else { showSuccess(descripcionEl); return true; }
    return false;
};
const checkCategoria = () => {
    if (!isRequired(categoriaEl.value)) { showError(categoriaEl, 'Selecciona una categoría.'); return false; }
    showSuccess(categoriaEl); return true;
};
const checkPrioridad = () => {
    if (!isRequired(prioridadEl.value)) { showError(prioridadEl, 'Selecciona una prioridad.'); return false; }
    showSuccess(prioridadEl); return true;
};

const evidenciasEl = $('evidencias'), previewEl = $('preview');
const MAX_FOTOS = 3, MAX_MB = 5, TIPOS = ['image/jpeg', 'image/png'];
// Al editar, las fotos que ya tiene el ticket también cuentan para el máximo de 3.
let fotosActuales = Number(form.dataset.fotosActuales || 0);

const checkEvidencias = () => {
    const fotos = [...evidenciasEl.files];
    const libres = MAX_FOTOS - fotosActuales;
    if (fotos.length > libres) {
        showError(evidenciasEl, fotosActuales === 0 ? 'Puedes adjuntar como máximo 3 fotos. Quita alguna.'
            : libres <= 0 ? 'El ticket ya tiene 3 fotos. Elimina una para agregar otra.'
            : 'Puedes agregar como máximo ' + libres + (libres === 1 ? ' foto más.' : ' fotos más.'));
        return false;
    }
    const malTipo = fotos.find(f => !TIPOS.includes(f.type));
    if (malTipo) { showError(evidenciasEl, malTipo.name + ' no es una imagen JPG o PNG.'); return false; }
    const falsa = fotos.find(f => archivosFalsos.includes(f.name));
    if (falsa) { showError(evidenciasEl, falsa.name + ' no es una imagen JPG o PNG real (solo tiene la extensión).'); return false; }
    const pesada = fotos.find(f => f.size > MAX_MB * 1024 * 1024);
    if (pesada) { showError(evidenciasEl, pesada.name + ' pesa más de 5 MB.'); return false; }
    if (fotos.length) showSuccess(evidenciasEl);
    else { const f = evidenciasEl.closest('.form-field'); f.classList.remove('error', 'success'); f.querySelector('small').textContent = ''; }
    return true;
};

const mostrarPreview = () => {
    const n = evidenciasEl.files.length;
    $('evidencias-texto').textContent = n === 0 ? 'Ninguna foto seleccionada' : n === 1 ? '1 foto seleccionada' : n + ' fotos seleccionadas';
    previewEl.innerHTML = '';
    [...evidenciasEl.files].forEach((f, i) => {
        const caja = document.createElement('div');
        const img = document.createElement('img');
        img.src = URL.createObjectURL(f); img.alt = f.name;
        const quitar = document.createElement('button');
        quitar.type = 'button'; quitar.className = 'secondary-button'; quitar.textContent = 'Quitar';
        quitar.addEventListener('click', () => {
            seleccion.items.remove(i);
            evidenciasEl.files = seleccion.files;
            mostrarPreview(); checkEvidencias();
        });
        caja.append(img, quitar);
        previewEl.append(caja);
    });
};
// Validación MIME también en el navegador: lee los primeros bytes (la extensión no basta).
let archivosFalsos = [];
const esImagenReal = async f => {
    const b = new Uint8Array(await f.slice(0, 8).arrayBuffer());
    const jpg = b[0] === 0xFF && b[1] === 0xD8 && b[2] === 0xFF;
    const png = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A].every((x, i) => b[i] === x);
    return jpg || png;
};

// Las fotos se van sumando: cada vez que eliges, se agregan a las que ya estaban (no las reemplazan).
const seleccion = new DataTransfer();
const mismoArchivo = (a, b) => a.name === b.name && a.size === b.size && a.lastModified === b.lastModified;

evidenciasEl.addEventListener('change', async () => {
    $('mensaje').replaceChildren();
    for (const f of [...evidenciasEl.files]) {
        if ([...seleccion.files].some(g => mismoArchivo(f, g))) continue;   // ya estaba elegida
        seleccion.items.add(f);
        if (!await esImagenReal(f)) archivosFalsos.push(f.name);
    }
    evidenciasEl.files = seleccion.files;
    mostrarPreview(); checkEvidencias();
});

// Mensaje bajo el formulario. textContent (no innerHTML): el nombre de un archivo nunca se ejecuta como HTML.
const mostrarMensaje = (texto, clase) => {
    const p = document.createElement('p');
    p.className = clase;
    p.textContent = texto;
    $('mensaje').replaceChildren(p);
};

// Ventana de confirmación reutilizable: devuelve una promesa con true (Sí) o false (Cancelar).
const pedirConfirmacion = texto => new Promise(resolver => {
    $('confirmTexto').textContent = texto;
    confirmModal.classList.remove('hidden');
    $('confirmYes').focus();
    const cerrar = valor => {
        confirmModal.classList.add('hidden');
        $('confirmYes').onclick = $('confirmNo').onclick = null;
        resolver(valor);
    };
    $('confirmYes').onclick = () => cerrar(true);
    $('confirmNo').onclick = () => cerrar(false);
});

// Editar: eliminar una foto que ya está guardada.
document.querySelectorAll('.btn-eliminar-foto').forEach(boton => boton.addEventListener('click', async () => {
    if (!await pedirConfirmacion('¿Eliminar la foto ' + boton.dataset.nombre + '? No se puede deshacer.')) return;
    boton.disabled = true;
    try {
        const r = await (await fetch(boton.dataset.url, { method: 'POST' })).json();
        if (r.ok) {
            boton.parentElement.remove();
            fotosActuales -= 1;
            checkEvidencias();
            mostrarMensaje(r.mensaje, 'status-chip');
            return;
        }
        mostrarMensaje(r.mensaje, 'form-error');
    } catch (error) {
        console.error(error);
        mostrarMensaje('Error al conectar con el servidor.', 'form-error');
    }
    boton.disabled = false;
}));

const enviarFormulario = async () => {
    const boton = $('btn-guardar');
    boton.disabled = true;
    try {
        const response = await fetch(form.action, { method: 'POST', body: new FormData(form) });
        const r = await response.json();
        if (r.ok) {
            mostrarMensaje(r.mensaje, 'status-chip');
            setTimeout(() => location.href = '/tickets/', 800);
            return;
        }
        mostrarMensaje(r.mensaje, 'form-error');
    } catch (error) {
        console.error(error);
        mostrarMensaje('Error al conectar con el servidor.', 'form-error');
    }
    boton.disabled = false;
};

form.addEventListener('submit', async e => {
    e.preventDefault();
    const ok = [checkAsunto(), checkDescripcion(), checkCategoria(), checkPrioridad(), checkEvidencias()].every(Boolean);
    if (ok && await pedirConfirmacion(form.dataset.confirmar)) enviarFormulario();
});

const debounce = (fn, delay = 500) => {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(null, args), delay); };
};
form.addEventListener('input', debounce(e => {
    switch (e.target.id) {
        case 'asunto': checkAsunto(); break;
        case 'descripcion': checkDescripcion(); break;
    }
}));
form.addEventListener('change', e => {
    switch (e.target.id) {
        case 'categoria': checkCategoria(); break;
        case 'prioridad': checkPrioridad(); break;
    }
});