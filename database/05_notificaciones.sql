CREATE TABLE IF NOT EXISTS `notificaciones` (
    `id`         INT AUTO_INCREMENT PRIMARY KEY,
    `usuario_id` INT NOT NULL,
    `ticket_id`  INT NOT NULL,
    `tipo`       ENUM('asignacion', 'cambio_estado', 'comentario') NOT NULL,
    `mensaje`    VARCHAR(255) NOT NULL,
    `leida`      TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_notificaciones_usuario` (`usuario_id`, `leida`, `created_at`),
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`),
    FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;