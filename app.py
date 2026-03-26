from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
import sys
import os
import traceback


def get_base_path_for_app():
    """
    Devuelve la ruta base de la aplicacion.
    Funciona tanto en modo desarrollo (.py) como empaquetado (.exe).
    """
    if getattr(sys, 'frozen', False):

        return os.path.dirname(sys.executable)
    else:

        return os.path.dirname(os.path.abspath(__file__))


BASE_APP_DIR = get_base_path_for_app()


app = Flask(
    __name__,
    template_folder=os.path.join(BASE_APP_DIR, 'templates'),
    static_folder=os.path.join(BASE_APP_DIR, 'static')
)


app.secret_key = '12345'


instance_path = os.path.join(BASE_APP_DIR, 'instance')
os.makedirs(instance_path, exist_ok=True)
db_path = os.path.join(instance_path, 'cartas.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


UPLOAD_FOLDER = os.path.join(BASE_APP_DIR, 'static', 'Cartas')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)


class Tipo(db.Model):
    __tablename__ = 'tipos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<Tipo {self.nombre}>'


class TipoGeneral(db.Model):
    __tablename__ = 'tipos_generales'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<TipoGeneral {self.nombre}>'


class Evolucion(db.Model):
    __tablename__ = 'evoluciones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<Evolucion {self.nombre}>'


class Expansion(db.Model):
    __tablename__ = 'expansiones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    sobres = db.relationship(
        'Sobre', backref='expansion_rel', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Expansion {self.nombre}>'


class Sobre(db.Model):
    __tablename__ = 'sobres'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    expansion_id = db.Column(db.Integer, db.ForeignKey(
        'expansiones.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint(
        'nombre', 'expansion_id', name='uq_sobre_nombre_expansion'),)

    def __repr__(self):
        return f'<Sobre {self.nombre} (ExpID: {self.expansion_id})>'


class Carta(db.Model):
    __tablename__ = 'cartas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    imagen = db.Column(db.String(100))
    cantidad = db.Column(db.Integer, default=1)
    hp = db.Column(db.String(50))
    energia = db.Column(db.String(100))

    tipo_id = db.Column(db.Integer, db.ForeignKey('tipos.id'), nullable=False)
    debilidad_id = db.Column(
        db.Integer, db.ForeignKey('tipos.id'), nullable=True)
    evolucion_id = db.Column(db.Integer, db.ForeignKey(
        'evoluciones.id'), nullable=True)
    expansion_id = db.Column(db.Integer, db.ForeignKey(
        'expansiones.id'), nullable=True)
    sobre_id = db.Column(db.Integer, db.ForeignKey(
        'sobres.id'), nullable=True)

    rareza = db.Column(db.String(50), nullable=False)
    cantidad_f2p = db.Column(db.Integer, default=0)
    ex = db.Column(db.Boolean, default=False)

    coste_retirada = db.Column(db.String(100))
    habilidad = db.Column(db.Boolean, default=False)
    tipo_general = db.Column(db.String(50), nullable=False)

    tipo = db.relationship('Tipo', foreign_keys=[tipo_id], backref=db.backref(
        'cartas_por_tipo', lazy='noload'))
    debilidad = db.relationship('Tipo', foreign_keys=[
                                debilidad_id], backref=db.backref('cartas_por_debilidad', lazy='noload'))
    evolucion = db.relationship('Evolucion', backref=db.backref(
        'cartas_con_evolucion', lazy='noload'))
    expansion = db.relationship('Expansion', backref=db.backref(
        'cartas_en_expansion', lazy='noload'))
    sobre = db.relationship('Sobre', backref=db.backref(
        'cartas_en_sobre', lazy='noload'))

    def __repr__(self):
        return f'<Carta {self.nombre}>'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def inicializar_tipos_base():
    nombres = ['Planta', 'Agua', 'Psiquico', 'Siniestro', 'Dragon', 'Fuego',
               'Electrico', 'Lucha', 'Acero', 'Normal', ]
    for nombre in nombres:
        if not Tipo.query.filter_by(nombre=nombre).first():
            db.session.add(Tipo(nombre=nombre))
    db.session.commit()


def inicializar_tipos_generales_base():
    nombres = ['Pokemon', 'Partidario', 'Herramienta', 'Objeto', 'Energia']
    for nombre in nombres:
        if not TipoGeneral.query.filter_by(nombre=nombre).first():
            db.session.add(TipoGeneral(nombre=nombre))
    db.session.commit()


