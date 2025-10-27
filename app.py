from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from requests.exceptions import ConnectTimeout, RequestException
import requests, os
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()
print("DATABASE_URL:", os.environ.get("DATABASE_URL"))

ESP32_IP = "172.20.10.2"

dades_camps = {
    i: {
        "soil1": 0.0,   # humitat sòl secció 1
        "soil2": 0.0,   # humitat sòl secció 2
        "temp": 0.0,
        "hum": 0.0
    } for i in range(5)
}

mysql_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
url = urlparse(mysql_url.replace("mysql+mysqlconnector://", "mysql://"))

try:
    conexio = mysql.connector.connect(
        host=url.hostname,
        user=url.username,
        password=url.password,
        database=url.path.lstrip("/"),
        port=url.port or 3306
    )
    print("✅ Conexión a MySQL establecida correctamente.")
except mysql.connector.Error as e:
    print("❌ Error al conectar con MySQL:", e)

app=Flask(__name__)
app.secret_key="Jaume"

#definicions

def mostrar_camps(userid):
    cursor = conexio.cursor(dictionary=True, buffered=True)
    cursor.execute("""
        SELECT camps.nomcamp, camps.tamany
        FROM usuaris_camps
        JOIN camps ON usuaris_camps.camps_id = camps.camps_id
        WHERE usuaris_camps.userid = %s
    """, (userid,))
    resultats = cursor.fetchall()
    cursor.close()

    session["camps"]   = [r['nomcamp'] for r in resultats][:5]
    session["tamanys"] = [r['tamany'] for r in resultats][:5]


    return redirect(url_for("pantalla_inici"))

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
    tamanys = session.get("tamanys",[])
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

@app.route("/camp0")
def camp0():
    camps = session.get("camps", [])
    nom_camp = camps[0] if len(camps) > 0 else "Camp 0"
    return render_template("camp0.html", nom_camp=nom_camp)

@app.route("/camp1")
def camp1():
    camps = session.get("camps", [])
    nom_camp = camps[1] if len(camps) > 1 else "Camp 1"
    return render_template("camp1.html", nom_camp=nom_camp)

@app.route("/camp2")
def camp2():
    camps = session.get("camps", [])
    nom_camp = camps[2] if len(camps) > 2 else "Camp 2"
    return render_template("camp2.html", nom_camp=nom_camp)

@app.route("/camp3")
def camp3():
    camps = session.get("camps", [])
    nom_camp = camps[3] if len(camps) > 3 else "Camp 3"
    return render_template("camp3.html", nom_camp=nom_camp)

@app.route("/camp4")
def camp4():
    camps = session.get("camps", [])
    nom_camp = camps[4] if len(camps) > 4 else "Camp 4"
    return render_template("camp4.html", nom_camp=nom_camp)


@app.route("/afegir")
def afegir():
    return render_template("afegir_camp.html")

@app.route("/emergent")
def emergent():
    return render_template("emergent_camp.html")

@app.route("/editable")
def editable(): 
    camps = session.get("camps", [])
    return render_template("editable.html", camps=camps)

@app.route("/emergent_editable", methods=["POST"])
def emergent_editable():
    camp_seleccionat = request.form.get("camp")
    session["camp_seleccionat"] = camp_seleccionat
    return render_template("emergent_editable.html")

@app.route("/camp0", methods=["POST"])
def nomcamp():
    camp_seleccionat2 = request.form.get("camp")
    session["camp_seleccionat2"] = camp_seleccionat2
    return render_template("camp0.html")

