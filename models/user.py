"""Modelo del módulo de autenticación: consultas y reglas de usuarios."""
import re
import bcrypt
from pymysql.err import IntegrityError
from db import obtener_conexion

ROLES = ("Administrador", "Técnico", "Solicitante")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$")

class UserError(Exception):
    def __init__(self, mensaje, estado=400):
        super().__init__(mensaje)
        self.estado = estado

class User:
    @staticmethod
    def hashear(password):
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def password_correcta(password, hash_guardado):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hash_guardado.encode("utf-8"))
        except (ValueError, TypeError, AttributeError):
            return False

    @staticmethod
    def autenticar(email, password):
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(
                    "SELECT u.id, u.empresa_id, u.password, u.activo, u.es_superadmin, r.nombre AS rol, "
                    "CONCAT(p.nombres, ' ', p.apellidos) AS nombre "
                    "FROM usuarios u JOIN roles r ON r.id = u.rol_id "
                    "JOIN personas p ON p.id = u.persona_id WHERE u.email=%s",
                    (email.strip().lower(),))
                u = cur.fetchone()
        finally:
            con.close()
        if not u or not User.password_correcta(password, u["password"]):
            return None, "Correo o contraseña incorrectos."
        if not u["activo"]:
            return None, "Tu cuenta está inactiva. Contacta al administrador."
        return u, ""

    @staticmethod
    def listar(emp, q="", rol="", activo=""):
        sql = ("SELECT u.id, u.email, u.activo, r.nombre AS rol, p.nombres, p.apellidos, p.dni, "
               "p.telefono, p.area_id, a.nombre AS area "
               "FROM usuarios u JOIN roles r ON r.id = u.rol_id "
               "JOIN personas p ON p.id = u.persona_id "
               "LEFT JOIN areas a ON a.id = p.area_id WHERE u.empresa_id=%s")
        params = [emp]
        if q:
            sql += " AND (CONCAT(p.nombres,' ',p.apellidos) LIKE %s OR u.email LIKE %s OR p.dni LIKE %s)"
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if rol in ROLES:
            sql += " AND r.nombre=%s"; params.append(rol)
        if activo in ("0", "1"):
            sql += " AND u.activo=%s"; params.append(int(activo))
        sql += " ORDER BY p.apellidos, p.nombres"
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(sql, params)
                lista = cur.fetchall()
        finally:
            con.close()
        return lista

    @staticmethod
    def guardar(emp, yo, datos, superadmin=False):
        uid = str(datos.get("id", "")).strip()
        if uid and (not uid.isdigit() or int(uid) < 1):
            raise UserError("El identificador no es válido.")
        uid = int(uid) if uid else None
        nombres = datos.get("nombres", "").strip()
        apellidos = datos.get("apellidos", "").strip()
        dni = datos.get("dni", "").strip() or None
        telefono = datos.get("telefono", "").strip() or None
        email = datos.get("email", "").strip().lower()
        rol = datos.get("rol", "")
        area_id = datos.get("area_id") or None
        if area_id is not None:
            if isinstance(area_id, bool) or not str(area_id).isdigit() or int(area_id) < 1:
                raise UserError("Selecciona un área válida.")
            area_id = int(area_id)
        password = datos.get("password", "")
        activo = User.validar_activo(datos.get("activo", 0))
    
        error = ""
        if not 2 <= len(nombres) <= 60:
            error = "Ingresa los nombres (hasta 60 caracteres)."
        elif not 2 <= len(apellidos) <= 60:
            error = "Ingresa los apellidos (hasta 60 caracteres)."
        elif dni and not re.fullmatch(r"\d{8}", dni):
            error = "El DNI debe tener 8 dígitos."
        elif telefono and not re.fullmatch(r"\d{6,15}", telefono):
            error = "El teléfono solo debe tener números (6 a 15 dígitos)."
        elif not EMAIL_RE.match(email) or len(email) > 160:
            error = "Ingresa un correo electrónico válido."
        elif rol not in ROLES:
            error = "Selecciona un rol válido."
        elif (not uid or password) and not PASSWORD_RE.match(password):
            error = "La contraseña debe tener 8+ caracteres con minúscula, mayúscula, número y símbolo (!@#$%^&*)."
        elif uid and int(uid) == yo and (not activo or rol != "Administrador"):
            error = "No puedes desactivar tu cuenta ni quitarte el rol de administrador."
        if error:
            raise UserError(error)
        if len(password.encode("utf-8")) > 72:
            raise UserError("La contraseña no debe superar 72 bytes en UTF-8.")
    
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                if area_id:  # el área debe ser de la misma empresa
                    cur.execute("SELECT id FROM areas WHERE id=%s AND empresa_id=%s", (area_id, emp))
                    if not cur.fetchone():
                        raise UserError("El área no pertenece a esta empresa.")
                persona_id = 0
                if uid:
                    cur.execute("SELECT id, persona_id, es_superadmin FROM usuarios WHERE id=%s AND empresa_id=%s", (uid, emp))
                    actual = cur.fetchone()
                    if not actual:
                        raise UserError("El usuario no existe.", 404)
                    if actual["es_superadmin"] and not superadmin:
                        raise UserError("No puedes modificar al administrador general.", 403)
                    if actual["es_superadmin"] and (not activo or rol != "Administrador"):
                        raise UserError("El administrador general debe mantenerse activo y conservar su rol.")
                    persona_id = actual["persona_id"]
                cur.execute("SELECT id FROM usuarios WHERE email=%s AND id<>%s", (email, uid or 0))
                if cur.fetchone():
                    raise UserError("Este correo ya está registrado.", 409)
                if dni:
                    cur.execute("SELECT id FROM personas WHERE dni=%s AND id<>%s", (dni, persona_id))
                    if cur.fetchone():
                        raise UserError("Este DNI ya está registrado.", 409)
    
                if uid:
                    cur.execute("UPDATE personas SET nombres=%s, apellidos=%s, dni=%s, telefono=%s, area_id=%s "
                                "WHERE id=%s AND empresa_id=%s",
                                (nombres, apellidos, dni, telefono, area_id, persona_id, emp))
                    cur.execute("UPDATE usuarios SET email=%s, activo=%s, "
                                "rol_id=(SELECT id FROM roles WHERE nombre=%s) "
                                "WHERE id=%s AND empresa_id=%s", (email, activo, rol, uid, emp))
                    if password:
                        cur.execute("UPDATE usuarios SET password=%s WHERE id=%s AND empresa_id=%s",
                                    (User.hashear(password), uid, emp))
                    mensaje = "Cambios guardados correctamente."
                else:
                    cur.execute("INSERT INTO personas (empresa_id, area_id, nombres, apellidos, dni, telefono) "
                                "VALUES (%s,%s,%s,%s,%s,%s)", (emp, area_id, nombres, apellidos, dni, telefono))
                    persona_id = cur.lastrowid
                    cur.execute("INSERT INTO usuarios (empresa_id, persona_id, rol_id, email, password, activo) "
                                "VALUES (%s,%s,(SELECT id FROM roles WHERE nombre=%s),%s,%s,%s)",
                                (emp, persona_id, rol, email, User.hashear(password), activo))
                    uid = cur.lastrowid
                    mensaje = "Usuario registrado correctamente."
            con.commit()
            return int(uid), mensaje
        except IntegrityError as e:
            con.rollback()
            raise UserError("El correo o DNI ya existe, o los datos relacionados no son válidos.", 409) from e
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def validar_activo(valor):
        if valor in (True, 1, "1", "on"):
            return 1
        if valor in (False, 0, "0", "", None):
            return 0
        raise UserError("El estado activo debe ser 1 o 0.")

    @staticmethod
    def obtener(emp, uid):
        # La misma proyección pública que el listado: nunca expone el hash.
        return next((u for u in User.listar(emp) if u["id"] == uid), None)

    @staticmethod
    def sesion(uid):
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT u.id, u.empresa_id, u.activo, u.es_superadmin, "
                            "r.nombre AS rol, CONCAT(p.nombres,' ',p.apellidos) AS nombre "
                            "FROM usuarios u JOIN roles r ON r.id=u.rol_id "
                            "JOIN personas p ON p.id=u.persona_id WHERE u.id=%s", (uid,))
                return cur.fetchone()
        finally:
            con.close()

    @staticmethod
    def areas(emp):
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT id, nombre FROM areas WHERE empresa_id=%s ORDER BY nombre", (emp,))
                return cur.fetchall()
        finally:
            con.close()

    @staticmethod
    def empresas():
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT id, nombre FROM empresas WHERE activa=1 ORDER BY id")
                return cur.fetchall()
        finally:
            con.close()

    @staticmethod
    def cambiar_estado(emp, uid, yo, activo, superadmin=False):
        activo = User.validar_activo(activo)
        if uid == yo and not activo:
            raise UserError("No puedes desactivar tu propia cuenta.")
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT es_superadmin FROM usuarios WHERE id=%s AND empresa_id=%s FOR UPDATE", (uid, emp))
                usuario = cur.fetchone()
                if not usuario:
                    raise UserError("El usuario no existe.", 404)
                if usuario["es_superadmin"]:
                    raise UserError("No puedes desactivar al administrador general.", 403)
                cur.execute("UPDATE usuarios SET activo=%s WHERE id=%s AND empresa_id=%s", (activo, uid, emp))
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return activo

    @staticmethod
    def eliminar(emp, uid, yo):
        if uid == yo:
            raise UserError("No puedes eliminar tu propia cuenta.")
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT persona_id, es_superadmin FROM usuarios "
                            "WHERE id=%s AND empresa_id=%s FOR UPDATE", (uid, emp))
                usuario = cur.fetchone()
                if not usuario:
                    raise UserError("El usuario no existe.", 404)
                if usuario["es_superadmin"]:
                    raise UserError("No puedes eliminar al administrador general.", 403)
                # Se conserva toda la actividad del sistema; no se borran tickets ni auditoría.
                consultas = (
                    ("SELECT id FROM tickets WHERE solicitante_id=%s OR tecnico_id=%s LIMIT 1", (uid, uid)),
                    ("SELECT id FROM ticket_historial WHERE usuario_id=%s OR tecnico_id=%s LIMIT 1", (uid, uid)),
                    ("SELECT id FROM ticket_comentarios WHERE usuario_id=%s LIMIT 1", (uid,)),
                    ("SELECT id FROM notificaciones WHERE usuario_id=%s LIMIT 1", (uid,)),
                )
                for sql, params in consultas:
                    cur.execute(sql, params)
                    if cur.fetchone():
                        raise UserError("El usuario tiene actividad relacionada. Desactívalo para conservar sus registros.", 409)
                cur.execute("DELETE FROM usuarios WHERE id=%s AND empresa_id=%s", (uid, emp))
                cur.execute("DELETE FROM personas WHERE id=%s AND empresa_id=%s", (usuario["persona_id"], emp))
            con.commit()
        except IntegrityError as e:
            con.rollback()
            raise UserError("El usuario tiene registros relacionados. Puedes desactivarlo.", 409) from e
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
