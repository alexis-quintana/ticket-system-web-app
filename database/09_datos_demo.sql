-- datos de demostración del sistema de tickets ti (multiempresa)
-- ejecutar después de crear la estructura (sistema_tickets_creacion.sql).
-- empresas y contactos: los reales del grupo. técnicos, solicitantes y tickets: inventados.
-- contraseña de todos los usuarios demo: Demo2026!  (se guarda como hash bcrypt)
-- las fechas de los tickets son relativas a la hora de ejecución, por eso el semáforo sla
-- muestra ejemplos en verde, amarillo y rojo.
-- las notificaciones se generan solas mediante los triggers del historial y de los comentarios.

use db_sistema_tickets_ti;
set names utf8mb4;
set @hash_demo = '$2b$12$VdaoV2QGb1c/l4vcaD8HPOSwHB99GmPimEhccPnSHhYiF.oHpcrr2';

-- roles del sistema
insert into roles (id, nombre) values
  (1, 'Administrador'),
  (2, 'Técnico'),
  (3, 'Solicitante');

-- empresas
insert into empresas (id, nombre, ruc, sector, num_trabajadores, contacto_nombre, contacto_cargo, contacto_email, integrante_responsable) values
  (1, 'ANGEL DIVINO BUS S.A.C.', '20608151771', 'Transporte', 174, 'Hugo Fernando Tantajulca Rimarachin', 'Jefe de TI', 'conpert@maytok.com', 'Montenegro Urrutia, Juan Diego'),
  (2, 'Empresa en coordinación (demo)', null, 'Manufactura', null, 'Contacto pendiente (demo)', 'Jefe de TI', 'admin@empresa02.test', 'Ordoñez Cavero, Martín Benjamín'),
  (3, 'BM Clínica Mendoza S.A.', '20480657323', 'Salud privada', 147, 'Miguel Angel Revilla Pejerrey', 'Jefe de T.I.', 'sistemas@bmclinica.com', 'Quintana Luis, Alexis Abel'),
  (4, 'Móvil Bus S.A.C.', '20555901179', 'Transporte', 1405, 'Juan Ronald Ynga Alvarado', 'Administrador', 'soporteti@movilbus.pe', 'Seminario Bautista, Lorena Marialya'),
  (5, 'Agroindustrial Pomalca S.A.A.', '20163898200', 'Agroindustria', 2133, 'Paul Giraldo Palacios', 'Jefe de TI', 'pgiraldo@pomalca.com.pe', 'Timaná Novoa, Juan Diego');

-- áreas y categorías por empresa
insert into areas (id, empresa_id, nombre) values
  (1, 1, 'Operaciones'),
  (2, 1, 'Administración'),
  (3, 1, 'Recursos Humanos'),
  (4, 1, 'Mantenimiento'),
  (5, 2, 'Producción'),
  (6, 2, 'Almacén'),
  (7, 2, 'Administración'),
  (8, 2, 'Calidad'),
  (9, 3, 'Consulta Externa'),
  (10, 3, 'Emergencia'),
  (11, 3, 'Laboratorio'),
  (12, 3, 'Administración'),
  (13, 4, 'Operaciones'),
  (14, 4, 'Boletería'),
  (15, 4, 'Administración'),
  (16, 4, 'Taller'),
  (17, 5, 'Campo'),
  (18, 5, 'Fábrica'),
  (19, 5, 'Administración'),
  (20, 5, 'Logística');

insert into categorias (id, empresa_id, nombre) values
  (1, 1, 'Red y conexión'),
  (2, 1, 'Software'),
  (3, 1, 'Hardware'),
  (4, 1, 'Accesos y cuentas'),
  (5, 1, 'Impresoras y periféricos'),
  (6, 2, 'Red y conexión'),
  (7, 2, 'Software'),
  (8, 2, 'Hardware'),
  (9, 2, 'Accesos y cuentas'),
  (10, 2, 'Impresoras y periféricos'),
  (11, 3, 'Red y conexión'),
  (12, 3, 'Software'),
  (13, 3, 'Hardware'),
  (14, 3, 'Accesos y cuentas'),
  (15, 3, 'Impresoras y periféricos'),
  (16, 4, 'Red y conexión'),
  (17, 4, 'Software'),
  (18, 4, 'Hardware'),
  (19, 4, 'Accesos y cuentas'),
  (20, 4, 'Impresoras y periféricos'),
  (21, 5, 'Red y conexión'),
  (22, 5, 'Software'),
  (23, 5, 'Hardware'),
  (24, 5, 'Accesos y cuentas'),
  (25, 5, 'Impresoras y periféricos');

