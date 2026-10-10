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


// Navegación e interactividad común (no cambia las preferencias de arriba).
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.querySelector('#sidebar');
  const botonMenu = document.querySelector('[data-action="menu"]');

  // Menú móvil: fondo oscuro, cierra al tocar fuera, con Escape o al elegir una opción.
  if (sidebar && botonMenu) {
    const fondo = document.createElement('div');
    fondo.className = 'sidebar-backdrop';
    document.body.appendChild(fondo);
    const cerrarMenu = () => {
      sidebar.classList.remove('is-open');
      botonMenu.setAttribute('aria-expanded', 'false');
    };
    new MutationObserver(() => {
      const abierto = sidebar.classList.contains('is-open');
      fondo.classList.toggle('is-visible', abierto);
      document.body.classList.toggle('menu-open', abierto);
    }).observe(sidebar, { attributes: true, attributeFilter: ['class'] });
    fondo.addEventListener('click', cerrarMenu);
    sidebar.addEventListener('click', e => { if (e.target.closest('.nav-item')) cerrarMenu(); });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
        cerrarMenu();
        botonMenu.focus();
      }
    });
  }

  // Avisos: se cierran con la X y los de éxito desaparecen solos a los 6 segundos.
  const ocultarAviso = aviso => {
    aviso.classList.add('is-hiding');
    setTimeout(() => aviso.remove(), 260);
  };
  document.addEventListener('click', e => {
    const cerrar = e.target.closest('.flash-close');
    if (cerrar) ocultarAviso(cerrar.closest('.flash'));
  });
  document.querySelectorAll('.flash-success').forEach(a => setTimeout(() => ocultarAviso(a), 6000));

  // Filtros: se aplican al cambiar un selector (formularios con data-auto-submit).
  document.querySelectorAll('form[data-auto-submit]').forEach(form => {
    form.addEventListener('change', e => {
      if (e.target.matches('select')) form.requestSubmit();
    });
  });

  // Filas de tabla con data-href: un clic en cualquier parte de la fila abre el detalle.
  document.querySelectorAll('tr[data-href]').forEach(fila => {
    fila.addEventListener('click', e => {
      if (e.target.closest('a, button, input, select, textarea, label')) return;
      window.location.href = fila.dataset.href;
    });
  });
});

// Selector de empresa (superadmin): abre y cierra su desplegable igual que el menú de cuenta.
document.addEventListener('DOMContentLoaded', () => {
  const boton = document.querySelector('#company-toggle');
  const menu = document.querySelector('#company-menu');
  if (!boton || !menu) return;
  const cerrar = () => {
    menu.hidden = true;
    boton.setAttribute('aria-expanded', 'false');
  };
  boton.addEventListener('click', () => {
    menu.hidden = !menu.hidden;
    boton.setAttribute('aria-expanded', String(!menu.hidden));
  });
  document.addEventListener('click', e => {
    if (!e.target.closest('.company-switch')) cerrar();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !menu.hidden) {
      cerrar();
      boton.focus();
    }
  });
});

