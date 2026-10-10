-- sistema de tickets ti (multiempresa) - script de creación completo.
-- crea la base db_sistema_tickets_ti con tablas, funciones, vista, procedimientos y triggers.
-- no inserta datos: para eso ejecutar después sistema_tickets_datos.sql.
-- es re-ejecutable: elimina lo anterior y vuelve a crear todo.
-- uso: phpmyadmin > pestaña sql (o importar) o  mysql -u root < sistema_tickets_creacion.sql

-- crea la base de datos y elimina todo lo anterior del sistema (sirve para reiniciar).
-- cuidado: borra tablas, vistas, funciones y procedimientos con sus datos.

create database if not exists db_sistema_tickets_ti
    default character set utf8mb4 collate utf8mb4_general_ci;

use db_sistema_tickets_ti;
set names utf8mb4;

set foreign_key_checks = 0;

drop view if exists vw_tickets_sla;

drop procedure if exists sp_crear_notificacion;
drop procedure if exists sp_asignar_ticket;
drop procedure if exists sp_cambiar_estado;
drop procedure if exists sp_agregar_comentario;
drop procedure if exists sp_marcar_leida;
drop procedure if exists sp_marcar_todas_leidas;
drop procedure if exists sp_resumen_empresa;

drop function if exists fn_codigo_ticket;
drop function if exists fn_nombre_usuario;
drop function if exists fn_horas_sla;
drop function if exists fn_fecha_limite_sla;
drop function if exists fn_color_sla;
drop function if exists fn_contar_no_leidas;

drop table if exists tokens_revocados;
drop table if exists notificaciones;
drop table if exists ticket_comentarios;
drop table if exists ticket_historial;
drop table if exists ticket_evidencias;
drop table if exists tickets;
drop table if exists usuarios;
drop table if exists personas;
drop table if exists roles;
drop table if exists categorias;
drop table if exists areas;
drop table if exists empresas;

set foreign_key_checks = 1;

-- catálogos base: empresas, áreas, categorías y roles.
-- una empresa representa a cada cliente; todo lo demás cuelga de ella (multiempresa).

use db_sistema_tickets_ti;

