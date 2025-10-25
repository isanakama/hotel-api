from flask import Flask, request, jsonify
import psycopg2, bcrypt

app = Flask(__name__)

# ⚙️ Configura con tus datos reales de Render (verás cómo obtenerlos en el paso 3)
DB_CONFIG = {
    'user': 'Admin',
    'password': 'admin',
    'host': 'localhost',
    'port': '5432',
    'dbname': 'bd_reservations'
}

@app.route("/")
def home():
    return jsonify({"ok": True, "msg": "API funcionando correctamente"})


@app.route("/init_db", methods=["POST"])
def init_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.tb_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(100) NOT NULL,
                name_full VARCHAR(100),
                email VARCHAR(100),
                rol CHAR(1),
                date_creation DATE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.tb_reservation (
                id_reservation SERIAL PRIMARY KEY,
                id_customer INTEGER NOT NULL REFERENCES public.tb_users(id),
                date_in DATE,
                date_out DATE,
                date_reservation DATE,
                num_customers INTEGER,
                total_cost MONEY,
                status VARCHAR(30)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.tb_payments (
                id_payment SERIAL PRIMARY KEY,
                id_reservation INTEGER NOT NULL REFERENCES public.tb_reservation(id_reservation),
                payment MONEY,
                date_payment DATE,
                status_payment VARCHAR(25)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.tb_hotels (
                id_hotel SERIAL PRIMARY KEY,
                id_photo INTEGER NOT NULL,
                id_service INTEGER NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.tb_comments (
                id_opinion SERIAL PRIMARY KEY,
                rank INTEGER,
                comment VARCHAR(250),
                date_post DATE,
                id_reservation INTEGER REFERENCES public.tb_reservation(id_reservation)
            );
        """)

        # Crear usuario admin
        hashed_password = bcrypt.hashpw("admin".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute("""
            INSERT INTO public.tb_users (username, password, name_full, rol, date_creation)
            VALUES (%s, %s, %s, %s, CURRENT_DATE)
            ON CONFLICT (username) DO NOTHING;
        """, ('admin', hashed_password, 'Administrador', 'a'))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"ok": True, "msg": "Base creada correctamente"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM public.tb_users WHERE username=%s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row and bcrypt.checkpw(password.encode(), row[0].encode()):
        return jsonify({"ok": True, "msg": "Login correcto"})
    else:
        return jsonify({"ok": False, "msg": "Usuario o contraseña incorrectos"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
