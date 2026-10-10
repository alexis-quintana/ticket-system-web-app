-- procedimientos almacenados. cada uno valida, guarda y deja el historial en una sola transacción.
-- ejemplos de uso al final de cada procedimiento, en los comentarios.

use db_sistema_tickets_ti;
set names utf8mb4;

delimiter $$

-- módulo 5: crea una notificación
-- ejemplo: call sp_crear_notificacion(2, 1, 'asignacion', 'Se te asignó el ticket TK-0001');
create procedure sp_crear_notificacion(
    in p_usuario_id int,
    in p_ticket_id int,
    in p_tipo varchar(20),
    in p_mensaje varchar(255)
)
begin
    if p_tipo not in ('asignacion', 'cambio_estado', 'comentario') then
        signal sqlstate '45000' set message_text = 'Tipo de notificación no válido';
    end if;

    insert into notificaciones (usuario_id, ticket_id, tipo, mensaje)
    values (p_usuario_id, p_ticket_id, p_tipo, p_mensaje);
end$$

-- módulo 3: asigna un técnico a un ticket (lo hace un administrador de la misma empresa).
-- la notificación al técnico la crea el trigger trg_historial_ai.
-- ejemplo: call sp_asignar_ticket(1, 2, 1, 'Atender con prioridad');
create procedure sp_asignar_ticket(
    in p_ticket_id int,
    in p_tecnico_id int,
    in p_admin_id int,
    in p_comentario text
)
begin
    declare v_empresa int;
    declare v_estado varchar(20);
    declare v_tecnico_actual int;
    declare v_es_admin int;
    declare v_es_tecnico int;

    declare exit handler for sqlexception
    begin
        rollback;
        resignal;
    end;

    start transaction;

    select empresa_id, estado, tecnico_id
      into v_empresa, v_estado, v_tecnico_actual
      from tickets
     where id = p_ticket_id
       for update;

    if v_empresa is null then
        signal sqlstate '45000' set message_text = 'El ticket no existe';
    end if;

    select count(*) into v_es_admin
      from usuarios u
      join roles r on r.id = u.rol_id
     where u.id = p_admin_id and u.empresa_id = v_empresa and u.activo = 1 and r.nombre = 'Administrador';

    if v_es_admin = 0 then
        signal sqlstate '45000' set message_text = 'Solo un administrador de la empresa puede asignar tickets';
    end if;

    select count(*) into v_es_tecnico
      from usuarios u
      join roles r on r.id = u.rol_id
     where u.id = p_tecnico_id and u.empresa_id = v_empresa and u.activo = 1 and r.nombre = 'Técnico';

    if v_es_tecnico = 0 then
        signal sqlstate '45000' set message_text = 'El técnico no es válido para esta empresa';
    end if;

    if v_estado = 'Cerrado' then
        signal sqlstate '45000' set message_text = 'Un ticket cerrado no se puede reasignar';
    end if;

    if v_tecnico_actual <=> p_tecnico_id then
        signal sqlstate '45000' set message_text = 'El ticket ya está asignado a ese técnico';
    end if;

    set p_comentario = coalesce(nullif(trim(p_comentario), ''),
                                concat('Ticket asignado a ', fn_nombre_usuario(p_tecnico_id), '.'));

    update tickets set tecnico_id = p_tecnico_id where id = p_ticket_id;

    insert into ticket_historial (empresa_id, ticket_id, usuario_id, tipo, estado_anterior, estado_nuevo, tecnico_id, comentario)
    values (v_empresa, p_ticket_id, p_admin_id, 'Asignación', v_estado, v_estado, p_tecnico_id, p_comentario);

    commit;
end$$

-- módulo 3: cambia el estado de un ticket con comentario obligatorio.
-- lo puede hacer un administrador o el técnico asignado.
-- flujo permitido: Abierto -> En proceso -> Resuelto -> Cerrado (y Resuelto -> En proceso al reabrir).
-- ejemplo: call sp_cambiar_estado(3, 2, 'Resuelto', 'Se reemplazó el cable de red');
create procedure sp_cambiar_estado(
    in p_ticket_id int,
    in p_usuario_id int,
    in p_nuevo_estado varchar(20),
    in p_comentario text
)
begin
    declare v_empresa int;
    declare v_estado varchar(20);
    declare v_tecnico int;
    declare v_rol varchar(30);

    declare exit handler for sqlexception
    begin
        rollback;
        resignal;
    end;

    set p_comentario = trim(p_comentario);

    if p_comentario is null or char_length(p_comentario) < 5 or char_length(p_comentario) > 1000 then
        signal sqlstate '45000' set message_text = 'El comentario debe tener entre 5 y 1000 caracteres';
    end if;

    start transaction;

    select empresa_id, estado, tecnico_id
      into v_empresa, v_estado, v_tecnico
      from tickets
     where id = p_ticket_id
       for update;

    if v_empresa is null then
        signal sqlstate '45000' set message_text = 'El ticket no existe';
    end if;

    select r.nombre into v_rol
      from usuarios u
      join roles r on r.id = u.rol_id
     where u.id = p_usuario_id and u.empresa_id = v_empresa and u.activo = 1;

    if v_rol is null or not (v_rol = 'Administrador' or (v_rol = 'Técnico' and v_tecnico = p_usuario_id)) then
        signal sqlstate '45000' set message_text = 'Solo el administrador o el técnico asignado puede cambiar el estado';
    end if;

    if v_tecnico is null then
        signal sqlstate '45000' set message_text = 'Asigna un técnico antes de cambiar el estado';
    end if;

    if not ((v_estado = 'Abierto' and p_nuevo_estado = 'En proceso')
         or (v_estado = 'En proceso' and p_nuevo_estado = 'Resuelto')
         or (v_estado = 'Resuelto' and p_nuevo_estado in ('Cerrado', 'En proceso'))) then
        signal sqlstate '45000' set message_text = 'Cambio de estado no permitido';
    end if;

    if p_nuevo_estado = 'Resuelto' then
        update tickets set estado = p_nuevo_estado, resuelto_en = now() where id = p_ticket_id;
    elseif p_nuevo_estado = 'En proceso' then
        update tickets set estado = p_nuevo_estado, resuelto_en = null where id = p_ticket_id;
    else
        update tickets set estado = p_nuevo_estado where id = p_ticket_id;
    end if;

    insert into ticket_historial (empresa_id, ticket_id, usuario_id, tipo, estado_anterior, estado_nuevo, comentario)
    values (v_empresa, p_ticket_id, p_usuario_id, 'Cambio de estado', v_estado, p_nuevo_estado, p_comentario);

    commit;
