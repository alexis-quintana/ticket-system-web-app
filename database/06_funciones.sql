-- funciones y vistas reutilizables.

use db_sistema_tickets_ti;
set names utf8mb4;

delimiter $$

-- módulo 2: código visible del ticket, por ejemplo tk-0007
create function fn_codigo_ticket(p_ticket_id int)
returns varchar(12)
deterministic
begin
    return concat('TK-', lpad(p_ticket_id, 4, '0'));
end$$

-- módulo 1: nombre completo de un usuario
create function fn_nombre_usuario(p_usuario_id int)
returns varchar(125)
not deterministic
reads sql data
begin
    declare v_nombre varchar(125);

    select concat(p.nombres, ' ', p.apellidos)
      into v_nombre
      from usuarios u
      join personas p on p.id = u.persona_id
     where u.id = p_usuario_id;

    return v_nombre;
end$$

-- módulo 4: horas máximas de resolución según la prioridad
create function fn_horas_sla(p_prioridad varchar(10))
returns int
deterministic
begin
    return case p_prioridad
        when 'Alta' then 4
        when 'Media' then 24
        when 'Baja' then 72
        else 24
    end;
end$$

-- módulo 4: fecha y hora en que vence el ticket
create function fn_fecha_limite_sla(p_prioridad varchar(10), p_creado datetime)
returns datetime
deterministic
begin
    return date_add(p_creado, interval fn_horas_sla(p_prioridad) hour);
end$$

-- módulo 4: color del semáforo (verde, amarillo o rojo).
-- si el ticket ya se resolvió, el contador se detiene en resuelto_en.
create function fn_color_sla(p_prioridad varchar(10), p_creado datetime, p_estado varchar(20), p_resuelto_en datetime)
returns varchar(10)
not deterministic
reads sql data
begin
    declare v_referencia datetime;
    declare v_restante int;
    declare v_color varchar(10);

    if p_estado in ('Resuelto', 'Cerrado') and p_resuelto_en is not null then
        set v_referencia = p_resuelto_en;
    else
        set v_referencia = now();
    end if;

    set v_restante = timestampdiff(second, v_referencia, fn_fecha_limite_sla(p_prioridad, p_creado));

    if v_restante <= 0 then
        set v_color = 'rojo';
    elseif v_restante <= fn_horas_sla(p_prioridad) * 3600 * 0.25 then
        set v_color = 'amarillo';
    else
        set v_color = 'verde';
    end if;

    return v_color;
end$$

-- módulo 5: cantidad de notificaciones sin leer (el número de la campana)
create function fn_contar_no_leidas(p_usuario_id int)
returns int
not deterministic
reads sql data
begin
    declare v_total int;

    select count(*)
      into v_total
      from notificaciones
     where usuario_id = p_usuario_id
       and leida = 0;

    return v_total;
end$$

delimiter ;

-- módulo 4: tickets con su fecha de vencimiento y semáforo ya calculados
create view vw_tickets_sla as
select t.id,
       fn_codigo_ticket(t.id) as codigo,
       t.empresa_id,
       t.asunto,
       t.prioridad,
       t.estado,
       t.tecnico_id,
       t.created_at,
       t.resuelto_en,
       fn_fecha_limite_sla(t.prioridad, t.created_at) as vence_en,
       fn_color_sla(t.prioridad, t.created_at, t.estado, t.resuelto_en) as semaforo
  from tickets t;
