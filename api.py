# --- api.py (Refactorizado con ORM y listo para la Nube) ---

# 1. Importaciones del Servidor
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy  # <-- NUEVO
from sqlalchemy.exc import IntegrityError # <-- NUEVO
from config import DATABASE_URI # <-- NUEVO
import bcrypt
import re
import smtplib
from email.mime.text import MIMEText
import random
from datetime import date, datetime, timedelta # <-- Añadido datetime y timedelta

# --- CONFIGURACIÓN CENTRALIZADA ---

app = Flask(__name__)
# Configura la app Flask para usar la URI de la nube
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa el ORM
db = SQLAlchemy(app)

# (Credenciales de Email - se quedan igual)
EMAIL_APP_PASSWORD = "jgoh konm evtq svci"
SENDER_EMAIL = "johanfullstack09@gmail.com"

# --- MODELOS DE BASE DE DATOS (El corazón del ORM) ---
# Reemplaza tu CREATE TABLE. Ahora defines tus tablas como Clases de Python.

class User(db.Model):
    __tablename__ = 'tb_users'
    
    # Mapeo de tus columnas
    id_user = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # Guardar hashes
    name_full = db.Column(db.String(120))
    rol = db.Column(db.String(1), default='u') # 'u' = usuario, 'a' = admin
    date_creation = db.Column(db.Date, default=date.today)
    email = db.Column(db.String(120), unique=True)
    last_code = db.Column(db.String(10))
    code_expiration = db.Column(db.DateTime)

    # (Aquí puedes definir tus otras tablas: tb_hotel, tb_reservation, etc.)
    # Ejemplo:
    # class Hotel(db.Model):
    #    __tablename__ = 'tb_hotel'
    #    id_hotel = db.Column(db.Integer, primary_key=True)
    #    ...


# --- LÓGICA DE BASE DE DATOS (Reemplaza setup_database) ---

def setup_database():
    """
    Crea todas las tablas definidas en los Modelos (ej. User) 
    si no existen en la base de datos de la nube.
    """
    print("--- [API] Verificando tablas de la Base de Datos en la nube... ---")
    with app.app_context():
        db.create_all()
        
        # --- Crear usuario admin (si no existe) ---
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("--- [API] Creando usuario 'admin' por defecto... ---")
            hashed_password = bcrypt.hashpw("admin".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            
            new_admin = User(
                username='admin',
                password=hashed_password,
                name_full='Administrador',
                rol='a',
                email='admin@hotel.com' # Email de ejemplo
            )
            db.session.add(new_admin)
            db.session.commit()
            
    print("--- [API] ¡Base de Datos en la nube lista! ---")


# --- ¡get_db_connection() HA SIDO ELIMINADA! ---
# SQLAlchemy maneja las conexiones por nosotros.


# --- ENDPOINT 1: CREAR CUENTA (Refactorizado con ORM) ---
@app.route('/create_account', methods=['POST'])
def handle_create_account():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()

    # (Tus validaciones de contraseña/email se quedan igual)
    if len(password) < 8:
        return jsonify({'message': 'La contraseña debe tener al menos 8 caracteres'}), 400
    if not re.search(r"[A-Z]", password):
        return jsonify({'message': 'Debe contener al menos una letra MAYÚSCULA'}), 400
    # ... (etc)
    
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # --- Lógica de ORM (No más SQL) ---
    new_user = User(
        username=username,
        password=hashed_password,
        email=email,
        name_full=username # (Puedes pedir nombre completo o dejarlo vacío)
    )

    try:
        db.session.add(new_user)
        db.session.commit() # El ORM ejecuta el "INSERT INTO..."
        return jsonify({'message': '¡Cuenta creada exitosamente!'}), 201

    except IntegrityError as e:
        db.session.rollback() # Deshacer si hay error
        if 'tb_users_username_key' in str(e):
            return jsonify({'message': 'Error: El nombre de usuario ya existe'}), 400
        if 'tb_users_email_key' in str(e):
            return jsonify({'message': 'Error: El email ya está en uso'}), 400
        return jsonify({'message': 'Error al crear la cuenta'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error inesperado: {str(e)}'}), 500

# --- ENDPOINT 2: LOGIN (Refactorizado con ORM) ---
@app.route('/login', methods=['POST'])
def handle_login():
    data = request.json
    username = data.get('username', '').strip()
    password_attempt = data.get('password', '')

    if not username or not password_attempt:
        return jsonify({'message': 'Usuario y contraseña requeridos'}), 400

    # --- Lógica de ORM (No más SQL) ---
    # 1. Buscar al usuario
    user = User.query.filter_by(username=username).first() # Ejecuta "SELECT * ... WHERE username=... LIMIT 1"

    if not user:
        return jsonify({'message': 'Usuario o contraseña incorrectos'}), 401

    # 2. Verificar la contraseña
    if bcrypt.checkpw(password_attempt.encode("utf-8"), user.password.encode("utf-8")):
        
        # 3. Enviar datos del usuario de vuelta
        user_data = {
            'id_user': user.id_user,
            'username': user.username,
            'email': user.email,
            'name_full': user.name_full,
            'rol': user.rol
        }
        return jsonify({
            'message': 'Login exitoso',
            'user_data': user_data
        }), 200
    else:
        return jsonify({'message': 'Usuario o contraseña incorrectos'}), 401


# --- ENDPOINT 3: OBTENER PERFIL (Refactorizado con ORM) ---
@app.route('/get_profile', methods=['POST'])
def handle_get_profile():
    data = request.json
    username = data.get('username')

    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'message': 'Usuario no encontrado'}), 404
        
    user_data = {
        'email': user.email,
        'name_full': user.name_full
    }
    return jsonify({'data': user_data}), 200

# --- ENDPOINT 4: ACTUALIZAR PERFIL (Refactorizado con ORM) ---
@app.route('/update_profile', methods=['POST'])
def handle_update_profile():
    data = request.json
    username = data.get('username') # El usuario actual
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'Usuario no encontrado'}), 404

    try:
        # Actualizar campos si vienen en el JSON
        if 'name_full' in data:
            user.name_full = data['name_full'].strip()
        
        if 'email' in data:
            # (Faltaría validar el email)
            user.email = data['email'].strip()

        if 'new_password' in data and data['new_password']:
            new_pass = data['new_password']
            # (Faltaría validar la contraseña)
            user.password = bcrypt.hashpw(new_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        db.session.commit() # El ORM ejecuta el "UPDATE..."
        return jsonify({'message': 'Perfil actualizado con éxito'}), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Error: Ese email ya está en uso por otra cuenta'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error inesperado: {str(e)}'}), 500


# --- (Tus otros endpoints: send_recovery_code, verify_code, etc. se refactorizan igual) ---
# Ejemplo:
# @app.route('/send_recovery_code', methods=['POST'])
# def handle_send_recovery_code():
#     ...
#     user = User.query.filter_by(email=email).first()
#     if user:
#         ...
#         user.last_code = recovery_code
#         user.code_expiration = datetime.now() + timedelta(minutes=10)
#         db.session.commit()
#         ...


# --- Punto de entrada para correr el servidor ---
if __name__ == '__main__':
    setup_database()  # Llama a la nueva función de setup
    
    # Esta línea hace que el servidor sea visible en tu red local (para pruebas)
    # Cuando lo despliegues a un servicio como Render o Heroku, ellos
    # manejarán el host y el puerto por ti.
    app.run(host='0.0.0.0', port=5000, debug=True)
