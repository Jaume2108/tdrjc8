from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import pooling
from requests.exceptions import ConnectTimeout, RequestException
import requests, os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
print("DATABASE_URL:", os.environ.get("DATABASE_URL"))

ESP32_IP = "172.20.10.2"

# Variables temporales de sensores
dades_camps = {
    i: {
        "soil1": 0.0,
        "soil2": 0.0,
        "temp": 0.0,
        "hum": 0.0
    } for i in range(5)
}

# --- CONFIGURACIÓN BASE DE DATOS ---
mysql_url = os.getenv("DATABASE_URL")
print("DATABASE_URL:", mysql_url)

if not mysql_url:
    raise ValueError("❌ No se encontró DATABASE_URL en el entorno.")

url = urlparse(mysql_url.replace("mysql+mysqlconnector://", "mysql://"))

try:
    dbconfig = {
        "host": url.hostname,
        "user": url.username,
        "password": url.password,
        "database": url.path.lstrip("/"),
        "port": url.port or 3306,
    }

    # Pool de conexiones MySQL
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        **dbconfig
    )

    print("✅ Pool de conexiones MySQL creado correctamente.")
except mysql.connector.Error as e:
    print("❌ Error al crear el pool de conexiones:", e)

# --- FLASK APP ---
app = Flask(__name__)
app.secret_key = "Jaume"

# Obtener conexión activa del pool
def get_db_connection():
    try:
        return connection_pool.get_connection()
    except mysql.connector.Error as e:
        print("⚠️ Error al obtener conexión del pool:", e)
        return None


# ---------------------- FUNCIONES ----------------------

def mostrar_camps(userid):
    conexio = get_db_connection()
    cursor = conexio.cursor(dictionary=True, buffered=True)
    cursor.execute("""
        SELECT camps.nomcamp, camps.tamany
        FROM usuaris_camps
        JOIN camps ON usuaris_camps.camps_id = camps.camps_id
        WHERE usuaris_camps.userid = %s
    """, (userid,))
    resultats = cursor.fetchall()
    cursor.close()
    conexio.close()

    session["camps"] = [r['nomcamp'] for r in resultats][:5]
    session["tamanys"] = [r['tamany'] for r in resultats][:5]
    return redirect(url_for("pantalla_inici"))


# ---------------------- RUTAS ----------------------

@app.route("/dades_esp32")
def dades_esp32():
    camp = int(request.args.get("camp", 0))
    soil1 = request.args.get("soil1")
    soil2 = request.args.get("soil2")
    temp = request.args.get("temp")
    hum = request.args.get("hum")

    if camp not in dades_camps:
        return "Camp no vàlid", 400

    if soil1 is not None:
        dades_camps[camp]["soil1"] = float(soil1)
    if soil2 is not None:
        dades_camps[camp]["soil2"] = float(soil2)
    if temp is not None:
        dades_camps[camp]["temp"] = float(temp)
    if hum is not None:
        dades_camps[camp]["hum"] = float(hum)

    return "OK"


@app.route("/dades")
def dades():
    camp = int(request.args.get("camp", 0))
    if camp not in dades_camps:
        return jsonify({"error": "Camp no vàlid"}), 400
    
    return jsonify({
        "seccio1": {
            "humitat_sol": dades_camps[camp]["soil1"],
            "temp_ambient": dades_camps[camp]["temp"],
            "humitat_ambient": dades_camps[camp]["hum"]
        },
        "seccio2": {
            "humitat_sol": dades_camps[camp]["soil2"],
            "temp_ambient": dades_camps[camp]["temp"],
            "humitat_ambient": dades_camps[camp]["hum"]
        }
    })


@app.route("/")
def pantalla_carrega():
    return render_template("pantalla_carrega.html")


@app.route("/pantalla_inici")
def pantalla_inici():
    camps = session.get("camps", [])
    tamanys = session.get("tamanys", [])
    return render_template("pantalla_inici.html", camps=camps, tamanys=tamanys)


@app.route("/inici_sessio")
def inici_sessio():
    return render_template("inici_sessio.html")


@app.route("/registrarse")
def registrarse():
    return render_template("registrarse.html")


@app.route("/registre_editar")
def registre_editar():
    return render_template("registre_editar.html")


# ---------------------- USUARI ----------------------

