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
