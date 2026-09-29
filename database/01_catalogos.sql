CREATE TABLE IF NOT EXISTS `empresas` (
    `id`     INT AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(120) NOT NULL UNIQUE,
    `ruc`    CHAR(11) NULL UNIQUE,
    `sector` VARCHAR(60) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `areas` (
    `id`         INT AUTO_INCREMENT PRIMARY KEY,
    `empresa_id` INT NOT NULL,
    `nombre`     VARCHAR(60) NOT NULL,
    UNIQUE KEY `uq_area_empresa` (`empresa_id`, `nombre`),
    FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `categorias` (
    `id`         INT AUTO_INCREMENT PRIMARY KEY,
    `empresa_id` INT NOT NULL,
    `nombre`     VARCHAR(60) NOT NULL,
    UNIQUE KEY `uq_categoria_empresa` (`empresa_id`, `nombre`),
    FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO `empresas` (`nombre`, `sector`) VALUES
    ('Clínica (demo)', 'Salud privada'),
    ('Azucarera (demo)', 'Agroindustria'),
    ('Transporte provincial (demo)', 'Transporte');

INSERT IGNORE INTO `categorias` (`empresa_id`, `nombre`)
SELECT e.`id`, c.`nombre`
FROM `empresas` e
CROSS JOIN (
    SELECT 'Red y conexión' AS `nombre`
    UNION ALL SELECT 'Software'
    UNION ALL SELECT 'Hardware'
    UNION ALL SELECT 'Accesos y cuentas'
) c;

INSERT IGNORE INTO `areas` (`empresa_id`, `nombre`)
SELECT e.`id`, a.`nombre`
FROM `empresas` e
CROSS JOIN (
    SELECT 'Administración' AS `nombre`
    UNION ALL SELECT 'Operaciones'
) a;