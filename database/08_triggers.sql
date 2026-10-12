-- triggers: reglas que la base aplica sola, aunque el dato llegue desde fuera de la aplicación.

use db_sistema_tickets_ti;
set names utf8mb4;

delimiter $$

-- módulo 1: el correo siempre se guarda en minúsculas y sin espacios
create trigger trg_usuarios_bi before insert on usuarios
for each row
begin
    set new.email = lower(trim(new.email));
end$$

create trigger trg_usuarios_bu before update on usuarios
for each row
begin
    set new.email = lower(trim(new.email));
end$$

-- módulo 2: un ticket no puede mezclar datos de otra empresa (el administrador general es la excepción).
-- si no se indica el área, se toma la del solicitante.
create trigger trg_tickets_bi before insert on tickets
for each row
begin
    if exists (select 1 from usuarios
                where id = new.solicitante_id
                  and empresa_id <> new.empresa_id
                  and es_superadmin = 0) then
        signal sqlstate '45000' set message_text = 'El solicitante no pertenece a la empresa del ticket';
    end if;

    if new.tecnico_id is not null
       and (select empresa_id from usuarios where id = new.tecnico_id) <> new.empresa_id then
        signal sqlstate '45000' set message_text = 'El técnico no pertenece a la empresa del ticket';
    end if;

    if (select empresa_id from categorias where id = new.categoria_id) <> new.empresa_id then
        signal sqlstate '45000' set message_text = 'La categoría no pertenece a la empresa del ticket';
    end if;

    if new.area_id is null then
        set new.area_id = (select p.area_id
                             from usuarios u
                             join personas p on p.id = u.persona_id
                            where u.id = new.solicitante_id);
    end if;
end$$

-- módulo 3 y 4: un ticket cerrado ya no cambia de estado ni de técnico;
-- al pasar a resuelto se guarda la hora para detener el contador del sla.
create trigger trg_tickets_bu before update on tickets
for each row
begin
    if old.estado = 'Cerrado'
       and (new.estado <> old.estado or not (new.tecnico_id <=> old.tecnico_id)) then
        signal sqlstate '45000' set message_text = 'Un ticket cerrado no se puede modificar';
    end if;

    if new.tecnico_id is not null
       and (select empresa_id from usuarios where id = new.tecnico_id) <> new.empresa_id then
        signal sqlstate '45000' set message_text = 'El técnico no pertenece a la empresa del ticket';
    end if;

    if new.estado = 'Resuelto' and old.estado <> 'Resuelto' and new.resuelto_en is null then
        set new.resuelto_en = now();
    end if;
end$$

-- módulo 3: el historial exige comentario y debe ser de la misma empresa del ticket
create trigger trg_historial_bi before insert on ticket_historial
for each row
begin
    if new.comentario is null or trim(new.comentario) = '' then
        signal sqlstate '45000' set message_text = 'El comentario es obligatorio en cada cambio';
    end if;

    if (select empresa_id from tickets where id = new.ticket_id) <> new.empresa_id then
        signal sqlstate '45000' set message_text = 'El historial no coincide con la empresa del ticket';
    end if;
end$$

-- módulo 5: cada asignación o cambio de estado genera su notificación.
-- la asignación avisa al técnico; el cambio de estado avisa al solicitante.
create trigger trg_historial_ai after insert on ticket_historial
for each row
begin
    declare v_solicitante int;
    declare v_asunto varchar(120);

    select solicitante_id, asunto
      into v_solicitante, v_asunto
      from tickets
     where id = new.ticket_id;

    if new.tipo = 'Asignación' then
        if new.tecnico_id is not null and new.tecnico_id <> new.usuario_id then
            insert into notificaciones (usuario_id, ticket_id, tipo, mensaje, created_at)
            values (new.tecnico_id, new.ticket_id, 'asignacion',
                    concat('Se te asignó el ticket ', fn_codigo_ticket(new.ticket_id), ': ', v_asunto),
                    new.created_at);
        end if;
    elseif new.tipo = 'Cambio de estado' then
        if v_solicitante <> new.usuario_id then
            insert into notificaciones (usuario_id, ticket_id, tipo, mensaje, created_at)
            values (v_solicitante, new.ticket_id, 'cambio_estado',
                    concat(fn_codigo_ticket(new.ticket_id), ' cambió de estado: ', new.estado_anterior, ' → ', new.estado_nuevo),
                    new.created_at);
        end if;
    end if;
end$$

-- módulo 3: el comentario no puede estar vacío y debe ser de la empresa del ticket
create trigger trg_comentarios_bi before insert on ticket_comentarios
for each row
begin
    if new.comentario is null or trim(new.comentario) = '' then
        signal sqlstate '45000' set message_text = 'El comentario no puede estar vacío';
    end if;

    if (select empresa_id from tickets where id = new.ticket_id) <> new.empresa_id then
        signal sqlstate '45000' set message_text = 'El comentario no coincide con la empresa del ticket';
    end if;
end$$

-- módulo 5: un comentario avisa al solicitante y al técnico asignado (menos a quien lo escribió)
create trigger trg_comentarios_ai after insert on ticket_comentarios
for each row
begin
    declare v_solicitante int;
    declare v_tecnico int;
    declare v_asunto varchar(120);

    select solicitante_id, tecnico_id, asunto
      into v_solicitante, v_tecnico, v_asunto
      from tickets
     where id = new.ticket_id;

    if v_solicitante <> new.usuario_id then
        insert into notificaciones (usuario_id, ticket_id, tipo, mensaje, created_at)
        values (v_solicitante, new.ticket_id, 'comentario',
                concat('Nuevo comentario en ', fn_codigo_ticket(new.ticket_id), ': ', v_asunto),
                new.created_at);
    end if;

    if v_tecnico is not null and v_tecnico <> new.usuario_id then
        insert into notificaciones (usuario_id, ticket_id, tipo, mensaje, created_at)
        values (v_tecnico, new.ticket_id, 'comentario',
                concat('Nuevo comentario en ', fn_codigo_ticket(new.ticket_id), ': ', v_asunto),
                new.created_at);
    end if;
end$$

delimiter ;