@app.route("/eliminar_compte", methods=["POST"])
def eliminar_compte():
    usuari_id = session.get("user_id")
    cursor = conexio.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT camps_id FROM usuaris_camps WHERE userid = %s
    """, (usuari_id,))
    camps_ids = [row["camps_id"] for row in cursor.fetchall()]

    cursor.execute("DELETE FROM usuaris_camps WHERE userid = %s", (usuari_id,))
    if camps_ids:
        cursor.execute(
            "DELETE FROM camps WHERE camps_id IN (%s)" % 
            ",".join(["%s"] * len(camps_ids)), tuple(camps_ids)
        )
    cursor.execute("DELETE FROM usuaris_app WHERE userid = %s", (usuari_id,))

    conexio.commit()
    cursor.close()
    session.clear()
    flash("Compte eliminat correctament.", "accio")


    return redirect(url_for("inici_sessio"))


@app.route("/eliminar_camp", methods=["POST"])
def eliminar_camp():
    nom_camp = session.get("camp_seleccionat")
    usuari_id = session.get("user_id")
    if not usuari_id or not nom_camp:
        return redirect(url_for("inici_sessio"))
    try:
        cursor = conexio.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT camps_id FROM camps WHERE nomcamp = %s", (nom_camp,))
        camp = cursor.fetchone()

        if camp:
            camps_id = camp["camps_id"]
            cursor.execute("DELETE FROM usuaris_camps WHERE userid = %s AND camps_id = %s", (usuari_id, camps_id))
            cursor.execute("DELETE FROM camps WHERE camps_id = %s", (camps_id,))
            conexio.commit()
            flash("Camp eliminat correctament!", "accio")
        else:
            flash("No s’ha trobat el camp", "error")

        cursor.close()
    except Exception as e:
        flash("Error en eliminar el camp", "error")
        print("Error:", e)

    return mostrar_camps(usuari_id)

@app.route("/cuadres", methods=["POST"])
def cuadres():
    nom=request.form["Nom"]
    cognom=request.form["Cognoms"]
    email=request.form["EMail"]
    contra=request.form["Contrasenya"]
    conf_contra=request.form["Confirmar contrasenya"]
    respostan=""
    respostac=""
    respostae=""
    respostacontra=""
    respostaccontra=""
    respostacoinc=""

    if nom=="":
        respostan="Escriu el teu nom"
    if cognom=="":
        respostac="Escriu els teus cognoms"
    if email=="":
        respostae="Escriu el teu email"
    if contra=="":
        respostacontra="Escriu la teva contrasenya"
    if conf_contra=="":
        respostaccontra="Escriu la teva contrasenya una altra vegada"
    if contra!="" and conf_contra!="" and contra!=conf_contra:
        contra=""
        conf_contra=""
        respostacoinc="La contrasenya no coincideix"

    if respostan=="" and respostac=="" and respostae=="" and respostacontra=="" and respostaccontra=="" and respostacoinc=="":
        cursor=conexio.cursor(dictionary=True, buffered=True)
        cursor.execute("""
            INSERT INTO usuaris_app (nom, cognom, email, contrasenya) 
            VALUES (%s, %s, %s, %s)
        """, (nom, cognom, email, contra))
        conexio.commit()
        cursor.close()
        flash("Usuari creat correctament!", "accio")
        return redirect("/inici_sessio")
    else:
        flash("Error, revisa les dades i torna-ho a provar.", "error")

    return render_template("registrarse.html", conf_contra=conf_contra, contra=contra, email=email, cognom=cognom, nom=nom, respostan=respostan, respostac=respostac, respostae=respostae, respostaccontra=respostaccontra, respostacontra=respostacontra, respostacoinc=respostacoinc)

@app.route("/cuadres_edit", methods=["POST"])
def cuadres_edit():
    nom=request.form["Nom"]
    cognom=request.form["Cognoms"]
    email=request.form["EMail"]
    contra=request.form["Contrasenya"]
    conf_contra=request.form["Confirmar contrasenya"]
    respostan=""
    respostac=""
    respostae=""
    respostacontra=""
    respostaccontra=""
    respostacoinc=""

    if nom=="":
        respostan="Escriu el nom"
    if cognom=="":
        respostac="Escriu els cognoms"
    if email=="":
        respostae="Escriu el email"
    if contra=="":
        respostacontra="Escriu la contrasenya"
    if conf_contra=="":
        respostaccontra="Escriu la contrasenya una altra vegada"
    if contra!="" and conf_contra!="" and contra!=conf_contra:
        contra=""
        conf_contra=""
        respostacoinc="La contrasenya no coincideix"

    if respostan=="" and respostac=="" and respostae=="" and respostacontra=="" and respostaccontra=="" and respostacoinc=="":
        cursor=conexio.cursor(dictionary=True, buffered=True)
        usuari_id = session.get("user_id")
        if not usuari_id:
            return redirect(url_for("inici_sessio"))
        noves_dades=[nom, cognom, email, contra, usuari_id]
        if conexio.is_connected():
            cursor = conexio.cursor()

        cursor.execute("""
            UPDATE usuaris_app 
            SET nom = %s, cognom = %s, email = %s, contrasenya = %s
            WHERE userid = %s
        """, noves_dades)

        if cursor.rowcount == 1:
            conexio.commit()

        else:
            conexio.rollback()


        cursor.close()
        conexio.close()
        flash("Les noves dades s'han desades correctament!", "accio")
        return redirect("/pantalla_inici")
    else:
        flash("Error, revisa les dades i torna-ho a provar.", "error")

    return render_template("registre_editar.html", conf_contra=conf_contra, contra=contra, email=email, cognom=cognom, nom=nom, respostan=respostan, respostac=respostac, respostae=respostae, respostaccontra=respostaccontra, respostacontra=respostacontra, respostacoinc=respostacoinc)

@app.route("/inici", methods=["POST"])
def iniciar_sessio():
    iemail = request.form.get("EMail")
    icontrasenya = request.form.get("Contrasenya")
    irespostac=""
    irespostae=""

    if iemail=="":
        irespostae="Escriu el teu Email"
    
    if icontrasenya=="":
        irespostac="Escriu la teva contrasenya"

    if irespostac=="" and irespostae=="":
        cursor = conexio.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM usuaris_app WHERE email = %s", (iemail,))
        usuari = cursor.fetchone()

        if usuari is None:
            return render_template("inici_sessio.html", irespostae="No existeix cap sessió amb aquest correu", iemail="", icontrasenya="")

        if usuari["contrasenya"] != icontrasenya:
            return render_template("inici_sessio.html", irespostac="Contrasenya incorrecta", iemail=iemail)

        session["user_id"] = usuari["userid"]
        session["user_email"] = usuari["email"]
        return mostrar_camps(usuari["userid"])

    return render_template("inici_sessio.html", icontrasenya=icontrasenya, iemail=iemail, irespostac=irespostac, irespostae=irespostae)

@app.route("/camps", methods=["POST"])
def camps():
    cnom = request.form.get("Nom")
    ctamany = request.form.get("Tamany")
    crespostan=""
    crespostat=""
    usuari_id = session.get("user_id")
    if not usuari_id:
        return redirect(url_for("inici_sessio"))

    if cnom=="":
        crespostan="Escriu el Nom del camp"
    
    if ctamany=="":
        crespostat="Tamany del camp en ha"
    else:
        try:
            valor = float(ctamany)
            if valor <= 0:
                crespostat = "El tamany ha de ser positiu"
        except ValueError:
            crespostat = "El tamany ha de ser un número"

    if crespostan=="" and crespostat=="":
        try:
            cursor=conexio.cursor(dictionary=True, buffered=True)
            cursor.execute("""
                INSERT INTO camps (nomcamp, tamany)
                VALUES (%s, %s)
            """, (cnom, ctamany))
            conexio.commit()
            camps_id=cursor.lastrowid
            cursor.execute("""
                INSERT INTO usuaris_camps (userid, camps_id)
                VALUES (%s, %s)
            """, (usuari_id, camps_id))
            conexio.commit()
            cursor.close()
            flash("Camp desat correctament!", "accio")
            return mostrar_camps(usuari_id)
        except mysql.connector.IntegrityError:
            crespostan="Ja existeix aquest nom"
    else:
        flash("Error, revisa les dades i torna-ho a provar.", "error")

    return render_template("emergent_camp.html", cnom=cnom, ctamany=ctamany, crespostan=crespostan, crespostat=crespostat)

@app.route("/camps_edit", methods=["POST"])
def camps_edit():
    cnom = request.form.get("Nom")
    ctamany = request.form.get("Tamany")
    crespostan=""
    crespostat=""
    nom_camp = session.get("camp_seleccionat")
    usuari_id = session.get("user_id")
    if not usuari_id:
        return redirect(url_for("inici_sessio"))

    if cnom=="":
        crespostan="Escriu el nou Nom del camp"
    
    if ctamany=="":
        crespostat="nou Tamany del camp en ha"
    else:
        try:
            valor = float(ctamany)
            if valor <= 0:
                crespostat = "El tamany ha de ser positiu"
        except ValueError:
            crespostat = "El tamany ha de ser un número"

    if crespostan=="" and crespostat=="":
        try:
            data = (cnom, ctamany, nom_camp)


            if conexio.is_connected():
                cursor=conexio.cursor(dictionary=True, buffered=True)

            cursor.execute("""
                UPDATE camps 
                SET nomcamp = %s, tamany = %s
                WHERE nomcamp = %s
            """, data)

            if cursor.rowcount == 1:
                conexio.commit()

            else:
                conexio.rollback()


            cursor.close()
            flash("Camp editat correctament!", "accio")
            return mostrar_camps(usuari_id)
        except mysql.connector.IntegrityError:
            crespostan="Ja existeix aquest nom"
    else:
        flash("Error, revisa les dades i torna-ho a provar.", "error")

    return render_template("emergent_editable.html", cnom=cnom, ctamany=ctamany, crespostan=crespostan, crespostat=crespostat)


@app.route("/tancar", methods=["GET","POST"])
def tancar():
    mensaje = ""
    try:
        r = requests.get(f"http://{ESP32_IP}/abrir", timeout=5)
        mensaje = r.text
        print(mensaje)
    except ConnectTimeout:
        mensaje = "⚠️ Timeout: no se pudo conectar a la ESP32"
        print(mensaje)
    except RequestException as e:
        mensaje = f"⚠️ Error al conectar a la ESP32: {e}"
        print(mensaje)
    
    return render_template("camp0.html")

@app.route("/obrir", methods=["GET","POST"])
def obrir():
    mensaje = ""
    try:
        r = requests.get(f"http://{ESP32_IP}/cerrar", timeout=5)
        mensaje = r.text
        print(mensaje)
    except ConnectTimeout:
        mensaje = "⚠️ Timeout: no se pudo conectar a la ESP32"
        print(mensaje)
    except RequestException as e:
        mensaje = f"⚠️ Error al conectar a la ESP32: {e}"
        print(mensaje)
        
    return render_template("camp0.html")

@app.route("/tancar2", methods=["GET","POST"])
def tancar2():
    mensaje = ""
    try:
        r = requests.get(f"http://{ESP32_IP}/abrir2", timeout=5)
        mensaje = r.text
        print(mensaje)
    except ConnectTimeout:
        mensaje = "⚠️ Timeout: no se pudo conectar a la ESP32"
        print(mensaje)
    except RequestException as e:
        mensaje = f"⚠️ Error al conectar a la ESP32: {e}"
        print(mensaje)
    
    return render_template("camp0.html")

@app.route("/obrir2", methods=["GET","POST"])
def obrir2():
    mensaje = ""
    try:
        r = requests.get(f"http://{ESP32_IP}/cerrar2", timeout=5)
        mensaje = r.text
        print(mensaje)
    except ConnectTimeout:
        mensaje = "⚠️ Timeout: no s'ha pogut conectar a la placa ESP32"
        print(mensaje)
    except RequestException as e:
        mensaje = f"⚠️ Error al conectar-se a la ESP32: {e}"
        print(mensaje)
    
    return render_template("camp0.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000 ,debug=True, use_reloader=False)
