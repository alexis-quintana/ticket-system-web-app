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
