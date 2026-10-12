"""Controlador de autenticación. El SQL y las reglas están en models/user.py."""
import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from werkzeug.exceptions import BadRequest
from models.user import User, UserError, ROLES, EMAIL_RE, PASSWORD_RE

bp = Blueprint("auth", __name__)
# Compatibilidad: panel.py ya importa estas funciones.
_hashear = User.hashear
_password_correcta = User.password_correcta


def respuesta(code, data, msge, estado=200):
    """El mismo diccionario de respuesta que se construye en clase."""
    rpta = dict()
    rpta['code'] = code
    rpta['data'] = data
    rpta['msge'] = msge
    return jsonify(rpta), estado


def ruta_json(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except UserError as e:
            return respuesta(-1, None, str(e), e.estado)
        except BadRequest:
            return respuesta(-1, None, "El cuerpo JSON no es válido.", 400)
        except Exception:
            current_app.logger.exception("Error en autenticación o usuarios")
            return respuesta(-1, None, "Error en el servidor. Inténtalo de nuevo.", 500)
    return wrapper


def datos_peticion():
    datos = request.get_json() if request.is_json else request.form.to_dict()
    if not isinstance(datos, dict):
        raise UserError("Envía un objeto JSON o un formulario.")
    # Evita errores de tipo con JSON: un nombre, correo o clave deben ser textos.
    for campo in ('nombres', 'apellidos', 'dni', 'telefono', 'email', 'rol', 'password'):
        if campo in datos and not isinstance(datos[campo], str):
            raise UserError("El campo " + campo + " debe ser texto.")
    return datos


@bp.record_once
def _configurar(state):
    state.app.secret_key = state.app.secret_key or os.environ.get("SECRET_KEY", "dev-clave-secreta")


def _es_json():
    return request.path.startswith('/api/') or request.path in ('/procesar_login', '/procesar_usuario')


@bp.before_app_request
def actualizar_sesion():
    """Un usuario eliminado/inactivo pierde acceso en su siguiente petición."""
    if 'usuario_id' not in session or request.endpoint == 'static':
        return
    try:
        u = User.sesion(session['usuario_id'])
    except Exception:
        current_app.logger.exception("No se pudo comprobar la sesión")
        if _es_json():
            return respuesta(-1, None, "No se pudo verificar la sesión.", 503)
        return "No se pudo verificar la sesión. Inténtalo de nuevo.", 503
    if not u or not u['activo']:
        session.clear()
        if _es_json():
            return respuesta(-1, None, "Tu sesión terminó. Inicia sesión nuevamente.", 401)
        return redirect(url_for('auth.login'))
    session['rol'] = u['rol']
    session['nombre'] = u['nombre']
    session['superadmin'] = bool(u['es_superadmin'])
    if not u['es_superadmin']:
        session['empresa_id'] = u['empresa_id']


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if 'usuario_id' not in session:
                if _es_json():
                    return respuesta(-1, None, "Debes iniciar sesión.", 401)
                flash("Inicia sesión para continuar.", "warning")
                return redirect(url_for('auth.login'))
            if roles and session.get('rol') not in roles:
                if _es_json():
                    return respuesta(-1, None, "No tienes permiso.", 403)
                flash("No tienes permiso para acceder a esa sección.", "danger")
                return redirect('/inicio')
            return fn(*a, **kw)
        return wrapper
    return deco


@bp.app_context_processor
def inyectar_usuario():
    if 'usuario_id' not in session:
        return {'usuario_actual': None}
    nombre = session.get('nombre', '')
    empresas = User.empresas()
    return {'usuario_actual': dict(
        usuario_id=session['usuario_id'], empresa_id=session['empresa_id'],
        empresa_nombre=next((e['nombre'] for e in empresas if e['id'] == session['empresa_id']), ''),
        superadmin=bool(session.get('superadmin')),
        empresas=empresas if session.get('superadmin') else [],
        rol=session['rol'], nombre=nombre,
        iniciales=''.join(p[0] for p in nombre.split()[:2]).upper())}


def _iniciar_sesion(u):
    session.clear()
    session.update(usuario_id=u['id'], empresa_id=u['empresa_id'], rol=u['rol'],
                   nombre=u['nombre'], superadmin=bool(u['es_superadmin']))


@bp.route('/login')
def login():
    if 'usuario_id' in session:
        return redirect('/inicio')
    return render_template('auth/login.html', email='')


@bp.route('/api/login', methods=['POST'])
@bp.route('/procesar_login', methods=['POST'])
@ruta_json
def procesar_login():
    datos = datos_peticion()
    email, password = datos.get('email', '').strip(), datos.get('password', '')
    if not EMAIL_RE.fullmatch(email) or not password:
        raise UserError("Ingresa tu correo válido y contraseña.")
    u, error = User.autenticar(email, password)
    if not u:
        return respuesta(-1, None, error, 401)
    _iniciar_sesion(u)
    data = dict()
    data['usuario_id'] = u['id']
    data['nombre'] = u['nombre']
    data['rol'] = u['rol']  # Siempre procede de la BD; no se recibe del formulario.
    data['destino'] = '/inicio'
    return respuesta(1, data, "Sesión iniciada correctamente.")


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('auth.login'))


