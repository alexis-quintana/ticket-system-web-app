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
