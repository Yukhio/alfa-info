# app.py
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
import os
import json
from uuid import uuid4
from datetime import datetime, date

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
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.route('/')
def vista_cliente():
    catalogo = cargar_catalogo()
    visibles = [p for p in catalogo if p.get('visible', False)]
    visibles.sort(key=lambda p: dias_para_cumple(datetime.strptime(p['fecha_nacimiento'], '%Y-%m-%d').date()))
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
            'fotos_previas': [filename],
            'visible': True
        }

        personas = cargar_catalogo()
        personas.append(nueva_persona)
        guardar_catalogo(personas)
        flash('Persona registrada exitosamente.', 'success')
        return redirect(url_for('vista_vendedor'))

    personas = cargar_catalogo()
    return render_template('vendedor.html', personas=personas)


@app.route('/editar/<persona_id>', methods=['POST'])
def editar_persona(persona_id):
    if 'vendedor' not in session:
        return redirect(url_for('login'))

    personas = cargar_catalogo()
    for p in personas:
        if p['id'] == persona_id:
            p['nombre'] = request.form['nombre']
            p['fecha_nacimiento'] = request.form['fecha_nacimiento']
            p['sexo'] = request.form['sexo']
            p['puesto'] = request.form['puesto']
            p['correo'] = request.form['correo']
            p['telefono'] = request.form['telefono']

            nueva_foto = request.files.get('nueva_foto')
            if nueva_foto and nueva_foto.filename:
                filename = f"{uuid4().hex}_{nueva_foto.filename}"
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                nueva_foto.save(foto_path)
                # Guardar historial de fotos previas
                if 'fotos_previas' not in p:
                    p['fotos_previas'] = []
                if p['foto'] not in p['fotos_previas']:
                    p['fotos_previas'].append(p['foto'])
                p['foto'] = filename

            foto_elegida = request.form.get('foto_historial')
            if foto_elegida:
                p['foto'] = foto_elegida

            break

    guardar_catalogo(personas)
    flash('Datos editados correctamente.', 'success')
    return redirect(url_for('vista_vendedor'))


@app.route('/eliminar/<persona_id>', methods=['POST'])
def eliminar_persona(persona_id):
    if 'vendedor' not in session:
        return redirect(url_for('login'))

    personas = cargar_catalogo()
    personas = [p for p in personas if p['id'] != persona_id]
    guardar_catalogo(personas)
    flash('Usuario eliminado correctamente.', 'success')
    return redirect(url_for('vista_vendedor'))

@app.route('/eliminar_foto_historial/<persona_id>/<foto_nombre>', methods=['POST'])
def eliminar_foto_historial(persona_id, foto_nombre):
    if 'vendedor' not in session:
        return redirect(url_for('login'))

    personas = cargar_catalogo()
    for p in personas:
        if p['id'] == persona_id:
            if 'fotos_previas' in p and foto_nombre in p['fotos_previas']:
                p['fotos_previas'].remove(foto_nombre)
                # Si también es la foto activa, borra del campo principal
                if p.get('foto') == foto_nombre:
                    p['foto'] = ''
            break

    guardar_catalogo(personas)
    flash('Foto eliminada del historial.', 'success')
    return redirect(url_for('vista_vendedor'))

def dias_para_cumple(fecha_nac):
    hoy = date.today()
    cumple = fecha_nac.replace(year=hoy.year)
    if cumple < hoy:
        cumple = cumple.replace(year=hoy.year + 1)
    return (cumple - hoy).days

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('data', exist_ok=True)
    app.run(debug=True)
