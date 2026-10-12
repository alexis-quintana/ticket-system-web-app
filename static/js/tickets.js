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

const checkEvidencias = () => {
    const fotos = [...evidenciasEl.files];
    if (fotos.length > MAX_FOTOS) { showError(evidenciasEl, 'Puedes adjuntar como máximo 3 fotos.'); return false; }
    const malTipo = fotos.find(f => !TIPOS.includes(f.type));
    if (malTipo) { showError(evidenciasEl, malTipo.name + ' no es una imagen JPG o PNG.'); return false; }
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
            const dt = new DataTransfer();
            [...evidenciasEl.files].forEach((g, j) => { if (j !== i) dt.items.add(g); });
            evidenciasEl.files = dt.files;
            mostrarPreview(); checkEvidencias();
        });
        caja.append(img, quitar);
        previewEl.append(caja);
    });
};
evidenciasEl.addEventListener('change', () => { mostrarPreview(); checkEvidencias(); });

const enviarFormulario = async () => {
    const boton = $('btn-guardar');
    boton.disabled = true;
    try {
        const response = await fetch(form.action, { method: 'POST', body: new FormData(form) });
        const r = await response.json();
        if (r.ok) {
            $('mensaje').innerHTML = '<p class="status-chip">' + r.mensaje + '</p>';
            setTimeout(() => location.href = '/tickets/', 800);
            return;
        }
        $('mensaje').innerHTML = '<p class="form-error">' + r.mensaje + '</p>';
    } catch (error) {
        console.error(error);
        $('mensaje').innerHTML = '<p class="form-error">Error al conectar con el servidor.</p>';
    }
    boton.disabled = false;
};

$('confirmYes').addEventListener('click', () => { confirmModal.classList.add('hidden'); enviarFormulario(); });
$('confirmNo').addEventListener('click', () => confirmModal.classList.add('hidden'));

form.addEventListener('submit', e => {
    e.preventDefault();
    const ok = [checkAsunto(), checkDescripcion(), checkCategoria(), checkPrioridad(), checkEvidencias()].every(Boolean);
    if (ok) confirmModal.classList.remove('hidden');
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