create table empresas (
    id                     int auto_increment primary key,
    nombre                 varchar(120) not null unique,
    ruc                    char(11) null unique,
    sector                 varchar(60) null,
    num_trabajadores       int null,
    contacto_nombre        varchar(120) null,
    contacto_cargo         varchar(60) null,
    contacto_email         varchar(160) null,
    integrante_responsable varchar(120) null,
    activa                 tinyint(1) not null default 1,
    created_at             timestamp not null default current_timestamp
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

create table areas (
    id         int auto_increment primary key,
    empresa_id int not null,
    nombre     varchar(60) not null,
    unique key uq_area_empresa (empresa_id, nombre),
    foreign key (empresa_id) references empresas (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

create table categorias (
    id         int auto_increment primary key,
    empresa_id int not null,
    nombre     varchar(60) not null,
    unique key uq_categoria_empresa (empresa_id, nombre),
    foreign key (empresa_id) references empresas (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

create table roles (
    id     int auto_increment primary key,
    nombre varchar(30) not null unique
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

-- módulo 1: autenticación y usuarios.
-- el password guarda el hash bcrypt, nunca la contraseña en texto.
-- es_superadmin = 1 marca al administrador general del sistema (el grupo): no pertenece a una
-- empresa cliente y puede cambiar de empresa desde la aplicación para gestionarlas y probarlas.

use db_sistema_tickets_ti;

create table personas (
    id         int auto_increment primary key,
    empresa_id int not null,
    area_id    int null,
    nombres    varchar(60) not null,
    apellidos  varchar(60) not null,
    dni        char(8) null unique,
    telefono   varchar(15) null,
    created_at timestamp not null default current_timestamp,
    foreign key (empresa_id) references empresas (id),
    foreign key (area_id) references areas (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

create table usuarios (
    id         int auto_increment primary key,
    empresa_id int not null,
    persona_id int not null unique,
    rol_id     int not null,
    email      varchar(160) not null unique,
    password   varchar(255) not null,
    activo     tinyint(1) not null default 1,
    es_superadmin tinyint(1) not null default 0,
    created_at timestamp not null default current_timestamp,
    index idx_usuarios_empresa_rol (empresa_id, rol_id, activo),
    foreign key (empresa_id) references empresas (id),
    foreign key (persona_id) references personas (id),
    foreign key (rol_id) references roles (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

-- tokens jwt invalidados al cerrar sesión
create table tokens_revocados (
    id         int auto_increment primary key,
    jti        varchar(64) not null unique,
    usuario_id int not null,
    expira_en  datetime not null,
    created_at timestamp not null default current_timestamp,
    index idx_tokens_expira (expira_en),
    foreign key (usuario_id) references usuarios (id) on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

-- módulo 2: registro de tickets con evidencias fotográficas.
-- resuelto_en detiene el contador del sla (módulo 4).

use db_sistema_tickets_ti;

create table tickets (
    id             int auto_increment primary key,
    empresa_id     int not null,
    solicitante_id int not null,
    categoria_id   int not null,
    area_id        int null,
    tecnico_id     int null,
    asunto         varchar(120) not null,
    descripcion    text not null,
    prioridad      enum('Alta', 'Media', 'Baja') not null default 'Media',
    estado         enum('Abierto', 'En proceso', 'Resuelto', 'Cerrado') not null default 'Abierto',
    resuelto_en    datetime null,
    created_at     timestamp not null default current_timestamp,
    updated_at     timestamp not null default current_timestamp on update current_timestamp,
    index idx_tickets_empresa_estado (empresa_id, estado),
    index idx_tickets_empresa_prioridad (empresa_id, prioridad),
    index idx_tickets_empresa_fecha (empresa_id, created_at),
    foreign key (empresa_id) references empresas (id),
    foreign key (solicitante_id) references usuarios (id),
    foreign key (categoria_id) references categorias (id),
    foreign key (area_id) references areas (id),
    foreign key (tecnico_id) references usuarios (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

-- archivo es el nombre guardado en la carpeta uploads
create table ticket_evidencias (
    id              int auto_increment primary key,
    ticket_id       int not null,
    empresa_id      int not null,
    archivo         varchar(80) not null unique,
    nombre_original varchar(160) not null,
    mime            varchar(30) not null,
    tamano_bytes    int not null,
    created_at      timestamp not null default current_timestamp,
    index idx_evidencias_ticket (ticket_id),
    foreign key (ticket_id) references tickets (id) on delete cascade,
    foreign key (empresa_id) references empresas (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

-- módulo 3: asignación, estados e historial.
-- cada cambio guarda quién lo hizo, cuándo y un comentario obligatorio.

use db_sistema_tickets_ti;

create table ticket_historial (
    id              int auto_increment primary key,
    empresa_id      int not null,
    ticket_id       int not null,
    usuario_id      int not null,
    tipo            varchar(20) not null,
    estado_anterior varchar(20) null,
    estado_nuevo    varchar(20) null,
    tecnico_id      int null,
    comentario      text not null,
    created_at      timestamp not null default current_timestamp,
    index idx_historial_ticket (ticket_id, created_at),
    foreign key (empresa_id) references empresas (id),
    foreign key (ticket_id) references tickets (id) on delete cascade,
    foreign key (usuario_id) references usuarios (id),
    foreign key (tecnico_id) references usuarios (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

-- comentarios libres sobre un ticket; generan notificación de tipo comentario
create table ticket_comentarios (
    id         int auto_increment primary key,
    empresa_id int not null,
    ticket_id  int not null,
    usuario_id int not null,
    comentario text not null,
    created_at timestamp not null default current_timestamp,
    index idx_comentarios_ticket (ticket_id, created_at),
    foreign key (empresa_id) references empresas (id),
    foreign key (ticket_id) references tickets (id) on delete cascade,
    foreign key (usuario_id) references usuarios (id)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

-- módulo 5: notificaciones internas (campana con contador de no leídas).

use db_sistema_tickets_ti;

create table notificaciones (
    id         int auto_increment primary key,
    usuario_id int not null,
    ticket_id  int not null,
    tipo       enum('asignacion', 'cambio_estado', 'comentario') not null,
    mensaje    varchar(255) not null,
    leida      tinyint(1) not null default 0,
    created_at timestamp not null default current_timestamp,
    key idx_notificaciones_usuario (usuario_id, leida, created_at),
    foreign key (usuario_id) references usuarios (id) on delete cascade,
    foreign key (ticket_id) references tickets (id) on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_general_ci;

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

-- módulo 3: asigna un técnico a un ticket (lo hace un administrador de la empresa o el administrador general).
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
     where u.id = p_admin_id and (u.empresa_id = v_empresa or u.es_superadmin = 1) and u.activo = 1 and r.nombre = 'Administrador';

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
     where u.id = p_usuario_id and (u.empresa_id = v_empresa or u.es_superadmin = 1) and u.activo = 1;

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
     where u.id = p_usuario_id and (u.empresa_id = v_empresa or u.es_superadmin = 1) and u.activo = 1;

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
