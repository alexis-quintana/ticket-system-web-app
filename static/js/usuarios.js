// Usuarios (admin): validación en JS + modal de confirmación + fetch a Flask (patrón visto en clase)
const $ = id => document.getElementById(id);
const form = $('signup');
const usernameEl = $('username'), apellidosEl = $('apellidos'), dniEl = $('dni'), telefonoEl = $('telefono'), emailEl = $('email'), passwordEl = $('password'), confirmPasswordEl = $('confirm-password');
const confirmModal = $('confirmModal');
let editando = false;

// ---------- validaciones ----------
const isRequired = value => value !== '';
const isBetween = (length, min, max) => !(length < min || length > max);
const isEmailValid = email => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
const isPasswordSecure = password => new RegExp('^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#\\$%\\^&\\*])(?=.{8,})').test(password);

const showError = (input, message) => {
    const f = input.parentElement;
    f.classList.remove('success'); f.classList.add('error');
    f.querySelector('small').textContent = message;
};
const showSuccess = input => {
    const f = input.parentElement;
    f.classList.remove('error'); f.classList.add('success');
    f.querySelector('small').textContent = '';
};
const clearField = input => {
    const f = input.parentElement;
    f.classList.remove('error', 'success');
    f.querySelector('small').textContent = '';
};

const checkUsername = () => {
    const v = usernameEl.value.trim();
    if (!isRequired(v)) showError(usernameEl, 'Los nombres no pueden estar vacíos.');
    else if (!isBetween(v.length, 2, 60)) showError(usernameEl, 'Entre 2 y 60 caracteres.');
    else { showSuccess(usernameEl); return true; }
    return false;
};
const checkApellidos = () => {
    const v = apellidosEl.value.trim();
    if (!isRequired(v)) showError(apellidosEl, 'Los apellidos no pueden estar vacíos.');
    else if (!isBetween(v.length, 2, 60)) showError(apellidosEl, 'Entre 2 y 60 caracteres.');
    else { showSuccess(apellidosEl); return true; }
    return false;
};
const checkDni = () => {
    const v = dniEl.value.trim();
    if (v === '') { clearField(dniEl); return true; }
    if (!/^\d{8}$/.test(v)) { showError(dniEl, 'El DNI tiene 8 dígitos.'); return false; }
    showSuccess(dniEl); return true;
};
const checkTelefono = () => {
    const v = telefonoEl.value.trim();
    if (v === '') { clearField(telefonoEl); return true; }
    if (!/^\d{6,15}$/.test(v)) { showError(telefonoEl, 'Solo números (6 a 15 dígitos).'); return false; }
    showSuccess(telefonoEl); return true;
};
const checkEmail = () => {
    const v = emailEl.value.trim();
    if (!isRequired(v)) showError(emailEl, 'El correo no puede estar vacío.');
    else if (!isEmailValid(v)) showError(emailEl, 'El correo no es válido.');
    else { showSuccess(emailEl); return true; }
    return false;
};
const checkPassword = () => {
    const v = passwordEl.value.trim();
    if (editando && v === '') { clearField(passwordEl); return true; }   // vacía = conservar la actual
    if (!isRequired(v)) showError(passwordEl, 'La contraseña no puede estar vacía.');
    else if (!isPasswordSecure(v)) showError(passwordEl, 'Mínimo 8 caracteres con minúscula, mayúscula, número y símbolo (!@#$%^&*).');
    else { showSuccess(passwordEl); return true; }
    return false;
};
const checkConfirmPassword = () => {
    const c = confirmPasswordEl.value.trim(), p = passwordEl.value.trim();
    if (editando && p === '' && c === '') { clearField(confirmPasswordEl); return true; }
    if (!isRequired(c)) showError(confirmPasswordEl, 'Escribe la contraseña otra vez.');
    else if (p !== c) showError(confirmPasswordEl, 'Las contraseñas no coinciden.');
    else { showSuccess(confirmPasswordEl); return true; }
    return false;
};

// ---------- modal: registrar / editar ----------
function modo(editar, d = {}) {
    editando = editar;
    form.reset();
    [usernameEl, apellidosEl, dniEl, telefonoEl, emailEl, passwordEl, confirmPasswordEl].forEach(clearField);
    $('mensaje').innerHTML = '';
    $('modal-titulo').textContent = editar ? 'Editar usuario' : 'Registrar usuario';
    $('u-guardar').textContent = editar ? 'Guardar cambios' : 'Registrar usuario';
    $('u-pass-label').textContent = editar ? 'Nueva contraseña (opcional)' : 'Contraseña *';
    $('u-pass-help').hidden = !editar;
    $('u-id').value = d.id || '';
    usernameEl.value = d.nombres || '';
    apellidosEl.value = d.apellidos || '';
    dniEl.value = d.dni || '';
    telefonoEl.value = d.telefono || '';
    emailEl.value = d.email || '';
    $('u-rol').value = d.rol || 'Solicitante';
    $('u-area').value = d.area || '';
    $('u-activo').checked = editar ? d.activo === '1' : true;
}
$('btn-nuevo').addEventListener('click', () => modo(false));
document.querySelectorAll('.btn-editar').forEach(b => b.addEventListener('click', () => modo(true, b.dataset)));

// ---------- envío ----------
const enviarFormulario = async () => {
    const boton = $('u-guardar');
    boton.disabled = true;
    try {
        const response = await fetch('/procesar_usuario', { method: 'POST', body: new FormData(form) });
        const r = await response.json();
        if (r.ok) {
            $('mensaje').innerHTML = '<div class="alert alert-success mb-0">' + r.mensaje + '</div>';
            setTimeout(() => location.reload(), 800);
            return;
        }
        $('mensaje').innerHTML = '<div class="alert alert-danger mb-0">' + r.mensaje + '</div>';
    } catch (error) {
        console.error(error);
        $('mensaje').innerHTML = '<div class="alert alert-danger mb-0">Error al conectar con el servidor.</div>';
    }
    boton.disabled = false;
};

$('confirmYes').addEventListener('click', () => { confirmModal.classList.add('hidden'); enviarFormulario(); });
$('confirmNo').addEventListener('click', () => confirmModal.classList.add('hidden'));

form.addEventListener('submit', e => {
    e.preventDefault();
    const ok = [checkUsername(), checkApellidos(), checkDni(), checkTelefono(), checkEmail(), checkPassword(), checkConfirmPassword()].every(Boolean);
    if (ok) confirmModal.classList.remove('hidden');
});

const debounce = (fn, delay = 500) => {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(null, args), delay); };
};
form.addEventListener('input', debounce(e => {
    switch (e.target.id) {
        case 'username': checkUsername(); break;
        case 'apellidos': checkApellidos(); break;
        case 'dni': checkDni(); break;
        case 'telefono': checkTelefono(); break;
        case 'email': checkEmail(); break;
        case 'password': checkPassword(); break;
        case 'confirm-password': checkConfirmPassword(); break;
    }
}));