def inicializar_evoluciones_base():
    nombres = ["Basico", "Fase 1", "Fase 2", ]
    for nombre in nombres:
        if not Evolucion.query.filter_by(nombre=nombre).first():
            db.session.add(Evolucion(nombre=nombre))
    db.session.commit()


def inicializar_expansiones_sobres_base():
    data = {
        "Genes Formidables": ["Misiones"],
        "La Isla Singular": ["Misiones"],
        "Pugna Espaciotemporal": ["Misiones"],
        "Luz Triunfal": ["Misiones"],
        "Festival Brillante": ["Misiones"],
        "Guardianes Celestiales": ["Misiones"],
        "Promo-A": ["Promo-A"],
    }
    for nombre_exp, nombres_sobres in data.items():
        exp_obj = Expansion.query.filter_by(nombre=nombre_exp).first()
        if not exp_obj:
            exp_obj = Expansion(nombre=nombre_exp)
            db.session.add(exp_obj)
        db.session.flush()
        for nombre_sob in nombres_sobres:
            if not Sobre.query.filter_by(nombre=nombre_sob, expansion_id=exp_obj.id).first():
                db.session.add(
                    Sobre(nombre=nombre_sob, expansion_id=exp_obj.id))
    db.session.commit()


with app.app_context():
    # Crea la carpeta de subidas si no existe
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        print(f"Carpeta de subidas creada en: {app.config['UPLOAD_FOLDER']}")

    db.create_all()
    print("Base de datos y tablas verificadas/creadas.")

    if Tipo.query.count() == 0:
        inicializar_tipos_base()
        print("Tipos base inicializados.")

    if TipoGeneral.query.count() == 0:
        inicializar_tipos_generales_base()
        print("Tipos Generales base inicializados.")

    if Evolucion.query.count() == 0:
        inicializar_evoluciones_base()
        print("Evoluciones base inicializadas.")

    if Expansion.query.count() == 0:
        inicializar_expansiones_sobres_base()
        print("Expansiones y sobres base inicializados.")


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/carta/<int:carta_id>/eliminar', methods=['POST'])
def eliminar_carta(carta_id):
    carta = db.session.get(Carta, carta_id)
    if not carta:
        flash('Carta no encontrada.', 'error')
        return redirect(url_for('home'))
    db.session.delete(carta)
    db.session.commit()
    flash('Carta eliminada correctamente', 'success')
    return redirect(url_for('home'))


@app.route('/carta/<int:carta_id>')
def ver_carta(carta_id):
    carta = db.session.query(Carta).options(
        joinedload(Carta.tipo),
        joinedload(Carta.debilidad),
        joinedload(Carta.evolucion),
        joinedload(Carta.expansion),
        joinedload(Carta.sobre)
    ).get(carta_id)
    if not carta:
        return "Carta no encontrada", 404
    return render_template('carta.html', carta=carta)