end$$

-- módulo 3 y 5: agrega un comentario al ticket.
-- el solicitante solo comenta sus propios tickets. la notificación la crea trg_comentarios_ai.
-- ejemplo: call sp_agregar_comentario(3, 6, 'Sigue sin funcionar');
create procedure sp_agregar_comentario(
    in p_ticket_id int,
    in p_usuario_id int,
    in p_comentario text
)
begin
    declare v_empresa int;
    declare v_solicitante int;
    declare v_rol varchar(30);

    set p_comentario = trim(p_comentario);

    if p_comentario is null or char_length(p_comentario) < 1 or char_length(p_comentario) > 1000 then
        signal sqlstate '45000' set message_text = 'El comentario debe tener entre 1 y 1000 caracteres';
    end if;

    select empresa_id, solicitante_id
      into v_empresa, v_solicitante
      from tickets
     where id = p_ticket_id;

    if v_empresa is null then
        signal sqlstate '45000' set message_text = 'El ticket no existe';
    end if;

    select r.nombre into v_rol
      from usuarios u
      join roles r on r.id = u.rol_id
     where u.id = p_usuario_id and u.empresa_id = v_empresa and u.activo = 1;

    if v_rol is null then
        signal sqlstate '45000' set message_text = 'El usuario no pertenece a la empresa del ticket';
    end if;

    if v_rol = 'Solicitante' and v_solicitante <> p_usuario_id then
        signal sqlstate '45000' set message_text = 'Solo puedes comentar tus propios tickets';
    end if;

    insert into ticket_comentarios (empresa_id, ticket_id, usuario_id, comentario)
    values (v_empresa, p_ticket_id, p_usuario_id, p_comentario);
end$$

-- módulo 5: marca una notificación como leída
-- ejemplo: call sp_marcar_leida(10, 4);
create procedure sp_marcar_leida(in p_notificacion_id int, in p_usuario_id int)
begin
    update notificaciones
       set leida = 1
     where id = p_notificacion_id
       and usuario_id = p_usuario_id;

    select row_count() as filas;
end$$

-- módulo 5: marca todas las notificaciones del usuario como leídas
-- ejemplo: call sp_marcar_todas_leidas(4);
create procedure sp_marcar_todas_leidas(in p_usuario_id int)
begin
    update notificaciones
       set leida = 1
     where usuario_id = p_usuario_id
       and leida = 0;

    select row_count() as filas;
end$$

-- dashboard: resumen de una empresa en cuatro resultados
-- (por estado, por prioridad, por técnico y tiempo promedio de resolución).
-- las fechas y el área son opcionales: envía null para no filtrar.
-- ejemplo: call sp_resumen_empresa(1, '2026-10-01', '2026-10-31', null);
create procedure sp_resumen_empresa(
    in p_empresa_id int,
    in p_desde date,
    in p_hasta date,
    in p_area_id int
)
begin
    select t.estado, count(*) as total
      from tickets t
     where t.empresa_id = p_empresa_id
       and (p_desde is null or date(t.created_at) >= p_desde)
       and (p_hasta is null or date(t.created_at) <= p_hasta)
       and (p_area_id is null or t.area_id = p_area_id)
     group by t.estado
     order by field(t.estado, 'Abierto', 'En proceso', 'Resuelto', 'Cerrado');

    select t.prioridad, count(*) as total
      from tickets t
     where t.empresa_id = p_empresa_id
       and (p_desde is null or date(t.created_at) >= p_desde)
       and (p_hasta is null or date(t.created_at) <= p_hasta)
       and (p_area_id is null or t.area_id = p_area_id)
     group by t.prioridad
     order by field(t.prioridad, 'Alta', 'Media', 'Baja');

    select coalesce(fn_nombre_usuario(t.tecnico_id), 'Sin asignar') as responsable, count(*) as total
      from tickets t
     where t.empresa_id = p_empresa_id
       and (p_desde is null or date(t.created_at) >= p_desde)
       and (p_hasta is null or date(t.created_at) <= p_hasta)
       and (p_area_id is null or t.area_id = p_area_id)
     group by t.tecnico_id
     order by total desc;

    select t.prioridad, round(avg(timestampdiff(minute, t.created_at, t.resuelto_en)) / 60, 1) as horas_promedio
      from tickets t
     where t.empresa_id = p_empresa_id
       and t.resuelto_en is not null
       and (p_desde is null or date(t.created_at) >= p_desde)
       and (p_hasta is null or date(t.created_at) <= p_hasta)
       and (p_area_id is null or t.area_id = p_area_id)
     group by t.prioridad
     order by field(t.prioridad, 'Alta', 'Media', 'Baja');
end$$

delimiter ;
