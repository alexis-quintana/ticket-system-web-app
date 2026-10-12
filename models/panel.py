import re

from db import obtener_conexion
from models.user import User, PASSWORD_RE
from modules.sla import calcular_sla

ESTADOS = ("Abierto", "En proceso", "Resuelto", "Cerrado")
PRIORIDADES = ("Alta", "Media", "Baja")
ACTIVOS = ("Abierto", "En proceso")
SLA_ETIQUETAS = {"verde": "En plazo", "amarillo": "Por vencer", "rojo": "Vencido"}


# Error de validación que se muestra al usuario en la pantalla de perfil
class PerfilError(Exception):
    pass


# Números de las páginas Inicio y Dashboard; solo lee tickets (SELECT parametrizados y filtrados por empresa_id)
class Resumen:

    # Tickets que el usuario puede ver: los de su empresa (el Solicitante, solo los suyos)
    @staticmethod
    def tickets_visibles(usuario, columnas, extra="", limite=None):
        sql = ("SELECT " + columnas + " FROM tickets t JOIN categorias c ON c.id = t.categoria_id "
               "WHERE t.empresa_id=%s")
        params = [usuario["empresa_id"]]
        if usuario["rol"] == "Solicitante":
            sql += " AND t.solicitante_id=%s"
            params.append(usuario["usuario_id"])
        sql += extra
        if limite:
            sql += " LIMIT %s"
            params.append(limite)
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            con.close()

    # Los 5 tickets más recientes
    @staticmethod
    def recientes(usuario):
        return Resumen.tickets_visibles(usuario, "t.id, t.asunto, t.estado, t.prioridad, t.created_at",
                                        " ORDER BY t.id DESC", limite=5)

    # [(etiqueta, cantidad, porcentaje)] para los gráficos de barras HTML
    @staticmethod
    def barras(conteo, total):
        return [(k, v, round(v * 100 / total) if total else 0) for k, v in conteo.items()]

    # Todo lo que necesita la plantilla del dashboard
    @staticmethod
    def dashboard(usuario):
        filas = Resumen.tickets_visibles(usuario, "t.estado, t.prioridad, t.created_at, t.resuelto_en, c.nombre AS categoria")
        total = len(filas)
        por_estado = {e: 0 for e in ESTADOS}
        por_prioridad = {p: 0 for p in PRIORIDADES}
        por_sla = {e: 0 for e in SLA_ETIQUETAS.values()}
        por_categoria = {}
        for t in filas:
            por_estado[t["estado"]] += 1
            por_prioridad[t["prioridad"]] += 1
            por_categoria[t["categoria"]] = por_categoria.get(t["categoria"], 0) + 1
            if t["estado"] in ACTIVOS:   # el semáforo solo importa en tickets aún sin resolver
                color = calcular_sla(t["prioridad"], t["created_at"], t["estado"], t["resuelto_en"],
                                     usuario["empresa_id"])["color"]
                por_sla[SLA_ETIQUETAS[color]] += 1
        activos = sum(por_estado[e] for e in ACTIVOS)
        return dict(total=total, activos=activos,
                    por_vencer=por_sla["Por vencer"], vencidos=por_sla["Vencido"],
                    estados=Resumen.barras(por_estado, total), prioridades=Resumen.barras(por_prioridad, total),
                    sla=Resumen.barras(por_sla, activos),
                    categorias=Resumen.barras(dict(sorted(por_categoria.items(), key=lambda x: -x[1])), total))


# Datos de la propia cuenta del usuario: ficha, teléfono y contraseña
class Perfil:

    # Datos del usuario conectado y, si no es administrador, a quién escribir para corregirlos
    @staticmethod
    def datos(usuario):
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT u.email, p.nombres, p.apellidos, p.dni, p.telefono, "
                            "a.nombre AS area, e.nombre AS empresa "
                            "FROM usuarios u JOIN personas p ON p.id = u.persona_id "
                            "JOIN empresas e ON e.id = u.empresa_id "
                            "LEFT JOIN areas a ON a.id = p.area_id "
                            "WHERE u.id=%s",     # solo su propia cuenta; el superadmin puede estar viendo otra empresa
                            (usuario["usuario_id"],))
                datos = cur.fetchone() or {}
            admins = []
            if usuario["rol"] != "Administrador":
                with con.cursor() as cur:
                    cur.execute("SELECT p.nombres, p.apellidos, u.email "
                                "FROM usuarios u JOIN personas p ON p.id = u.persona_id "
                                "JOIN roles r ON r.id = u.rol_id "
                                "WHERE u.empresa_id=%s AND r.nombre='Administrador' AND u.activo=1 "
                                "AND u.es_superadmin=0 ORDER BY u.id", (usuario["empresa_id"],))
                    admins = cur.fetchall()
        finally:
            con.close()
        return datos, admins

    # Cambia el teléfono (vacío lo borra); devuelve True si quedó con teléfono
    @staticmethod
    def cambiar_telefono(usuario_id, telefono):
        telefono = telefono.strip()
        if telefono and not re.fullmatch(r"\d{6,15}", telefono):
            raise PerfilError("El teléfono solo debe tener números (6 a 15 dígitos).")
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("UPDATE personas SET telefono=%s "
                            "WHERE id=(SELECT persona_id FROM usuarios WHERE id=%s)",
                            (telefono or None, usuario_id))
            con.commit()
        finally:
            con.close()
        return bool(telefono)

    # Cambia la contraseña después de validar la actual y las reglas de la nueva
    @staticmethod
    def cambiar_password(usuario_id, actual, nueva, confirmar):
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT password FROM usuarios WHERE id=%s", (usuario_id,))
                fila = cur.fetchone() or {}
            error = ""
            if not actual or not nueva or not confirmar:
                error = "Completa los tres campos."
            elif not User.password_correcta(actual, fila.get("password", "")):
                error = "La contraseña actual no es correcta."
            elif not PASSWORD_RE.match(nueva):
                error = "La nueva contraseña debe tener 8+ caracteres con minúscula, mayúscula, número y símbolo (!@#$%^&*)."
            elif len(nueva.encode("utf-8")) > 72:
                error = "La nueva contraseña no puede superar 72 caracteres."
            elif nueva == actual:
                error = "La nueva contraseña debe ser distinta de la actual."
            elif nueva != confirmar:
                error = "La confirmación no coincide con la nueva contraseña."
            if error:
                raise PerfilError(error)
            with con.cursor() as cur:
                cur.execute("UPDATE usuarios SET password=%s WHERE id=%s", (User.hashear(nueva), usuario_id))
            con.commit()
        finally:
            con.close()
