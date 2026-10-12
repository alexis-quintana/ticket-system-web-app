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
