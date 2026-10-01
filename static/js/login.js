// Login (mismo patrón visto en clase: validar en JS + fetch a Flask + mostrar respuesta en #mensaje)
const loginForm = document.querySelector('#loginForm');

if (loginForm) {
    const emailEl = document.querySelector('#loginEmail');
    const passwordEl = document.querySelector('#loginPassword');
    const roleError = document.querySelector('#role-error');
    const mensaje = document.querySelector('#mensaje');

    const isRequired = value => value !== '';
    const isEmailValid = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    const showError = (input, message) => {
        const formField = input.closest('.form-field');
        formField.classList.remove('success');
        formField.classList.add('error');
        formField.querySelector('small').textContent = message;
    };
    const showSuccess = (input) => {
        const formField = input.closest('.form-field');
        formField.classList.remove('error');
        formField.classList.add('success');
        formField.querySelector('small').textContent = '';
    };

    const checkEmail = () => {
        const email = emailEl.value.trim();
        if (!isRequired(email)) { showError(emailEl, 'Ingresa tu correo electrónico.'); return false; }
        if (!isEmailValid(email)) { showError(emailEl, 'Ingresa un correo electrónico válido.'); return false; }
        showSuccess(emailEl); return true;
    };
    const checkPassword = () => {
        const password = passwordEl.value.trim();
        if (!isRequired(password)) { showError(passwordEl, 'Ingresa tu contraseña.'); return false; }
        if (password.length < 8) { showError(passwordEl, 'La contraseña debe tener al menos 8 caracteres.'); return false; }
        showSuccess(passwordEl); return true;
    };
    const checkRole = () => {
        const ok = !!loginForm.querySelector('[name="role"]:checked');
        roleError.textContent = ok ? '' : 'Selecciona el rol con el que deseas acceder.';
        return ok;
    };

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        mensaje.innerHTML = '';
        const roleOk = checkRole(), emailOk = checkEmail(), passwordOk = checkPassword();
        if (!(roleOk && emailOk && passwordOk)) return;

        const boton = loginForm.querySelector('[type="submit"]');
        const textoOriginal = boton.innerHTML;
        boton.disabled = true;
        boton.textContent = 'Ingresando…';
        try {
            const response = await fetch('/procesar_login', { method: 'POST', body: new FormData(loginForm) });
            const resultado = await response.json();
            if (resultado.ok) {
                window.location.href = resultado.destino;   // la cookie JWT ya fue guardada
                return;
            }
            mensaje.innerHTML = '<div class="alert alert-danger">' + resultado.mensaje + '</div>';
        } catch (error) {
            console.error(error);
            mensaje.innerHTML = '<div class="alert alert-danger">Error al conectar con el servidor.</div>';
        }
        boton.disabled = false;
        boton.innerHTML = textoOriginal;
    });

    emailEl.addEventListener('input', () => { if (emailEl.closest('.form-field').classList.contains('error')) checkEmail(); });
    passwordEl.addEventListener('input', () => { if (passwordEl.closest('.form-field').classList.contains('error')) checkPassword(); });
    loginForm.querySelectorAll('[name="role"]').forEach(r => r.addEventListener('change', checkRole));
}
