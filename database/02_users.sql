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