@bp.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return respuesta(1, None, "Sesión cerrada correctamente.")


@bp.route('/cambiar_empresa', methods=['POST'])
@roles_required('Administrador')
def cambiar_empresa():
    if not session.get('superadmin'):
        flash("No tienes permiso para cambiar de empresa.", "danger")
        return redirect('/inicio')
    empresa = next((e for e in User.empresas() if str(e['id']) == request.form.get('empresa_id')), None)
    if empresa:
        session['empresa_id'] = empresa['id']
        flash("Ahora trabajas con " + empresa['nombre'] + ".", "success")
    else:
        flash("La empresa seleccionada no existe.", "danger")
    return redirect('/inicio')


@bp.route('/recuperar')
def recuperar():
    return render_template('auth/recuperar.html')


@bp.route('/usuarios')
@roles_required('Administrador')
def usuarios():
    f = {k: request.args.get(k, '').strip() for k in ('q', 'rol', 'activo')}
    return render_template('auth/usuarios.html', usuarios=User.listar(session['empresa_id'], **f),
                           areas=User.areas(session['empresa_id']), roles=ROLES, f=f)


@bp.route('/procesar_usuario', methods=['POST'])
@roles_required('Administrador')
@ruta_json
def procesar_usuario():
    datos = datos_peticion()
    uid, mensaje = User.guardar(session['empresa_id'], session['usuario_id'], datos, session.get('superadmin', False))
    return respuesta(1, dict(id=uid), mensaje)


@bp.route('/api/usuarios', methods=['GET', 'POST'])
@roles_required('Administrador')
@ruta_json
def api_usuarios():
    if request.method == 'GET':
        filtros = {k: request.args.get(k, '').strip() for k in ('q', 'rol', 'activo')}
        lista = list()
        for u in User.listar(session['empresa_id'], **filtros):
            lista.append(dict(u))
        return respuesta(1, lista, "Lista de usuarios generada correctamente en JSON.")
    datos = datos_peticion()
    datos.pop('id', None)
    datos.setdefault('activo', 1)
    uid, mensaje = User.guardar(session['empresa_id'], session['usuario_id'], datos, session.get('superadmin', False))
    return respuesta(1, dict(id=uid), mensaje, 201)


@bp.route('/api/usuarios/<int:uid>', methods=['GET', 'PUT', 'DELETE'])
@roles_required('Administrador')
@ruta_json
def api_usuario(uid):
    emp, yo = session['empresa_id'], session['usuario_id']
    if request.method == 'DELETE':
        User.eliminar(emp, uid, yo)
        return respuesta(1, dict(id=uid), "Usuario eliminado correctamente.")
    actual = User.obtener(emp, uid)
    if not actual:
        raise UserError("El usuario no existe.", 404)
    if request.method == 'GET':
        return respuesta(1, actual, "Usuario encontrado.")
    datos = datos_peticion()
    datos['id'] = str(uid)
    if 'activo' not in datos:
        raise UserError("Indica el estado activo del usuario.")
    _, mensaje = User.guardar(emp, yo, datos, session.get('superadmin', False))
    return respuesta(1, dict(id=uid), mensaje)


@bp.route('/api/usuarios/<int:uid>/estado', methods=['PATCH'])
@roles_required('Administrador')
@ruta_json
def api_estado(uid):
    datos = datos_peticion()
    if 'activo' not in datos:
        raise UserError("Indica el estado activo del usuario.")
    activo = User.cambiar_estado(session['empresa_id'], uid, session['usuario_id'], datos['activo'], session.get('superadmin', False))
    return respuesta(1, dict(id=uid, activo=activo), "Usuario activado." if activo else "Usuario desactivado.")
