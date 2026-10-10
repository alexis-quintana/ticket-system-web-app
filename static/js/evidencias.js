// Módulo 2: ver la foto de evidencia en tamaño completo (zoom) dentro de un <dialog>
(() => {
    const dialogo = document.getElementById('dialogo-evidencia');
    const grande = document.getElementById('evidencia-grande');
    const nombre = document.getElementById('evidencia-nombre');
    const abrir = document.getElementById('evidencia-abrir');

    document.querySelectorAll('.gallery-image').forEach(b => b.addEventListener('click', () => {
        grande.src = b.dataset.src;
        grande.alt = b.dataset.nombre;
        nombre.textContent = b.dataset.nombre;
        abrir.href = b.dataset.src;
        dialogo.showModal();
    }));

    dialogo.querySelector('.dialog-close').addEventListener('click', () => dialogo.close());
    // clic fuera de la foto (en el fondo oscuro) también cierra
    dialogo.addEventListener('click', e => { if (e.target === dialogo) dialogo.close(); });
})();