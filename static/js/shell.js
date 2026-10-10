// Comportamiento común del menú lateral, del menú de cuenta y de las preferencias de visualización.

// Preferencias (Configuración): clases en <body> definidas en settings.css. Solo viven en este navegador.
const PREFERENCIAS = ['large-text', 'reduce-motion'];
const leerPreferencia = nombre => {
  try { return localStorage.getItem('pref-' + nombre) === '1'; } catch (e) { return false; }
};
const guardarPreferencia = (nombre, activa) => {
  try { localStorage.setItem('pref-' + nombre, activa ? '1' : '0'); return true; } catch (e) { return false; }
};

document.addEventListener('DOMContentLoaded', () => {
  PREFERENCIAS.forEach(p => document.body.classList.toggle(p, leerPreferencia(p)));

  const formPreferencias = document.querySelector('#preferences-form');
  if (formPreferencias) {
    const aviso = document.querySelector('#preferences-feedback');
    PREFERENCIAS.forEach(p => { formPreferencias.elements[p].checked = leerPreferencia(p); });
    formPreferencias.addEventListener('submit', e => e.preventDefault());
    formPreferencias.addEventListener('change', e => {
      const nombre = e.target.name;
      document.body.classList.toggle(nombre, e.target.checked);
      aviso.textContent = guardarPreferencia(nombre, e.target.checked)
        ? 'Preferencia guardada.'
        : 'Se aplicó, pero este navegador no permite guardarla.';
    });
  }

  const sidebar = document.querySelector('#sidebar');
  const botonMenu = document.querySelector('[data-action="menu"]');
  if (sidebar && botonMenu) {
    botonMenu.addEventListener('click', () => {
      const abierto = sidebar.classList.toggle('is-open');
      botonMenu.setAttribute('aria-expanded', String(abierto));
    });
  }

  const boton = document.querySelector('#profile-toggle');
  const menu = document.querySelector('#profile-menu');
  if (boton && menu) {
    const cerrar = () => {
      menu.hidden = true;
      boton.setAttribute('aria-expanded', 'false');
    };
    boton.addEventListener('click', () => {
      menu.hidden = !menu.hidden;
      boton.setAttribute('aria-expanded', String(!menu.hidden));
    });
    document.addEventListener('click', e => {
      if (!e.target.closest('.profile-dropdown')) cerrar();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && !menu.hidden) {
        cerrar();
        boton.focus();
      }
    });
  }
});