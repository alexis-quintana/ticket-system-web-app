# Sistema de Tickets TI

Sistema web de gestión de tickets de Soporte TI con seguimiento de SLA, notificaciones y reportes. Desarrollado con Python, Flask y MySQL.

## Descripción

Plataforma que permite registrar, asignar y hacer seguimiento de incidencias de soporte TI dentro de una organización. Los usuarios pueden crear tickets, y el área de TI puede gestionarlos hasta su resolución.

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python + Flask |
| Base de datos | MySQL |
| Frontend | HTML, CSS, JavaScript |

## Integrantes y módulos

| Integrante | N° Módulo | Descripción del Módulo |
|------------|-----------|------------------------|
| Montenegro Urrutia, Juan Diego | 1 | Autenticación y usuarios |
| Timaná Novoa, Juan Diego | 2 | Registro de tickets con evidencias |
| Seminario Bautista, Lorena Marialya | 3 | Asignación, estados e historial |
| Ordoñez Cavero, Martín Benjamín | 4 | SLA y semáforo visual |
| Quintana Luis, Alexis Abel | 5 | Notificaciones internas |

## Cómo ejecutar

1. Iniciar Apache y MySQL en XAMPP.
2. En phpMyAdmin (pestaña SQL o Importar), ejecutar en orden `database/sistema_tickets.sql` (crea la base, tablas, funciones, procedimientos y triggers) y luego `database/sistema_tickets_datos.sql` (empresas, usuarios y tickets demo). Ambos se pueden volver a ejecutar para reiniciar. La misma estructura dividida por módulos está en `database/00_reiniciar_base.sql` … `database/09_datos_demo.sql`.
3. Ejecutar `setup.bat` (una sola vez por computadora).
4. Ejecutar `run.bat` y abrir `http://127.0.0.1:5000/`.

---

## Información académica

- **Universidad:** Universidad Católica Santo Toribio de Mogrovejo (USAT)
- **Curso:** Desarrollo de Aplicaciones Web
- **Ciclo:** VI — 2026-II
- **Docente:** Mg. Ing. Junior Eugenio Cachay Maco
