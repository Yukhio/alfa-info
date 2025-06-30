# app.py
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
import os
import json
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.secret_key = 'super_secret_key'

CATALOGO_PATH = 'data/catalogo.json'
USUARIO = 'hcryztel'
CLAVE = '123'

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.template_filter('todatetime')
def to_datetime_filter(value):
    return datetime.strptime(value, "%Y-%m-%d")

@app.context_processor
def inject_now():
    return {'now': datetime.now}

def cargar_catalogo():
    if not os.path.exists(CATALOGO_PATH):
        return []
    try:
        with open(CATALOGO_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def guardar_catalogo(data):
    with open(CATALOGO_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def vista_cliente():
    catalogo = cargar_catalogo()
    visibles = [p for p in catalogo if p.get('visible', False)]

    # Ordenar alfabéticamente por nombre (sin importar mayúsculas/minúsculas)
    visibles.sort(key=lambda p: p['nombre'].lower())

    return render_template('cliente.html', personas=visibles)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']
        if usuario == USUARIO and clave == CLAVE:
            session['vendedor'] = True
            return redirect(url_for('vista_vendedor'))
        else:
            return render_template('login.html', error='Credenciales inválidas')
    mensaje = 'Debes iniciar sesión primero' if request.args.get('next') else None
    return render_template('login.html', error=mensaje)

@app.route('/logout')
def logout():
    session.pop('vendedor', None)
    return redirect(url_for('vista_cliente'))

@app.route('/vendedor', methods=['GET', 'POST'])
def vista_vendedor():
    if 'vendedor' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.form
        foto = request.files['foto']
        filename = f"{uuid4().hex}_{foto.filename}"
        foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        foto.save(foto_path)

        nueva_persona = {
            'id': uuid4().hex,
            'nombre': data['nombre'],
            'fecha_nacimiento': data['fecha_nacimiento'],
            'sexo': data['sexo'],
            'puesto': data['puesto'],
            'telefono': data['telefono'],
            'correo': data['correo'],
            'foto': filename,
            'visible': True
        }

        personas = cargar_catalogo()
        personas.append(nueva_persona)
        guardar_catalogo(personas)
        return redirect(url_for('vista_vendedor'))

    personas = cargar_catalogo()
    return render_template('vendedor.html', personas=personas)


@app.route('/ocultar/<producto_id>')
def ocultar_producto(producto_id):
    if 'vendedor' not in session or session['vendedor'] != True:
        return redirect(url_for('login'))

    catalogo = cargar_catalogo()
    for producto in catalogo:
        if producto['id'] == producto_id:
            producto['visible'] = False
            break
    guardar_catalogo(catalogo)
    return redirect(url_for('vista_vendedor'))

@app.route('/mostrar/<producto_id>')
def mostrar_producto(producto_id):
    if 'vendedor' not in session or session['vendedor'] != True:
        return redirect(url_for('login'))

    catalogo = cargar_catalogo()
    for producto in catalogo:
        if producto['id'] == producto_id:
            producto['visible'] = True
            break
    guardar_catalogo(catalogo)
    return redirect(url_for('vista_vendedor'))

@app.route('/editar/<producto_id>', methods=['POST'])
def editar_producto(producto_id):
    if 'vendedor' not in session or session['vendedor'] != True:
        return redirect(url_for('login'))

    catalogo = cargar_catalogo()
    for producto in catalogo:
        if producto['id'] == producto_id:
            producto['precio'] = float(request.form['precio'])
            producto['stock'] = int(request.form['stock'])
            break
    guardar_catalogo(catalogo)
    return redirect(url_for('vista_vendedor'))

@app.route('/toggle_visibilidad/<producto_id>', methods=['POST'])
def toggle_visibilidad(producto_id):
    if 'vendedor' not in session or session['vendedor'] != True:
        return redirect(url_for('login'))

    catalogo = cargar_catalogo()
    for producto in catalogo:
        if producto['id'] == producto_id:
            producto['visible'] = not producto['visible']
            break
    guardar_catalogo(catalogo)
    return redirect(url_for('vista_vendedor'))


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('data', exist_ok=True)
    app.run(debug=True)