-- personas y usuarios
insert into personas (id, empresa_id, area_id, nombres, apellidos, dni, telefono) values
  (1, 1, 2, 'Hugo Fernando', 'Tantajulca Rimarachin', '30011111', '970000001'),
  (2, 1, 1, 'Carlos Alberto', 'Llontop Chero', '41230987', '981000100'),
  (3, 1, 1, 'Rosa Elena', 'Santamaría Díaz', '42318765', '981000111'),
  (4, 1, 2, 'Miguel Angel', 'Vasquez Muñoz', '40871234', '982000100'),
  (5, 1, 3, 'Jessica Paola', 'Ruiz Calderón', '45120938', '982000111'),
  (6, 1, 4, 'Walter', 'Bances Quiroz', '43987120', '982000122'),
  (7, 2, 6, 'Contacto', 'pendiente (demo)', '30022222', '970000002'),
  (8, 2, 5, 'Luis Fernando', 'Carrasco Neyra', '44561230', '981000200'),
  (9, 2, 5, 'Ana María', 'Torres Zapata', '46781239', '981000211'),
  (10, 2, 6, 'Pedro', 'Gonzales Arce', '47123098', '982000200'),
  (11, 2, 7, 'Lucía', 'Mendoza Ríos', '48230971', '982000211'),
  (12, 2, 8, 'Héctor', 'Salazar Dávila', '41908765', '982000222'),
  (13, 3, 10, 'Miguel Angel', 'Revilla Pejerrey', '30033333', '970000003'),
  (14, 3, 9, 'Diego Armando', 'Fernández Cubas', '40129876', '981000300'),
  (15, 3, 9, 'Karen Milagros', 'Olazábal Vera', '45671289', '981000311'),
  (16, 3, 10, 'Sandra Patricia', 'Chávez Gil', '43218790', '982000300'),
  (17, 3, 11, 'Raúl', 'Coronado Medina', '42097651', '982000311'),
  (18, 3, 12, 'Elizabeth', 'Pisfil Sánchez', '46012873', '982000322'),
  (19, 4, 14, 'Juan Ronald', 'Ynga Alvarado', '30044444', '970000004'),
  (20, 4, 13, 'Jorge Luis', 'Mego Tarrillo', '41765890', '981000400'),
  (21, 4, 13, 'Milagros del Pilar', 'Hurtado Cieza', '44326719', '981000411'),
  (22, 4, 14, 'Víctor Hugo', 'Alarcón Paz', '45210987', '982000400'),
  (23, 4, 15, 'Noemí', 'Cajusol Reque', '46893021', '982000411'),
  (24, 4, 16, 'Franco', 'Delgado Vílchez', '40912378', '982000422'),
  (25, 5, 18, 'Paul', 'Giraldo Palacios', '30055555', '970000005'),
  (26, 5, 17, 'Oscar Daniel', 'Rojas Fernández', '42781903', '981000500'),
  (27, 5, 17, 'Gladys Rocío', 'Cabrera Lozano', '43982017', '981000511'),
  (28, 5, 18, 'Manuel', 'Idrogo Bravo', '40712398', '982000500'),
  (29, 5, 19, 'Teresa', 'Vera Montalvo', '45982130', '982000511'),
  (30, 5, 20, 'Alonso', 'Tapia Guevara', '47102839', '982000522'),
  (31, 1, null, 'Administrador', 'General', '00000000', null);

