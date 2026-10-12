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