@app.route("/cuadres", methods=["POST"])
def cuadres():
    nom = request.form["Nom"]
    cognom = request.form["Cognoms"]
    email = request.form["EMail"]
    contra = request.form["Contrasenya"]
    conf_contra = request.form["Confirmar contrasenya"]

    respostan = respostac = respostae = respostacontra = respostaccontra = respostacoinc = ""

    if nom == "":
        respostan = "Escriu el teu nom"
    if cognom == "":
        respostac = "Escriu els teus cognoms"
    if email == "":
        respostae = "Escriu el teu email"
    if contra == "":
        respostacontra = "Escriu la teva contrasenya"
    if conf_contra == "":
        respostaccontra = "Escriu la teva contrasenya una altra vegada"
    if contra != conf_contra and contra != "" and conf_contra != "":
        respostacoinc = "La contrasenya no coincideix"

    if not any([respostan, respostac, respostae, respostacontra, respostaccontra, respostacoinc]):
        conexio = get_db_connection()
        cursor = conexio.cursor(dictionary=True, buffered=True)
        cursor.execute("""
            INSERT INTO usuaris_app (nom, cognom, email, contrasenya)
            VALUES (%s, %s, %s, %s)
        """, (nom, cognom, email, contra))
        conexio.commit()
        cursor.close()
        conexio.close()
        flash("Usuari creat correctament!", "accio")
        return redirect("/inici_sessio")
    else:
        flash("Error, revisa les dades i torna-ho a provar.", "error")

    return render_template("registrarse.html", conf_contra=conf_contra, contra=contra, email=email, cognom=cognom, nom=nom,
                           respostan=respostan, respostac=respostac, respostae=respostae,
                           respostaccontra=respostaccontra, respostacontra=respostacontra, respostacoinc=respostacoinc)


@app.route("/inici", methods=["POST"])
def iniciar_sessio():
    iemail = request.form.get("EMail")
    icontrasenya = request.form.get("Contrasenya")
    irespostac = irespostae = ""

    if iemail == "":
        irespostae = "Escriu el teu Email"
    if icontrasenya == "":
        irespostac = "Escriu la teva contrasenya"

    if irespostac == "" and irespostae == "":
        conexio = get_db_connection()
        cursor = conexio.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM usuaris_app WHERE email = %s", (iemail,))
        usuari = cursor.fetchone()
        cursor.close()
        conexio.close()

        if usuari is None:
            return render_template("inici_sessio.html", irespostae="No existeix cap sessió amb aquest correu", iemail="", icontrasenya="")
        if usuari["contrasenya"] != icontrasenya:
            return render_template("inici_sessio.html", irespostac="Contrasenya incorrecta", iemail=iemail)

        session["user_id"] = usuari["userid"]
        session["user_email"] = usuari["email"]
        return mostrar_camps(usuari["userid"])

    return render_template("inici_sessio.html", icontrasenya=icontrasenya, iemail=iemail, irespostac=irespostac, irespostae=irespostae)


# ---------------------- CAMPS ----------------------

@app.route("/camps", methods=["POST"])
def camps():
    cnom = request.form.get("Nom")
    ctamany = request.form.get("Tamany")
    crespostan = crespostat = ""
    usuari_id = session.get("user_id")

    if not usuari_id:
        return redirect(url_for("inici_sessio"))

    if cnom == "":
        crespostan = "Escriu el Nom del camp"
    if ctamany == "":
        crespostat = "Tamany del camp en ha"
    else:
        try:
            valor = float(ctamany)
            if valor <= 0:
                crespostat = "El tamany ha de ser positiu"
        except ValueError:
            crespostat = "El tamany ha de ser un número"

    if crespostan == "" and crespostat == "":
        try:
            conexio = get_db_connection()
            cursor = conexio.cursor(dictionary=True, buffered=True)
            cursor.execute("INSERT INTO camps (nomcamp, tamany) VALUES (%s, %s)", (cnom, ctamany))
            conexio.commit()
            camps_id = cursor.lastrowid
            cursor.execute("INSERT INTO usuaris_camps (userid, camps_id) VALUES (%s, %s)", (usuari_id, camps_id))
            conexio.commit()
            cursor.close()
            conexio.close()
            flash("Camp desat correctament!", "accio")
            return mostrar_camps(usuari_id)
        except mysql.connector.IntegrityError:
            crespostan = "Ja existeix aquest nom"
    else:
        flash("Error, revisa les dades i torna-ho a provar.", "error")

    return render_template("emergent_camp.html", cnom=cnom, ctamany=ctamany, crespostan=crespostan, crespostat=crespostat)


# ---------------------- CONTROL ESP32 ----------------------

@app.route("/tancar", methods=["GET","POST"])
def tancar():
    try:
        r = requests.get(f"http://{ESP32_IP}/abrir", timeout=5)
        print(r.text)
    except (ConnectTimeout, RequestException) as e:
        print(f"⚠️ Error ESP32:", e)
    return render_template("camp0.html")


@app.route("/obrir", methods=["GET","POST"])
def obrir():
    try:
        r = requests.get(f"http://{ESP32_IP}/cerrar", timeout=5)
        print(r.text)
    except (ConnectTimeout, RequestException) as e:
        print(f"⚠️ Error ESP32:", e)
    return render_template("camp0.html")


# ---------------------- MAIN ----------------------

if __name__ == "__main__":
    from os import environ
    port = int(environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