insert into usuarios (id, empresa_id, persona_id, rol_id, email, password, activo) values
  (1, 1, 1, 1, 'conpert@maytok.com', @hash_demo, 1),
  (2, 1, 2, 2, 'carlos.llontop@angeldivinobus.test', @hash_demo, 1),
  (3, 1, 3, 2, 'rosa.santamaria@angeldivinobus.test', @hash_demo, 1),
  (4, 1, 4, 3, 'miguel.vasquez@angeldivinobus.test', @hash_demo, 1),
  (5, 1, 5, 3, 'jessica.ruiz@angeldivinobus.test', @hash_demo, 1),
  (6, 1, 6, 3, 'walter.bances@angeldivinobus.test', @hash_demo, 1),
  (7, 2, 7, 1, 'admin@empresa02.test', @hash_demo, 1),
  (8, 2, 8, 2, 'luis.carrasco@empresa02.test', @hash_demo, 1),
  (9, 2, 9, 2, 'ana.torres@empresa02.test', @hash_demo, 1),
  (10, 2, 10, 3, 'pedro.gonzales@empresa02.test', @hash_demo, 1),
  (11, 2, 11, 3, 'lucia.mendoza@empresa02.test', @hash_demo, 1),
  (12, 2, 12, 3, 'hector.salazar@empresa02.test', @hash_demo, 1),
  (13, 3, 13, 1, 'sistemas@bmclinica.com', @hash_demo, 1),
  (14, 3, 14, 2, 'diego.fernandez@bmclinica.test', @hash_demo, 1),
  (15, 3, 15, 2, 'karen.olazabal@bmclinica.test', @hash_demo, 1),
  (16, 3, 16, 3, 'sandra.chavez@bmclinica.test', @hash_demo, 1),
  (17, 3, 17, 3, 'raul.coronado@bmclinica.test', @hash_demo, 1),
  (18, 3, 18, 3, 'elizabeth.pisfil@bmclinica.test', @hash_demo, 1),
  (19, 4, 19, 1, 'soporteti@movilbus.pe', @hash_demo, 1),
  (20, 4, 20, 2, 'jorge.mego@movilbus.test', @hash_demo, 1),
  (21, 4, 21, 2, 'milagros.hurtado@movilbus.test', @hash_demo, 1),
  (22, 4, 22, 3, 'victor.alarcon@movilbus.test', @hash_demo, 1),
  (23, 4, 23, 3, 'noemi.cajusol@movilbus.test', @hash_demo, 1),
  (24, 4, 24, 3, 'franco.delgado@movilbus.test', @hash_demo, 1),
  (25, 5, 25, 1, 'pgiraldo@pomalca.com.pe', @hash_demo, 1),
  (26, 5, 26, 2, 'oscar.rojas@pomalca.test', @hash_demo, 1),
  (27, 5, 27, 2, 'gladys.cabrera@pomalca.test', @hash_demo, 1),
  (28, 5, 28, 3, 'manuel.idrogo@pomalca.test', @hash_demo, 1),
  (29, 5, 29, 3, 'teresa.vera@pomalca.test', @hash_demo, 1),
  (30, 5, 30, 3, 'alonso.tapia@pomalca.test', @hash_demo, 1),
  (31, 1, 31, 1, 'admin@lexfixer.com', @hash_demo, 1);

