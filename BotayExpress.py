import os
import random
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import mysql.connector
print("Démarrage de l'application BotayExpress...")
print("je suis dans le fichier BotayExpress.py")
print("Importations terminées, initialisation de l'application Flask...")

app = Flask(__name__)
app.secret_key = "super_secret_key"

# Connexion à la base de données
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Daniel12349",
    database="botayexpress"
)
cursor = conn.cursor(dictionary=True)


# ---------- ROUTES AUTH / ACCUEIL ----------

@app.route("/")
def home():
    return render_template("connexion.html")


@app.route("/connexion", methods=["GET"])
def connexion():
    return render_template("connexion.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


@app.route("/users")
def get_users():
    cursor.execute("SELECT * FROM buyers")
    users = cursor.fetchall()
    return jsonify(users)


@app.route("/create_account")
def create_account():
    return render_template("creation_compte_acheteur.html")


@app.route("/create_seller")
def create_seller():
    return render_template("creation_compte.html")


@app.route("/account_setup", methods=["POST"])
def account_setup():
    last_name = request.form["last_name"]
    first_name = request.form["first_name"]
    middle_name = request.form["middle_name"]
    email = request.form["email"]
    naissance = request.form["naissance"]
    adresse = request.form["adresse"]
    nom_boutique = request.form["nom_boutique"]
    description = request.form["description"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    if password != confirm_password:
        return render_template(
            "creation_compte_acheteur.html",
            error="Les mots de passe ne correspondent pas."
        )

    cursor.execute("""
        INSERT INTO buyers (last_name, first_name, middle_name, email, naissance, adresse, nom_boutique, description, password)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (last_name, first_name, middle_name, email, naissance, adresse, nom_boutique, description, password))

    conn.commit()
    return redirect(url_for("home"))


@app.route("/seller_setup", methods=["POST"])
def seller_setup():
    # Enregistrement d'un vendeur (e-shop)
    nom_proprio = request.form.get("nom_proprio")
    tel = request.form.get("tel")
    nom_e_shop = request.form.get("nom_e-shop")
    tel2 = request.form.get("tel2")
    motdepasse = request.form.get("motdepasse")

    # On stocke le vendeur dans la table buyers (approche simple)
    # On utilise le nom du responsable comme prénom, et le nom du e-shop comme nom de boutique.
    cursor.execute(
        """
        INSERT INTO buyers (last_name, first_name, email, adresse, nom_boutique, description, password)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (nom_e_shop, nom_proprio, None, tel, nom_e_shop, f"Tel: {tel} / {tel2}", motdepasse)
    )
    conn.commit()
    return redirect(url_for("home"))


# ---------- FIL D'ACTU + CONNEXION ----------

@app.route("/fil_actu", methods=["GET", "POST"])
def fil_actu():
    # GET : afficher le fil si connecté
    if request.method == "GET":
        if "user" in session:
            user = session["user"]

            cursor.execute("""
                SELECT p.*, b.nom_boutique
                FROM products p
                JOIN buyers b ON p.seller_id = b.id
            """)
            produits = cursor.fetchall()
            random.shuffle(produits)

            return render_template(
                "fil_actu.html",
                name=user["first_name"],
                produits=produits,
                user=user
            )
        else:
            return redirect(url_for("home"))

    # POST : tentative de connexion
    email = request.form.get("email")
    motdepasse = request.form.get("motdepasse")

    cursor.execute("SELECT * FROM buyers WHERE email = %s", (email,))
    user = cursor.fetchone()

    if user and user.get("password") == motdepasse:
        session["user"] = user

        cursor.execute("""
            SELECT p.*, b.nom_boutique
            FROM products p
            JOIN buyers b ON p.seller_id = b.id
        """)
        produits = cursor.fetchall()
        random.shuffle(produits)

        return render_template(
            "fil_actu.html",
            name=user["first_name"],
            produits=produits,
            user=user
        )

    return render_template(
        "connexion.html",
        error="Identifiants incorrects. Veuillez réessayer."
    )


@app.route("/acceuil")
def acceuil():
    return redirect(url_for("fil_actu"))


# ---------- PRODUITS / DETAILS / PANIER ----------

def get_product_with_seller(product_id):
    cursor.execute("""
        SELECT p.*, b.nom_boutique AS seller_name
        FROM products p
        JOIN buyers b ON p.seller_id = b.id
        WHERE p.id = %s
    """, (product_id,))
    return cursor.fetchone()


@app.route("/produit/<int:product_id>")
def produit_details(product_id):
    user = session.get("user")

    produit = get_product_with_seller(product_id)
    if not produit:
        return "Produit introuvable", 404

    added = request.args.get("added")

    return render_template(
        "detail_produit.html",
        produit=produit,
        panier="Produit ajouté au panier !" if added else None,
        user=user
    )


@app.route("/add_product/<int:product_id>", methods=["POST"])
def add_product(product_id):
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    produit = get_product_with_seller(product_id)
    if not produit:
        return "Produit introuvable", 404

    # Infos acheteur
    buyer_id = user["id"]
    buyer_first_name = user["first_name"]
    buyer_last_name = user["last_name"]

    # Quantité
    quantite_raw = request.form.get("quantite", "1")
    try:
        quantite = int(quantite_raw)
        if quantite < 1:
            quantite = 1
    except ValueError:
        quantite = 1

    # Prix total
    prix_total = quantite * float(produit["price"])

    # Insertion dans panier2
    cursor.execute("""
        INSERT INTO panier2 (
            buyer_id, buyer_first_name, buyer_last_name,
            product_id, product_name, product_price, product_description, product_image_url,
            seller_id, seller_name,
            quantite, prix_total
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        buyer_id, buyer_first_name, buyer_last_name,
        produit["id"], produit["name"], produit["price"], produit["description"], produit["image_url"],
        produit["seller_id"], produit["seller_name"],
        quantite, prix_total
    ))

    conn.commit()

    return redirect(url_for("produit_details", product_id=product_id, added=1))


# ---------- PROFIL / PAIEMENT / AVIS ----------

@app.route("/profil_acheteur")
def profil_acheteur():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    cursor.execute(
        "SELECT * FROM panier2 WHERE buyer_id = %s ORDER BY created_at DESC",
        (user["id"],)
    )
    cart_items = cursor.fetchall()

    total = 0.0
    for item in cart_items:
        total += float(item.get("prix_total") or 0)

    return render_template(
        "profil_acheteur.html",
        user=user,
        cart_items=cart_items,
        cart_total=total
    )


@app.route("/paiement")
def paiement():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    cursor.execute(
        "SELECT * FROM panier2 WHERE buyer_id = %s ORDER BY created_at DESC",
        (user["id"],)
    )
    cart_items = cursor.fetchall()

    total = 0.0
    for item in cart_items:
        total += float(item.get("prix_total") or 0)

    return render_template(
        "paiement.html",
        user=user,
        cart_items=cart_items,
        cart_total=total
    )


@app.route("/checkout", methods=["POST"])
def checkout():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    # Ici, la logique de paiement peut être ajoutée (ex: API de paiement)
    # Pour l'instant, on vide simplement le panier de l'utilisateur et on confirme.
    cursor.execute("DELETE FROM panier2 WHERE buyer_id = %s", (user["id"],))
    conn.commit()

    message = "Paiement effectué avec succès ! Votre commande est enregistrée."
    return render_template(
        "paiement.html",
        user=user,
        cart_items=[],
        cart_total=0,
        message=message
    )


@app.route("/avis_commande")
def avis_commande():
    return render_template("avis_commande.html")


# ---------- PROFIL VENDEUR / PRODUITS VENDEUR ----------

@app.route("/profil_vendeur")
def profil_vendeur():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM products WHERE seller_id = %s", (user["id"],))
    produits_vendeur = cursor.fetchall()

    return render_template("profil_vendeur.html", user=user, produits=produits_vendeur)


@app.route("/ajouter_produit")
def ajouter_produit():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    return render_template("ajouter_produit.html", user=user)


@app.route("/enregistrer_produit", methods=["POST"])
def enregistrer_produit():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    nom_produit = request.form.get("nom_produit")
    prix = request.form.get("prix")
    description = request.form.get("description")

    image_file = request.files.get("image_url")

    if image_file and image_file.filename != "":
        filename = secure_filename(image_file.filename)
        image_path = os.path.join("static/uploads", filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image_file.save(image_path)
        image_url = "/" + image_path.replace("\\", "/")
    else:
        image_url = None

    cursor.execute("""
        INSERT INTO products (seller_id, name, price, description, image_url)
        VALUES (%s, %s, %s, %s, %s)
    """, (user["id"], nom_produit, prix, description, image_url))

    conn.commit()
    return redirect(url_for("profil_vendeur"))


@app.route("/vendeur_details/<int:product_id>")
def vendeur_details(product_id):
    user = session.get("user")

    cursor2 = conn.cursor()
    cursor2.execute("""
        SELECT p.id, p.name, p.description, p.price, p.image_url, b.nom_boutique
        FROM products p
        JOIN buyers b ON p.seller_id = b.id
        WHERE p.id = %s
    """, (product_id,))

    produit = cursor2.fetchone()
    cursor2.close()

    if produit:
        produit_dict = {
            "id": produit[0],
            "name": produit[1],
            "description": produit[2],
            "price": produit[3],
            "image_url": produit[4],
            "nom_boutique": produit[5]
        }
        return render_template("vendeur_details.html", produit=produit_dict, user=user)

    return "Produit introuvable", 404


# ---------- MODIFICATION PROFIL ----------

@app.route("/modifier_profil_acheteur")
def modifier_profil_acheteur():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    return render_template("modifier_profil.html", user=user)


@app.route("/modifier_profil", methods=["GET", "POST"])
def modifier_profil():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    user_id = user["id"]

    cursor_local = conn.cursor(dictionary=True)
    cursor_local.execute("SELECT * FROM buyers WHERE id=%s", (user_id,))
    user_db = cursor_local.fetchone()

    if request.method == "POST":
        email = request.form["email"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        middle_name = request.form.get("middle_name")
        adresse = request.form["adresse"]
        naissance = request.form["naissance"]
        nom_boutique = request.form.get("nom_boutique")
        description = request.form.get("description")
        motdepasse = request.form.get("motdepasse")
        confirmer = request.form.get("confirmer")

        file = request.files.get("profil")
        profil_path = user_db.get("profil")

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            profil_path = os.path.join("static/profils", filename)
            os.makedirs(os.path.dirname(profil_path), exist_ok=True)
            file.save(profil_path)

        if motdepasse and motdepasse == confirmer:
            cursor_local.execute("""
                UPDATE buyers SET email=%s, first_name=%s, last_name=%s,
                middle_name=%s, adresse=%s, naissance=%s, password=%s,
                profil=%s, nom_boutique=%s, description=%s WHERE id=%s
            """, (email, first_name, last_name, middle_name, adresse, naissance,
                  motdepasse, profil_path, nom_boutique, description, user_id))
        else:
            cursor_local.execute("""
                UPDATE buyers SET email=%s, first_name=%s, last_name=%s,
                middle_name=%s, adresse=%s, naissance=%s, profil=%s,
                nom_boutique=%s, description=%s WHERE id=%s
            """, (email, first_name, last_name, middle_name, adresse, naissance,
                  profil_path, nom_boutique, description, user_id))

        conn.commit()

        # Mettre à jour la session
        cursor_local.execute("SELECT * FROM buyers WHERE id=%s", (user_id,))
        session["user"] = cursor_local.fetchone()

        cursor_local.close()
        return redirect("/profil_acheteur")

    cursor_local.close()
    return render_template("modifier_profil.html", user=user_db)


# ---------- NOTIFICATIONS ----------

@app.route("/notifications")
def notifications():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    return render_template("notif_vendeur.html", user=user)


if __name__ == "__main__":
    app.run(debug=True)