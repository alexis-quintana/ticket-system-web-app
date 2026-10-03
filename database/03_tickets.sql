CREATE TABLE IF NOT EXISTS tickets (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id     INT NOT NULL,
    solicitante_id INT NOT NULL,              
    categoria_id   INT NOT NULL,
    tecnico_id     INT NULL,                  
    asunto         VARCHAR(120) NOT NULL,
    descripcion    TEXT NOT NULL,
    prioridad      ENUM('Alta', 'Media', 'Baja') NOT NULL DEFAULT 'Media',
    estado         ENUM('Abierto', 'En proceso', 'Resuelto', 'Cerrado') NOT NULL DEFAULT 'Abierto',
    resuelto_en    DATETIME NULL,             -- lo usa el módulo 4 (SLA) para detener el contador
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tickets_empresa_estado (empresa_id, estado),
    INDEX idx_tickets_empresa_prioridad (empresa_id, prioridad),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
    FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ticket_evidencias (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id       INT NOT NULL,
    empresa_id      INT NOT NULL,
    archivo         VARCHAR(80) NOT NULL UNIQUE,  
    nombre_original VARCHAR(160) NOT NULL,
    mime            VARCHAR(30) NOT NULL,
    tamano_bytes    INT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_evidencias_ticket (ticket_id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;