-- tickets (las áreas se toman del solicitante)
insert into tickets (id, empresa_id, solicitante_id, categoria_id, area_id, tecnico_id, asunto, descripcion, prioridad, estado, resuelto_en, created_at) values
  (1, 1, 4, 1, 2, null, 'No imprime el módulo de boletos en terminal', 'No imprime el módulo de boletos en terminal. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 60 minute)),
  (2, 1, 5, 2, 3, 2, 'Sin conexión en la oficina de despacho', 'Sin conexión en la oficina de despacho. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 210 minute)),
  (3, 1, 6, 3, 4, 3, 'Sistema de GPS de flota no actualiza', 'Sistema de GPS de flota no actualiza. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'En proceso', null, date_sub(now(), interval 1800 minute)),
  (4, 1, 4, 4, 2, 2, 'Correo corporativo no envía mensajes', 'Correo corporativo no envía mensajes. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'En proceso', null, date_sub(now(), interval 1200 minute)),
  (5, 1, 5, 5, 3, 3, 'Lector de códigos no reconoce pasajes', 'Lector de códigos no reconoce pasajes. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'Resuelto', date_sub(now(), interval 240 minute), date_sub(now(), interval 600 minute)),
  (6, 1, 6, 1, 4, 2, 'Solicitud de acceso al sistema de planillas', 'Solicitud de acceso al sistema de planillas. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Cerrado', date_sub(now(), interval 2760 minute), date_sub(now(), interval 2880 minute)),
  (7, 1, 4, 2, 2, null, 'PC de recepción se reinicia sola', 'PC de recepción se reinicia sola. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'Abierto', null, date_sub(now(), interval 4800 minute)),
  (8, 2, 10, 6, 6, null, 'Impresora de etiquetas sin tinta de transferencia', 'Impresora de etiquetas sin tinta de transferencia. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 60 minute)),
  (9, 2, 11, 7, 7, 8, 'Balanza electrónica no se sincroniza', 'Balanza electrónica no se sincroniza. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 210 minute)),
  (10, 2, 12, 8, 8, 9, 'Falla de red en planta de producción', 'Falla de red en planta de producción. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'En proceso', null, date_sub(now(), interval 1800 minute)),
  (11, 2, 10, 9, 6, 8, 'Acceso denegado al ERP', 'Acceso denegado al ERP. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'En proceso', null, date_sub(now(), interval 1200 minute)),
  (12, 2, 11, 10, 7, 9, 'Laptop de calidad no enciende', 'Laptop de calidad no enciende. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'Resuelto', date_sub(now(), interval 240 minute), date_sub(now(), interval 600 minute)),
  (13, 2, 12, 6, 8, 8, 'Instalar software de inventario', 'Instalar software de inventario. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Cerrado', date_sub(now(), interval 2760 minute), date_sub(now(), interval 2880 minute)),
  (14, 2, 10, 7, 6, null, 'Cámara de almacén sin señal', 'Cámara de almacén sin señal. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'Abierto', null, date_sub(now(), interval 4800 minute)),
  (15, 3, 16, 11, 10, null, 'Historia clínica electrónica no carga', 'Historia clínica electrónica no carga. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 60 minute)),
  (16, 3, 17, 12, 11, 14, 'Impresora de recetas sin conexión', 'Impresora de recetas sin conexión. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 210 minute)),
  (17, 3, 18, 13, 12, 15, 'Equipo de laboratorio no envía resultados', 'Equipo de laboratorio no envía resultados. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'En proceso', null, date_sub(now(), interval 1800 minute)),
  (18, 3, 16, 14, 10, 14, 'WiFi inestable en consultorios', 'WiFi inestable en consultorios. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'En proceso', null, date_sub(now(), interval 1200 minute)),
  (19, 3, 17, 15, 11, 15, 'Cambio de contraseña del sistema de citas', 'Cambio de contraseña del sistema de citas. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'Resuelto', date_sub(now(), interval 240 minute), date_sub(now(), interval 600 minute)),
  (20, 3, 18, 11, 12, 14, 'Monitor de triaje con pantalla parpadeante', 'Monitor de triaje con pantalla parpadeante. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Cerrado', date_sub(now(), interval 2760 minute), date_sub(now(), interval 2880 minute)),
  (21, 3, 16, 12, 10, null, 'Solicitud de usuario para nuevo médico', 'Solicitud de usuario para nuevo médico. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'Abierto', null, date_sub(now(), interval 4800 minute)),
  (22, 4, 22, 16, 14, null, 'Terminal de venta de pasajes sin red', 'Terminal de venta de pasajes sin red. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 60 minute)),
  (23, 4, 23, 17, 15, 20, 'Tablet de control de salidas no inicia sesión', 'Tablet de control de salidas no inicia sesión. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 210 minute)),
  (24, 4, 24, 18, 16, 21, 'Impresora térmica de boletería atascada', 'Impresora térmica de boletería atascada. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'En proceso', null, date_sub(now(), interval 1800 minute)),
  (25, 4, 22, 19, 14, 20, 'Reporte de ventas no se genera', 'Reporte de ventas no se genera. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'En proceso', null, date_sub(now(), interval 1200 minute)),
  (26, 4, 23, 20, 15, 21, 'Falla en cámaras del terminal', 'Falla en cámaras del terminal. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'Resuelto', date_sub(now(), interval 240 minute), date_sub(now(), interval 600 minute)),
  (27, 4, 24, 16, 16, 20, 'Alta de usuario para nuevo cajero', 'Alta de usuario para nuevo cajero. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Cerrado', date_sub(now(), interval 2760 minute), date_sub(now(), interval 2880 minute)),
  (28, 4, 22, 17, 14, null, 'Servidor de archivos muy lento', 'Servidor de archivos muy lento. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'Abierto', null, date_sub(now(), interval 4800 minute)),
  (29, 5, 28, 21, 18, null, 'Sin internet en oficina de campo', 'Sin internet en oficina de campo. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 60 minute)),
  (30, 5, 29, 22, 19, 26, 'Sistema de pesaje de caña no registra', 'Sistema de pesaje de caña no registra. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Abierto', null, date_sub(now(), interval 210 minute)),
  (31, 5, 30, 23, 20, 27, 'Radio enlace con fábrica caído', 'Radio enlace con fábrica caído. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'En proceso', null, date_sub(now(), interval 1800 minute)),
  (32, 5, 28, 24, 18, 26, 'PC de contabilidad con virus', 'PC de contabilidad con virus. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'En proceso', null, date_sub(now(), interval 1200 minute)),
  (33, 5, 29, 25, 19, 27, 'Solicitud de VPN para jefe de campo', 'Solicitud de VPN para jefe de campo. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Media', 'Resuelto', date_sub(now(), interval 240 minute), date_sub(now(), interval 600 minute)),
  (34, 5, 30, 21, 20, 26, 'Impresora de guías de remisión sin respuesta', 'Impresora de guías de remisión sin respuesta. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Alta', 'Cerrado', date_sub(now(), interval 2760 minute), date_sub(now(), interval 2880 minute)),
  (35, 5, 28, 22, 18, null, 'Respaldo de base de datos falló', 'Respaldo de base de datos falló. Reportado por el usuario; se requiere revisión del área de TI. (ticket de demostración)', 'Baja', 'Abierto', null, date_sub(now(), interval 4800 minute));

-- historial de asignaciones y cambios de estado (el trigger crea las notificaciones)
insert into ticket_historial (empresa_id, ticket_id, usuario_id, tipo, estado_anterior, estado_nuevo, tecnico_id, comentario, created_at) values
  (1, 2, 1, 'Asignación', 'Abierto', 'Abierto', 2, 'Ticket asignado a Carlos Alberto Llontop Chero.', date_sub(now(), interval 205 minute)),
  (1, 3, 1, 'Asignación', 'Abierto', 'Abierto', 3, 'Ticket asignado a Rosa Elena Santamaría Díaz.', date_sub(now(), interval 1795 minute)),
  (1, 3, 3, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 1077 minute)),
  (1, 4, 1, 'Asignación', 'Abierto', 'Abierto', 2, 'Ticket asignado a Carlos Alberto Llontop Chero.', date_sub(now(), interval 1195 minute)),
  (1, 4, 2, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 717 minute)),
  (1, 5, 1, 'Asignación', 'Abierto', 'Abierto', 3, 'Ticket asignado a Rosa Elena Santamaría Díaz.', date_sub(now(), interval 595 minute)),
  (1, 5, 3, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 417 minute)),
  (1, 5, 3, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 240 minute)),
  (1, 6, 1, 'Asignación', 'Abierto', 'Abierto', 2, 'Ticket asignado a Carlos Alberto Llontop Chero.', date_sub(now(), interval 2875 minute)),
  (1, 6, 2, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 2817 minute)),
  (1, 6, 2, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 2760 minute)),
  (1, 6, 2, 'Cambio de estado', 'Resuelto', 'Cerrado', null, 'Conformidad del solicitante. Ticket cerrado.', date_sub(now(), interval 2730 minute)),
  (2, 9, 7, 'Asignación', 'Abierto', 'Abierto', 8, 'Ticket asignado a Luis Fernando Carrasco Neyra.', date_sub(now(), interval 205 minute)),
  (2, 10, 7, 'Asignación', 'Abierto', 'Abierto', 9, 'Ticket asignado a Ana María Torres Zapata.', date_sub(now(), interval 1795 minute)),
  (2, 10, 9, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 1077 minute)),
  (2, 11, 7, 'Asignación', 'Abierto', 'Abierto', 8, 'Ticket asignado a Luis Fernando Carrasco Neyra.', date_sub(now(), interval 1195 minute)),
  (2, 11, 8, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 717 minute)),
  (2, 12, 7, 'Asignación', 'Abierto', 'Abierto', 9, 'Ticket asignado a Ana María Torres Zapata.', date_sub(now(), interval 595 minute)),
  (2, 12, 9, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 417 minute)),
  (2, 12, 9, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 240 minute)),
  (2, 13, 7, 'Asignación', 'Abierto', 'Abierto', 8, 'Ticket asignado a Luis Fernando Carrasco Neyra.', date_sub(now(), interval 2875 minute)),
  (2, 13, 8, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 2817 minute)),
  (2, 13, 8, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 2760 minute)),
  (2, 13, 8, 'Cambio de estado', 'Resuelto', 'Cerrado', null, 'Conformidad del solicitante. Ticket cerrado.', date_sub(now(), interval 2730 minute)),
  (3, 16, 13, 'Asignación', 'Abierto', 'Abierto', 14, 'Ticket asignado a Diego Armando Fernández Cubas.', date_sub(now(), interval 205 minute)),
  (3, 17, 13, 'Asignación', 'Abierto', 'Abierto', 15, 'Ticket asignado a Karen Milagros Olazábal Vera.', date_sub(now(), interval 1795 minute)),
  (3, 17, 15, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 1077 minute)),
  (3, 18, 13, 'Asignación', 'Abierto', 'Abierto', 14, 'Ticket asignado a Diego Armando Fernández Cubas.', date_sub(now(), interval 1195 minute)),
  (3, 18, 14, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 717 minute)),
  (3, 19, 13, 'Asignación', 'Abierto', 'Abierto', 15, 'Ticket asignado a Karen Milagros Olazábal Vera.', date_sub(now(), interval 595 minute)),
  (3, 19, 15, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 417 minute)),
  (3, 19, 15, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 240 minute)),
  (3, 20, 13, 'Asignación', 'Abierto', 'Abierto', 14, 'Ticket asignado a Diego Armando Fernández Cubas.', date_sub(now(), interval 2875 minute)),
  (3, 20, 14, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 2817 minute)),
  (3, 20, 14, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 2760 minute)),
  (3, 20, 14, 'Cambio de estado', 'Resuelto', 'Cerrado', null, 'Conformidad del solicitante. Ticket cerrado.', date_sub(now(), interval 2730 minute)),
  (4, 23, 19, 'Asignación', 'Abierto', 'Abierto', 20, 'Ticket asignado a Jorge Luis Mego Tarrillo.', date_sub(now(), interval 205 minute)),
  (4, 24, 19, 'Asignación', 'Abierto', 'Abierto', 21, 'Ticket asignado a Milagros del Pilar Hurtado Cieza.', date_sub(now(), interval 1795 minute)),
  (4, 24, 21, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 1077 minute)),
  (4, 25, 19, 'Asignación', 'Abierto', 'Abierto', 20, 'Ticket asignado a Jorge Luis Mego Tarrillo.', date_sub(now(), interval 1195 minute)),
  (4, 25, 20, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 717 minute)),
  (4, 26, 19, 'Asignación', 'Abierto', 'Abierto', 21, 'Ticket asignado a Milagros del Pilar Hurtado Cieza.', date_sub(now(), interval 595 minute)),
  (4, 26, 21, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 417 minute)),
  (4, 26, 21, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 240 minute)),
  (4, 27, 19, 'Asignación', 'Abierto', 'Abierto', 20, 'Ticket asignado a Jorge Luis Mego Tarrillo.', date_sub(now(), interval 2875 minute)),
  (4, 27, 20, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 2817 minute)),
  (4, 27, 20, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 2760 minute)),
  (4, 27, 20, 'Cambio de estado', 'Resuelto', 'Cerrado', null, 'Conformidad del solicitante. Ticket cerrado.', date_sub(now(), interval 2730 minute)),
  (5, 30, 25, 'Asignación', 'Abierto', 'Abierto', 26, 'Ticket asignado a Oscar Daniel Rojas Fernández.', date_sub(now(), interval 205 minute)),
  (5, 31, 25, 'Asignación', 'Abierto', 'Abierto', 27, 'Ticket asignado a Gladys Rocío Cabrera Lozano.', date_sub(now(), interval 1795 minute)),
  (5, 31, 27, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 1077 minute)),
  (5, 32, 25, 'Asignación', 'Abierto', 'Abierto', 26, 'Ticket asignado a Oscar Daniel Rojas Fernández.', date_sub(now(), interval 1195 minute)),
  (5, 32, 26, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 717 minute)),
  (5, 33, 25, 'Asignación', 'Abierto', 'Abierto', 27, 'Ticket asignado a Gladys Rocío Cabrera Lozano.', date_sub(now(), interval 595 minute)),
  (5, 33, 27, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 417 minute)),
  (5, 33, 27, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 240 minute)),
  (5, 34, 25, 'Asignación', 'Abierto', 'Abierto', 26, 'Ticket asignado a Oscar Daniel Rojas Fernández.', date_sub(now(), interval 2875 minute)),
  (5, 34, 26, 'Cambio de estado', 'Abierto', 'En proceso', null, 'Atención iniciada; se realiza el diagnóstico del problema.', date_sub(now(), interval 2817 minute)),
  (5, 34, 26, 'Cambio de estado', 'En proceso', 'Resuelto', null, 'Problema solucionado y verificado con el usuario.', date_sub(now(), interval 2760 minute)),
  (5, 34, 26, 'Cambio de estado', 'Resuelto', 'Cerrado', null, 'Conformidad del solicitante. Ticket cerrado.', date_sub(now(), interval 2730 minute));

