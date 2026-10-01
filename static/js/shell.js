// Comportamiento común del menú lateral y del menú de cuenta.
document.addEventListener('DOMContentLoaded', () => {
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