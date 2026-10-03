-- ============================================================
-- Módulo 3 — Asignación, estados e historial (Seminario)
-- Requiere (en este orden): 01_catalogos.sql, 02_inicio_sesion.sql, 03_tickets.sql
-- Columnas que este módulo usa de `tickets` (confirmar con Timaná):
--   id, empresa_id, asunto, descripcion, categoria_id, prioridad,
--   estado, solicitante_id, tecnico_id, created_at
-- ============================================================

CREATE TABLE IF NOT EXISTS ticket_historial (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id      INT NOT NULL,
    ticket_id       INT NOT NULL,
    usuario_id      INT NOT NULL,              -- autor del cambio
    tipo            VARCHAR(20) NOT NULL,      -- 'Asignación' | 'Cambio de estado'
    estado_anterior VARCHAR(20) NULL,
    estado_nuevo    VARCHAR(20) NULL,
    tecnico_id      INT NULL,                  -- técnico asignado (solo en 'Asignación')
    comentario      TEXT NOT NULL,             -- obligatorio en cada cambio
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_historial_ticket (ticket_id, created_at),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (ticket_id)  REFERENCES tickets(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
