
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS personas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT NOT NULL,
    area_id INT NULL,
    nombres VARCHAR(60) NOT NULL,
    apellidos VARCHAR(60) NOT NULL,
    dni CHAR(8) NULL UNIQUE,
    telefono VARCHAR(15) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (area_id) REFERENCES areas(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT NOT NULL,
    persona_id INT NOT NULL UNIQUE,
    rol_id INT NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (persona_id) REFERENCES personas(id),
    FOREIGN KEY (rol_id) REFERENCES roles(id)
) ENGINE=InnoDB;

-- DATOS INICIALES
INSERT IGNORE INTO roles (id, nombre) VALUES
    (1, 'Administrador'),
    (2, 'Técnico'),
    (3, 'Solicitante');

-- Usuario: admin@lexfixer.com   Contraseña: Admin12345
INSERT IGNORE INTO personas (id, empresa_id, nombres, apellidos, dni)
VALUES (1, 1, 'Administrador', 'General', '00000000');

INSERT IGNORE INTO usuarios (id, empresa_id, persona_id, rol_id, email, password)
VALUES (1, 1, 1, 1, 'admin@lexfixer.com', 'Admin12345');