@app.route('/agregar_variacion/<int:id_carta_base>', methods=['GET', 'POST'])
def agregar_variacion(id_carta_base):
    carta_original = db.session.get(Carta, id_carta_base)
    if not carta_original:
        flash("Carta base no encontrada.", "error")
        return redirect(url_for('home'))
    if request.method == 'POST':
        nombre_nuevo = request.form.get('nombre')
        rareza = request.form.get('rareza')
        cantidad_str = request.form.get('cantidad', '0')
        cantidad_f2p_str = request.form.get('cantidad_f2p', '0')
        imagen_file = request.files.get('imagen')
        if not nombre_nuevo:
            flash("El nombre no puede estar vacio.", "error")
            return render_template('agregar_variacion.html', carta_original=carta_original)
        if not rareza:
            flash("Debe seleccionar una rareza", "error")
            return render_template('agregar_variacion.html', carta_original=carta_original)
        if not imagen_file or imagen_file.filename == '':
            flash("Debe subir una imagen", "error")
            return render_template('agregar_variacion.html', carta_original=carta_original)
        if not allowed_file(imagen_file.filename):
            flash("Tipo de archivo de imagen no permitido.", "error")
            return render_template('agregar_variacion.html', carta_original=carta_original)
        try:
            cantidad = int(cantidad_str)
            cantidad_f2p = int(cantidad_f2p_str)
        except ValueError:
            flash("Cantidad y Cantidad F2P deben ser numeros.", "error")
            return render_template('agregar_variacion.html', carta_original=carta_original)
        filename = secure_filename(imagen_file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        imagen_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        nueva_variacion = Carta(
            nombre=nombre_nuevo,
            hp=carta_original.hp, energia=carta_original.energia,
            tipo_id=carta_original.tipo_id, debilidad_id=carta_original.debilidad_id,
            evolucion_id=carta_original.evolucion_id, expansion_id=carta_original.expansion_id,
            sobre_id=carta_original.sobre_id, coste_retirada=carta_original.coste_retirada,
            ex=carta_original.ex, habilidad=carta_original.habilidad, tipo_general=carta_original.tipo_general,
            rareza=rareza, imagen=filename, cantidad=cantidad, cantidad_f2p=cantidad_f2p
        )
        db.session.add(nueva_variacion)
        db.session.commit()
        flash("Variacion agregada correctamente", "success")
        return redirect(url_for('home'))
    return render_template('agregar_variacion.html', carta_original=carta_original)


@app.route('/modificar_cantidad/<int:carta_id>', methods=['POST'])
def modificar_cantidad(carta_id):
    carta = db.session.get(Carta, carta_id)
    if not carta:
        return jsonify(success=False, error="Carta no encontrada"), 404
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="No se recibieron datos JSON"), 400
    delta = data.get('delta')
    if delta is None:
        return jsonify(success=False, error="Parametro 'delta' no encontrado"), 400
    try:
        delta = int(delta)
    except ValueError:
        return jsonify(success=False, error="'delta' debe ser un numero entero"), 400
    nueva_cantidad = carta.cantidad + delta
    if nueva_cantidad < 0:
        nueva_cantidad = 0
    carta.cantidad = nueva_cantidad
    try:
        db.session.commit()
        return jsonify(success=True, nueva_cantidad=nueva_cantidad)
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify(success=False, error="Error al guardar"), 500


# --- RUTAS DE ADMINISTRACION ---
@app.route('/admin')
def admin_home(): return render_template('admin_home.html')


@app.route('/admin/tipos')
def admin_gestionar_tipos():
    tipos = Tipo.query.order_by(Tipo.nombre).all()
    return render_template('admin_gestionar_tipos.html', tipos=tipos)


@app.route('/admin/tipos_generales')
def admin_gestionar_tipos_generales():
    tipos_generales = TipoGeneral.query.order_by(TipoGeneral.nombre).all()
    return render_template('admin_gestionar_tipos_generales.html', tipos_generales=tipos_generales)


@app.route('/admin/evoluciones')
def admin_gestionar_evoluciones():
    evoluciones = Evolucion.query.order_by(Evolucion.nombre).all()
    return render_template('admin_gestionar_evoluciones.html', evoluciones=evoluciones)


@app.route('/admin/expansiones')
def admin_gestionar_expansiones():
    expansiones = Expansion.query.order_by(Expansion.nombre).all()
    return render_template('admin_gestionar_expansiones.html', expansiones=expansiones)


@app.route('/admin/expansiones/<int:expansion_id>/sobres')
def admin_gestionar_sobres(expansion_id):
    expansion = db.session.get(Expansion, expansion_id)
    if not expansion:
        flash("Expansion no encontrada", "error")
        return redirect(url_for('admin_gestionar_expansiones'))
    return render_template('admin_gestionar_sobres.html', expansion=expansion)


# --- APIs ---
@app.route('/api/cartas_para_index')
def api_get_todas_las_cartas_para_index():
    try:
        cartas_db = db.session.query(Carta).options(
            joinedload(Carta.tipo), joinedload(Carta.debilidad),
            joinedload(Carta.evolucion), joinedload(Carta.expansion),
            joinedload(Carta.sobre)
        ).order_by(Carta.nombre).all()
        cartas_list = [{
            'id': c.id, 'nombre': c.nombre, 'hp': c.hp, 'energia': c.energia,
            'tipo_id': c.tipo_id, 'tipo_nombre': c.tipo.nombre if c.tipo else None,
            'debilidad_id': c.debilidad_id, 'debilidad_nombre': c.debilidad.nombre if c.debilidad else None,
            'evolucion_id': c.evolucion_id, 'evolucion_nombre': c.evolucion.nombre if c.evolucion else None,
            'expansion_id': c.expansion_id, 'expansion_nombre': c.expansion.nombre if c.expansion else None,
            'sobre_id': c.sobre_id, 'sobre_nombre': c.sobre.nombre if c.sobre else None,
            'coste_retirada': c.coste_retirada, 'rareza': c.rareza,
            'cantidad_f2p': c.cantidad_f2p, 'cantidad': c.cantidad,
            'ex': bool(c.ex), 'habilidad': bool(c.habilidad), 'tipo_general': c.tipo_general,
            'imagen_url': url_for('static', filename=f'Cartas/{c.imagen}') if c.imagen else url_for('static', filename='imagenes/pokeball.svg')
        } for c in cartas_db]
        return jsonify(cartas_list)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Error interno', 'details': str(e)}), 500