// Desplegables (combos): reemplaza el menú nativo de cada <select> por uno con el mismo estilo
// que el menú de cuenta. El <select> original sigue en la página (oculto) y se mantiene sincronizado,
// así que formularios, filtros con envío automático y el JS de cada módulo funcionan igual.
// Para dejar un select nativo: <select data-native>.
(() => {
  const mejorados = new WeakSet();
  let abierto = null; // { combo, menu }

  const textoActual = sel => {
    const op = sel.options[sel.selectedIndex];
    return op ? op.textContent.trim() : '';
  };

  function cerrar() {
    if (!abierto) return;
    abierto.menu.remove();
    abierto.toggle.setAttribute('aria-expanded', 'false');
    abierto = null;
  }

  function abrir(sel, toggle) {
    cerrar();
    const menu = document.createElement('div');
    menu.className = 'cbo-menu';
    menu.setAttribute('role', 'listbox');
    Array.from(sel.options).forEach((op, i) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'cbo-option' + (i === sel.selectedIndex ? ' is-current' : '');
      item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', String(i === sel.selectedIndex));
      item.textContent = op.textContent.trim();
      item.dataset.index = i;
      if (op.disabled) item.disabled = true;
      menu.appendChild(item);
    });
    (sel.closest('.modal') || document.body).appendChild(menu); // dentro del modal, Bootstrap no le quita el foco
    const r = toggle.getBoundingClientRect();
    menu.style.minWidth = r.width + 'px';
    menu.style.left = Math.min(r.left, window.innerWidth - menu.offsetWidth - 8) + 'px';
    const abajo = window.innerHeight - r.bottom - 12;
    const arriba = r.top - 12;
    const tope = Math.min(300, Math.max(abajo, arriba));
    menu.style.maxHeight = tope + 'px';
    if (abajo < Math.min(menu.scrollHeight, 220) && arriba > abajo) {
      menu.style.bottom = (window.innerHeight - r.top + 8) + 'px';
    } else {
      menu.style.top = (r.bottom + 8) + 'px';
    }
    toggle.setAttribute('aria-expanded', 'true');
    abierto = { menu, toggle, sel };
    const actual = menu.querySelector('.is-current') || menu.firstElementChild;
    if (actual) actual.scrollIntoView({ block: 'nearest' });

    menu.addEventListener('click', e => {
      const item = e.target.closest('.cbo-option');
      if (!item || item.disabled) return;
      elegir(sel, Number(item.dataset.index));
      cerrar();
      toggle.focus();
    });
    menu.addEventListener('keydown', e => {
      const items = Array.from(menu.querySelectorAll('.cbo-option:not(:disabled)'));
      const i = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); (items[i + 1] || items[0]).focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); (items[i - 1] || items[items.length - 1]).focus(); }
      else if (e.key === 'Home') { e.preventDefault(); items[0].focus(); }
      else if (e.key === 'End') { e.preventDefault(); items[items.length - 1].focus(); }
      else if (e.key === 'Tab') { cerrar(); }
    });
    (menu.querySelector('.is-current') || menu.firstElementChild)?.focus();
  }

  function elegir(sel, indice) {
    if (sel.selectedIndex === indice) return;
    sel.selectedIndex = indice;
    sel.dispatchEvent(new Event('input', { bubbles: true }));
    sel.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function mejorar(sel) {
    if (mejorados.has(sel) || sel.multiple || sel.size > 1 || sel.hasAttribute('data-native')) return;
    mejorados.add(sel);

    const cs = getComputedStyle(sel);
    const ancho = sel.offsetWidth;
    const completo = cs.width.endsWith('%') || !ancho ||
      (sel.parentElement && ancho >= sel.parentElement.clientWidth - 2);

    const combo = document.createElement('div');
    combo.className = 'cbo' + (completo ? ' cbo-full' : '');
    if (!completo) combo.style.minWidth = ancho + 'px';
    if (cs.flexGrow !== '0') combo.style.flexGrow = cs.flexGrow;
    if (cs.gridColumnStart !== 'auto') combo.style.gridColumn = cs.gridColumnStart + ' / ' + cs.gridColumnEnd;

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'cbo-toggle';
    toggle.setAttribute('aria-haspopup', 'listbox');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML = '<span></span><i class="bi bi-chevron-down icon chevron" aria-hidden="true"></i>';
    const etiqueta = sel.labels && sel.labels[0];
    if (etiqueta) toggle.setAttribute('aria-label', etiqueta.textContent.trim().replace(/\s+/g, ' '));

    sel.parentNode.insertBefore(combo, sel);
    combo.appendChild(toggle);
    combo.appendChild(sel);
    sel.classList.add('cbo-native');
    sel.tabIndex = -1;
    sel.setAttribute('aria-hidden', 'true');

    const texto = toggle.firstElementChild;
    const refrescar = () => {
      const t = textoActual(sel);
      if (texto.textContent !== t) texto.textContent = t;
      toggle.disabled = sel.disabled;
    };
    refrescar();

    sel.addEventListener('change', refrescar);
    sel.addEventListener('focus', () => toggle.focus());
    sel.form && sel.form.addEventListener('reset', () => setTimeout(refrescar, 0));
    toggle.addEventListener('click', () => {
      if (abierto && abierto.toggle === toggle) cerrar(); else abrir(sel, toggle);
    });
    toggle.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); abrir(sel, toggle); }
    });
    // Si otro script cambia el valor sin disparar "change" (por ejemplo al abrir un modal), se actualiza solo.
    setInterval(refrescar, 400);
  }

  function iniciar(raiz) {
    (raiz.querySelectorAll ? raiz.querySelectorAll('select') : []).forEach(mejorar);
    if (raiz.matches && raiz.matches('select')) mejorar(raiz);
  }

  document.addEventListener('click', e => {
    if (abierto && !e.target.closest('.cbo-menu') && !e.target.closest('.cbo-toggle')) cerrar();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && abierto) { const t = abierto.toggle; cerrar(); t.focus(); }
  });
  window.addEventListener('resize', cerrar);
  window.addEventListener('scroll', e => {
    if (abierto && !(e.target.closest && e.target.closest('.cbo-menu'))) cerrar();
  }, true);

  document.addEventListener('DOMContentLoaded', () => {
    iniciar(document);
    new MutationObserver(muts => muts.forEach(m => m.addedNodes.forEach(n => n.nodeType === 1 && iniciar(n))))
      .observe(document.body, { childList: true, subtree: true });
  });
})();

// Configuración: botón "Restablecer" borra las preferencias de visualización guardadas.
document.addEventListener('DOMContentLoaded', () => {
  const boton = document.querySelector('[data-reset-prefs]');
  const form = document.querySelector('#preferences-form');
  if (!boton || !form) return;
  boton.addEventListener('click', () => {
    PREFERENCIAS.forEach(p => {
      guardarPreferencia(p, false);
      document.body.classList.remove(p);
      form.elements[p].checked = false;
    });
    const aviso = document.querySelector('#preferences-feedback');
    if (aviso) aviso.textContent = 'Preferencias restablecidas.';
  });
});
