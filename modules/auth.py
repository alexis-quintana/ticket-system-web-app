import os, re
from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, session)
from db import obtener_conexion

bp = Blueprint("auth", __name__)
ROLES = ("Administrador", "Técnico", "Solicitante")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# Destino tras login según rol (cambiar cuando existan los módulos de los demás)
# INTEGRACIÓN: todos los roles entran por /inicio (antes: Administrador -> /usuarios, resto -> /)
DESTINO = {"Administrador": "/inicio", "Técnico": "/inicio", "Solicitante": "/inicio"}


# ---------- Configuración (se ejecuta sola al registrar el blueprint) ----------
@bp.record_once
def _configurar(state):
    # La sesión de Flask necesita una clave secreta para firmar la cookie
    state.app.secret_key = state.app.secret_key or os.environ.get("SECRET_KEY", "dev-clave-secreta")


# ---------- Decorador de protección por rol ----------
# Los datos del usuario logueado quedan en session:
#   session["usuario_id"], session["empresa_id"], session["rol"], session["nombre"]
def roles_required(*roles):
    """@roles_required() = cualquier usuario logueado.
       @roles_required("Administrador", "Técnico") = solo esos roles."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if "usuario_id" not in session:
                if request.path.startswith("/api"):
                    return jsonify(error="Debes iniciar sesión"), 401
                flash("Inicia sesión para continuar.", "warning")
                return redirect(url_for("auth.login"))
            if roles and session.get("rol") not in roles:
                if request.path.startswith("/api"):
                    return jsonify(error="Sin permiso"), 403
                flash("No tienes permiso para acceder a esa sección.", "danger")
                return redirect(url_for("auth.login"))
            return fn(*a, **kw)
        return wrapper
    return deco


@bp.app_context_processor
def inyectar_usuario():
    """Disponible en todas las plantillas como `usuario_actual`."""
    if "usuario_id" in session:
        nombre = session.get("nombre", "")
        ini = "".join(p[0] for p in nombre.split()[:2]).upper()
        return {"usuario_actual": {"usuario_id": session["usuario_id"],
                                   "empresa_id": session["empresa_id"],
                                   "rol": session["rol"], "nombre": nombre,
                                   "iniciales": ini}}
    return {"usuario_actual": None}


def _autenticar(email, password):
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.empresa_id, u.password, u.activo, r.nombre AS rol, "
                "CONCAT(p.nombres, ' ', p.apellidos) AS nombre "
                "FROM usuarios u JOIN roles r ON r.id = u.rol_id "
                "JOIN personas p ON p.id = u.persona_id WHERE u.email=%s",
                (email.strip().lower(),))
            u = cur.fetchone()
    finally:
        con.close()
    if not u or password != u["password"]:
        return None, "Correo o contraseña incorrectos."
    if not u["activo"]:
        return None, "Tu cuenta está inactiva. Contacta al administrador."
    return u, ""


def _iniciar_sesion(u):
    session.clear()
    session["usuario_id"] = u["id"]
    session["empresa_id"] = u["empresa_id"]
    session["rol"] = u["rol"]
    session["nombre"] = u["nombre"]


# ---------- Login / logout ----------
@bp.route("/login")
def login():
    return render_template("auth/login.html", email="", role="")


@bp.route("/procesar_login", methods=["POST"])
def procesar_login():
    """Recibe el FormData del fetch (igual que en clase) y responde JSON."""
    try:
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        rol = request.form.get("role", "")
        if not EMAIL_RE.match(email.strip()) or len(password) < 8 or rol not in ROLES:
            return jsonify(ok=False, mensaje="Completa rol, correo válido y contraseña (mínimo 8 caracteres)."), 400
        u, err = _autenticar(email, password)
        if u and u["rol"] != rol:
            u, err = None, "Tu cuenta no tiene el rol " + rol + "."
        if not u:
            return jsonify(ok=False, mensaje=err), 401
        _iniciar_sesion(u)
        return jsonify(ok=True, destino=DESTINO.get(u["rol"], "/"))
    except Exception as e:
        print(repr(e))
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()   # borra los datos de la sesión
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/recuperar")
def recuperar():
    return render_template("auth/recuperar.html")


# ---------- Gestión de usuarios (solo Administrador, filtrado por empresa_id) ----------
@bp.route("/usuarios")
@roles_required("Administrador")
def usuarios():
    emp = session["empresa_id"]
    q = request.args.get("q", "").strip()
    rol = request.args.get("rol", "")
    activo = request.args.get("activo", "")
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
            cur.execute("SELECT id, nombre FROM areas WHERE empresa_id=%s ORDER BY nombre", (emp,))
            areas = cur.fetchall()
    finally:
        con.close()
    return render_template("auth/usuarios.html", usuarios=lista, areas=areas, roles=ROLES,
                           f={"q": q, "rol": rol, "activo": activo})


PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$")


@bp.route("/procesar_usuario", methods=["POST"])
@roles_required("Administrador")
def procesar_usuario():
    """Crea o edita persona + usuario de la empresa del admin. Responde JSON (fetch)."""
    emp, yo = session["empresa_id"], session["usuario_id"]
    uid = request.form.get("id", "").strip()
    nombres = request.form.get("nombres", "").strip()
    apellidos = request.form.get("apellidos", "").strip()
    dni = request.form.get("dni", "").strip() or None
    telefono = request.form.get("telefono", "").strip() or None
    email = request.form.get("email", "").strip().lower()
    rol = request.form.get("rol", "")
    area_id = request.form.get("area_id") or None
    password = request.form.get("password", "")
    activo = 1 if request.form.get("activo") else 0

    error = ""
    if not nombres or len(nombres) > 60:
        error = "Ingresa los nombres (hasta 60 caracteres)."
    elif not apellidos or len(apellidos) > 60:
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
        return jsonify(ok=False, mensaje=error), 400

    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            if area_id:  # el área debe ser de la misma empresa
                cur.execute("SELECT id FROM areas WHERE id=%s AND empresa_id=%s", (area_id, emp))
                if not cur.fetchone():
                    area_id = None
            persona_id = 0
            if uid:
                cur.execute("SELECT id, persona_id FROM usuarios WHERE id=%s AND empresa_id=%s", (uid, emp))
                actual = cur.fetchone()
                if not actual:
                    return jsonify(ok=False, mensaje="El usuario no existe."), 404
                persona_id = actual["persona_id"]
            cur.execute("SELECT id FROM usuarios WHERE email=%s AND id<>%s", (email, uid or 0))
            if cur.fetchone():
                return jsonify(ok=False, mensaje="Este correo ya está registrado."), 409
            if dni:
                cur.execute("SELECT id FROM personas WHERE dni=%s AND id<>%s", (dni, persona_id))
                if cur.fetchone():
                    return jsonify(ok=False, mensaje="Este DNI ya está registrado."), 409

            if uid:
                cur.execute("UPDATE personas SET nombres=%s, apellidos=%s, dni=%s, telefono=%s, area_id=%s "
                            "WHERE id=%s AND empresa_id=%s",
                            (nombres, apellidos, dni, telefono, area_id, persona_id, emp))
                cur.execute("UPDATE usuarios SET email=%s, activo=%s, "
                            "rol_id=(SELECT id FROM roles WHERE nombre=%s) "
                            "WHERE id=%s AND empresa_id=%s", (email, activo, rol, uid, emp))
                if password:
                    cur.execute("UPDATE usuarios SET password=%s WHERE id=%s AND empresa_id=%s",
                                (password, uid, emp))
                mensaje = "Cambios guardados correctamente."
            else:
                cur.execute("INSERT INTO personas (empresa_id, area_id, nombres, apellidos, dni, telefono) "
                            "VALUES (%s,%s,%s,%s,%s,%s)", (emp, area_id, nombres, apellidos, dni, telefono))
                persona_id = cur.lastrowid
                cur.execute("INSERT INTO usuarios (empresa_id, persona_id, rol_id, email, password, activo) "
                            "VALUES (%s,%s,(SELECT id FROM roles WHERE nombre=%s),%s,%s,%s)",
                            (emp, persona_id, rol, email, password, activo))
                mensaje = "Usuario registrado correctamente."
        con.commit()
        return jsonify(ok=True, mensaje=mensaje)
    except Exception as e:
        con.rollback()
        print(repr(e))
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500
    finally:
        con.close()


# ---------- API REST de usuarios ----------
@bp.route("/api/usuarios")
@roles_required("Administrador")
def api_usuarios():
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT u.id, u.email, u.activo, r.nombre AS rol, p.nombres, p.apellidos, "
                        "p.dni, p.telefono, p.area_id "
                        "FROM usuarios u JOIN roles r ON r.id=u.rol_id JOIN personas p ON p.id=u.persona_id "
                        "WHERE u.empresa_id=%s", (session["empresa_id"],))
            return jsonify(cur.fetchall())
    finally:
        con.close()