@app.route('/api/tipos', methods=['GET'])
def api_get_tipos():
    try:
        return jsonify([{"id": t.id, "nombre": t.nombre} for t in Tipo.query.order_by(Tipo.nombre).all()])
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/tipos/nuevo', methods=['POST'])
def api_agregar_tipo():
    data = request.get_json()
    nombre = data.get('nombre', '').strip() if data else ''
    if not nombre:
        return jsonify({"error": "Nombre requerido."}), 400
    if Tipo.query.filter_by(nombre=nombre).first():
        return jsonify({"error": "Tipo ya existe."}), 409
    try:
        nuevo = Tipo(nombre=nombre)
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"id": nuevo.id, "nombre": nuevo.nombre, "message": "Tipo agregado."}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/tipos/eliminar/<int:tipo_id>', methods=['DELETE'])
def api_eliminar_tipo(tipo_id):
    item = db.session.get(Tipo, tipo_id)
    if not item:
        return jsonify({"error": "No encontrado."}), 404
    if Carta.query.filter((Carta.tipo_id == tipo_id) | (Carta.debilidad_id == tipo_id)).first():
        return jsonify({"error": "En uso. No se puede eliminar."}), 400
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Eliminado."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/tipos_generales', methods=['GET'])
def api_get_tipos_generales():
    try:
        tipos_gen_db = TipoGeneral.query.order_by(TipoGeneral.nombre).all()
        return jsonify([{"id": tg.id, "nombre": tg.nombre} for tg in tipos_gen_db])
    except Exception as e:
        print(f"Error en api_get_tipos_generales: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/tipos_generales/nuevo', methods=['POST'])
def api_agregar_tipo_general():
    data = request.get_json()
    nombre = data.get('nombre', '').strip() if data else ''
    if not nombre:
        return jsonify({"error": "Nombre requerido."}), 400
    if TipoGeneral.query.filter_by(nombre=nombre).first():
        return jsonify({"error": "Tipo General ya existe."}), 409
    try:
        nuevo_tg = TipoGeneral(nombre=nombre)
        db.session.add(nuevo_tg)
        db.session.commit()
        return jsonify({"id": nuevo_tg.id, "nombre": nuevo_tg.nombre, "message": "Tipo General agregado."}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/tipos_generales/eliminar/<int:tipo_general_id>', methods=['DELETE'])
def api_eliminar_tipo_general(tipo_general_id):
    item = db.session.get(TipoGeneral, tipo_general_id)
    if not item:
        return jsonify({"error": "No encontrado."}), 404
    if Carta.query.filter_by(tipo_general=item.nombre).first():
        return jsonify({"error": "En uso. No se puede eliminar."}), 400
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Eliminado."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/evoluciones', methods=['GET'])
def api_get_evoluciones():
    try:
        return jsonify([{"id": ev.id, "nombre": ev.nombre} for ev in Evolucion.query.order_by(Evolucion.nombre).all()])
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/evoluciones/nuevo', methods=['POST'])
def api_agregar_evolucion():
    data = request.get_json()
    nombre = data.get('nombre', '').strip() if data else ''
    if not nombre:
        return jsonify({"error": "Nombre requerido."}), 400
    if Evolucion.query.filter_by(nombre=nombre).first():
        return jsonify({"error": "Evolucion ya existe."}), 409
    try:
        nuevo = Evolucion(nombre=nombre)
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"id": nuevo.id, "nombre": nuevo.nombre, "message": "Evolucion agregada."}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/evoluciones/eliminar/<int:evolucion_id>', methods=['DELETE'])
def api_eliminar_evolucion(evolucion_id):
    item = db.session.get(Evolucion, evolucion_id)
    if not item:
        return jsonify({"error": "No encontrado."}), 404
    if Carta.query.filter_by(evolucion_id=evolucion_id).first():
        return jsonify({"error": "En uso."}), 400
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Eliminado."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/expansiones', methods=['GET'])
def api_get_expansiones():
    try:
        return jsonify([{"id": ex.id, "nombre": ex.nombre} for ex in Expansion.query.order_by(Expansion.nombre).all()])
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/expansiones/nuevo', methods=['POST'])
def api_agregar_expansion():
    data = request.get_json()
    nombre = data.get('nombre', '').strip() if data else ''
    if not nombre:
        return jsonify({"error": "Nombre requerido."}), 400
    if Expansion.query.filter_by(nombre=nombre).first():
        return jsonify({"error": "Expansion ya existe."}), 409
    try:
        nuevo = Expansion(nombre=nombre)
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"id": nuevo.id, "nombre": nuevo.nombre, "message": "Expansion agregada."}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/expansiones/eliminar/<int:expansion_id>', methods=['DELETE'])
def api_eliminar_expansion(expansion_id):
    item = db.session.get(Expansion, expansion_id)
    if not item:
        return jsonify({"error": "No encontrado."}), 404
    if Carta.query.filter_by(expansion_id=expansion_id).first():
        return jsonify({"error": "En uso."}), 400
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Expansion y sobres eliminados."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/expansiones/<int:expansion_id>/sobres', methods=['GET'])
def api_get_sobres_por_expansion(expansion_id):
    expansion = db.session.get(Expansion, expansion_id)
    if not expansion:
        return jsonify({"error": "Expansion no encontrada"}), 404
    try:
        sobres_db = Sobre.query.filter_by(
            expansion_id=expansion_id).order_by(Sobre.nombre).all()
        return jsonify([{"id": s.id, "nombre": s.nombre} for s in sobres_db])
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/sobres/nuevo', methods=['POST'])
def api_agregar_sobre():
    data = request.get_json()
    if not data or 'nombre' not in data or 'expansion_id' not in data:
        return jsonify({"error": "Datos invalidos."}), 400
    nombre = data.get('nombre', '').strip()
    expansion_id_str = data.get('expansion_id')
    if not nombre or expansion_id_str is None:
        return jsonify({"error": "Nombre y ID expansion requeridos."}), 400
    try:
        expansion_id = int(expansion_id_str)
    except ValueError:
        return jsonify({"error": "ID expansion debe ser numero."}), 400
    if not db.session.get(Expansion, expansion_id):
        return jsonify({"error": "Expansion no encontrada."}), 404
    if Sobre.query.filter_by(nombre=nombre, expansion_id=expansion_id).first():
        return jsonify({"error": "Sobre ya existe."}), 409
    try:
        nuevo = Sobre(nombre=nombre, expansion_id=expansion_id)
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"id": nuevo.id, "nombre": nuevo.nombre, "expansion_id": nuevo.expansion_id, "message": "Sobre agregado."}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/sobres/eliminar/<int:sobre_id>', methods=['DELETE'])
def api_eliminar_sobre(sobre_id):
    item = db.session.get(Sobre, sobre_id)
    if not item:
        return jsonify({"error": "No encontrado."}), 404
    if Carta.query.filter_by(sobre_id=sobre_id).first():
        return jsonify({"error": "En uso."}), 400
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Eliminado."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# --- RUTA AGREGAR CARTA ---
@app.route('/agregar', methods=['GET', 'POST'])
def agregar_carta_route():
    tipos_db = Tipo.query.order_by(Tipo.nombre).all()
    evoluciones_db = Evolucion.query.order_by(Evolucion.nombre).all()
    expansiones_db = Expansion.query.order_by(Expansion.nombre).all()
    tipos_generales_db = TipoGeneral.query.order_by(TipoGeneral.nombre).all()

    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            hp = request.form.get('hp', '').strip()
            energia = request.form.get('energia', '').strip()
            coste_retirada = request.form.get('coste_retirada')
            rareza = request.form.get('rareza')
            tipo_id_str = request.form.get('tipo')
            tipo_general_id_str = request.form.get('tipo_general')

            errores = []
            if not nombre:
                errores.append("Nombre es obligatorio.")
            if not hp:
                errores.append("HP es obligatorio.")
            if not energia:
                errores.append("Energia es obligatoria.")
            if not coste_retirada:
                errores.append("Coste de retirada es obligatorio.")
            if not rareza:
                errores.append("Rareza es obligatoria.")
            if not tipo_id_str:
                errores.append("Tipo es obligatorio.")
            if not tipo_general_id_str:
                errores.append("Tipo de Carta es obligatorio.")

            if 'imagen' not in request.files or request.files['imagen'].filename == '':
                errores.append("La imagen de la carta es obligatoria.")
            else:
                imagen_file = request.files['imagen']
                if not allowed_file(imagen_file.filename):
                    errores.append("Tipo de archivo de imagen no permitido.")

            tipo_general_nombre = None
            if tipo_general_id_str and tipo_general_id_str.isdigit():
                tipo_general_obj = db.session.get(
                    TipoGeneral, int(tipo_general_id_str))
                if tipo_general_obj:
                    tipo_general_nombre = tipo_general_obj.nombre
                else:
                    errores.append(
                        f"Tipo de Carta seleccionado invalido (ID: {tipo_general_id_str}).")
            elif tipo_general_id_str:
                errores.append("Tipo de Carta seleccionado es invalido.")

            if errores:
                for error in errores:
                    flash(error, "error")
                return render_template('agregar.html',
                                       tipos=tipos_db,
                                       evoluciones=evoluciones_db,
                                       expansiones=expansiones_db,
                                       tipos_generales_db=tipos_generales_db,
                                       carta_data=request.form)

            cantidad_str = request.form.get('cantidad', '1')
            cantidad_f2p_str = request.form.get('cantidad_f2p', '0')

            try:
                cantidad = int(cantidad_str)
                cantidad_f2p = int(cantidad_f2p_str)
                tipo_id = int(tipo_id_str)
            except ValueError:
                flash(
                    "Cantidad, Cantidad F2P y Tipo ID deben ser numeros validos.", "error")
                return render_template('agregar.html', tipos=tipos_db, evoluciones=evoluciones_db,
                                       expansiones=expansiones_db, tipos_generales_db=tipos_generales_db,
                                       carta_data=request.form)

            ex = True if request.form.get('ex') == 'on' else False
            habilidad = True if request.form.get(
                'habilidad') == 'on' else False

            debilidad_id_str = request.form.get('debilidad')
            evolucion_id_str = request.form.get('evolucion')
            expansion_id_str = request.form.get('expansion')
            sobre_id_str = request.form.get('sobre')

            debilidad_id = int(
                debilidad_id_str) if debilidad_id_str and debilidad_id_str.isdigit() else None
            evolucion_id = int(
                evolucion_id_str) if evolucion_id_str and evolucion_id_str.isdigit() else None
            expansion_id = int(
                expansion_id_str) if expansion_id_str and expansion_id_str.isdigit() else None
            sobre_id = int(
                sobre_id_str) if sobre_id_str and sobre_id_str.isdigit() else None

            imagen_file = request.files['imagen']
            nombre_archivo_seguro = secure_filename(imagen_file.filename)
            nombre_archivo_db = nombre_archivo_seguro
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            ruta_guardado = os.path.join(
                app.config['UPLOAD_FOLDER'], nombre_archivo_db)
            imagen_file.save(ruta_guardado)

            nueva_carta = Carta(
                nombre=nombre, hp=hp, energia=energia, coste_retirada=coste_retirada,
                cantidad=cantidad, rareza=rareza, cantidad_f2p=cantidad_f2p,
                ex=ex, habilidad=habilidad,
                tipo_general=tipo_general_nombre,
                tipo_id=tipo_id, debilidad_id=debilidad_id, evolucion_id=evolucion_id,
                expansion_id=expansion_id, sobre_id=sobre_id, imagen=nombre_archivo_db
            )
            db.session.add(nueva_carta)
            db.session.commit()
            flash(f"Agregaste a  '{nombre}' correctamente", "success")
            return render_template('agregar.html',
                                   tipos=tipos_db,
                                   evoluciones=evoluciones_db,
                                   expansiones=expansiones_db,
                                   tipos_generales_db=tipos_generales_db,
                                   carta_data={})
        except Exception as e:
            db.session.rollback()
            print(f"Error al agregar la carta: {e}")
            traceback.print_exc()
            flash(f"Error general al agregar la carta: {str(e)}", "error")
            return render_template('agregar.html',
                                   tipos=tipos_db,
                                   evoluciones=evoluciones_db,
                                   expansiones=expansiones_db,
                                   tipos_generales_db=tipos_generales_db,
                                   carta_data=request.form)

    return render_template('agregar.html',
                           tipos=tipos_db,
                           evoluciones=evoluciones_db,
                           expansiones=expansiones_db,
                           tipos_generales_db=tipos_generales_db,
                           carta_data={})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