-- comentarios (el trigger crea las notificaciones)
insert into ticket_comentarios (empresa_id, ticket_id, usuario_id, comentario, created_at) values
  (1, 3, 3, 'Estamos revisando el caso; en breve le indicamos los resultados.', date_sub(now(), interval 150 minute)),
  (1, 3, 6, 'Gracias, quedo atento a cualquier novedad.', date_sub(now(), interval 90 minute)),
  (2, 10, 9, 'Estamos revisando el caso; en breve le indicamos los resultados.', date_sub(now(), interval 150 minute)),
  (2, 10, 12, 'Gracias, quedo atento a cualquier novedad.', date_sub(now(), interval 90 minute)),
  (3, 17, 15, 'Estamos revisando el caso; en breve le indicamos los resultados.', date_sub(now(), interval 150 minute)),
  (3, 17, 18, 'Gracias, quedo atento a cualquier novedad.', date_sub(now(), interval 90 minute)),
  (4, 24, 21, 'Estamos revisando el caso; en breve le indicamos los resultados.', date_sub(now(), interval 150 minute)),
  (4, 24, 24, 'Gracias, quedo atento a cualquier novedad.', date_sub(now(), interval 90 minute)),
  (5, 31, 27, 'Estamos revisando el caso; en breve le indicamos los resultados.', date_sub(now(), interval 150 minute)),
  (5, 31, 30, 'Gracias, quedo atento a cualquier novedad.', date_sub(now(), interval 90 minute));

-- las notificaciones con más de 5 horas se consideran leídas; las recientes quedan sin leer
update notificaciones set leida = 1 where created_at < date_sub(now(), interval 5 hour);

-- resumen por empresa
select e.id, e.nombre,
       (select count(*) from usuarios u where u.empresa_id = e.id) as usuarios,
       (select count(*) from tickets t where t.empresa_id = e.id) as tickets,
       (select count(*) from notificaciones n join usuarios u on u.id = n.usuario_id where u.empresa_id = e.id) as notificaciones
from empresas e
order by e.id;
