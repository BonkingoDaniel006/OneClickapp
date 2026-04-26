import os
import random
from flask import Flask, jsonify, render_template, request, redirect, url_for, make_response
from werkzeug.utils import secure_filename
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, set_access_cookies, unset_jwt_cookies, get_jwt
) #import des element pour jwt
from datetime import timedelta



load_dotenv()

app = Flask(__name__)

# CLES DE SECURITE 
app.secret_key = os.getenv("jwt_key")
app.config["JWT_SECRET_KEY"] = os.getenv("jwt_key")

# PARAMETRES DES COOKIES 
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)

# --- BLINDAGE CSRF ---
app.config["JWT_COOKIE_CSRF_PROTECT"] = True  # ACTIVÉ
app.config['JWT_ACCESS_CSRF_HEADER_NAME'] = "X-CSRF-TOKEN"

# --- LE PIEGE A EVITER ---
# Si tu es sur ton PC (http://127.0.0.1), SECURE doit être False.
# En ligne (HTTPS), il DOIT être True.
app.config['JWT_COOKIE_SECURE'] = False # Mets True uniquement quand tu passes en HTTPS

jwt = JWTManager(app)


# Redirection automatique si non connecté
@jwt.unauthorized_loader
def customized_response(callback):
    return redirect(url_for('connexion'))


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@app.route("/")
def home():
    return render_template("connexion.html")

@app.route("/connexion", methods=["GET"])
def connexion():
    return render_template("connexion.html")

@app.route("/logout")
def logout():
    response = make_response(redirect(url_for("home")))
    unset_jwt_cookies(response)
    return response

from flask import jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt

@app.route("/users")
@jwt_required()
def get_users():
    # 1. Vérification du rôle (Optionnel mais recommandé)
    claims = get_jwt()
    if claims.get("is_admin") is not True:
        return jsonify({"msg": "Accès refusé : autorisé seulement aux admin"}), 403

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 2. Sélection explicite des colonnes (Pas de password !)
        query = "SELECT id, first_name, last_name, email FROM buyers"
        cursor.execute(query)
        
        users = cursor.fetchall()
        return jsonify(users)
    
    except Exception as e:
        return jsonify({"error": "Erreur lors de la récupération"}), 500
    
    finally:
        # Toujours fermer la connexion, même en cas d'erreur
        cursor.close()
        conn.close()

@app.route("/create_account")
def create_account():
    return render_template("creation_compte_acheteur.html")

@app.route("/create_seller")
def create_seller():
    return render_template("creation_compte.html")

@app.route("/account_setup", methods=["POST"])
def account_setup():
    last_name = request.form.get("last_name")
    first_name = request.form.get("first_name")
    middle_name = request.form.get("middle_name")
    email = request.form.get("email")
    naissance = request.form.get("naissance")
    adresse = request.form.get("adresse")
    nom_boutique = request.form.get("nom_boutique")
    description = request.form.get("description")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if password != confirm_password:
        return render_template("creation_compte_acheteur.html", error="Les mots de passe ne correspondent pas.")
    
    hash_password = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO buyers (last_name, first_name, middle_name, email, naissance, adresse, nom_boutique, description, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (last_name, first_name, middle_name, email, naissance, adresse, nom_boutique, description, hash_password))
        conn.commit()
    except Exception as e:
        return f"Erreur : {e}"
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("home"))

@app.route("/seller_setup", methods=["POST"])
def seller_setup():
    nom_proprio = request.form.get("nom_proprio")
    tel = request.form.get("tel")
    nom_e_shop = request.form.get("nom_e-shop")
    tel2 = request.form.get("tel2")
    motdepasse = request.form.get("motdepasse")

    hash_password = generate_password_hash(motdepasse)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO buyers (last_name, first_name, email, adresse, nom_boutique, description, password)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (nom_e_shop, nom_proprio, None, tel, nom_e_shop, f"Tel: {tel} / {tel2}", hash_password)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("home"))

@app.route("/fil_actu", methods=["GET", "POST"])
def fil_actu():
    if request.method == "POST":
        email = request.form.get("email")
        motdepasse = request.form.get("motdepasse")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM buyers WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], motdepasse):
            access_token = create_access_token(
                identity=str(user['id']),
                additional_claims={
                    "first_name": user['first_name'],
                    "last_name": user['last_name'],
                    "email": user.get('email'), # Optionnel pour l'affichage
                    "profil": user.get('profil') , # Chemin image
                    "is_vendor": bool(user.get('nom_boutique'))
                }
            )
            response = make_response(redirect(url_for("fil_actu")))
            set_access_cookies(response, access_token)
            return response
        
        return render_template("connexion.html", error="Email ou mot de passe incorrect.")

    return display_fil_actu()

@jwt_required()
def display_fil_actu():
    claims = get_jwt()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, b.nom_boutique 
        FROM products p 
        JOIN buyers b ON p.seller_id = b.id
    """)
    produits = cursor.fetchall()
    random.shuffle(produits)
    cursor.close()
    conn.close()
    
    return render_template(
        "fil_actu.html",
        name=claims.get("first_name"),
        produits=produits,
        user=claims
    )

@app.route("/acceuil")
@jwt_required()
def acceuil():
    return redirect(url_for("fil_actu"))

@app.route("/produit/<int:product_id>")
@jwt_required(optional=True)
def vendeur_details(product_id):
    user_id = get_jwt_identity()
    user = get_jwt() if user_id else None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, b.nom_boutique AS seller_name
        FROM products p
        JOIN buyers b ON p.seller_id = b.id
        WHERE p.id = %s
    """, (product_id,))
    produit = cursor.fetchone()
    added = request.args.get("added")
    cursor.close()
    conn.close()

    if not produit:
        return "Produit introuvable", 404

    return render_template(
        "detail_produit.html",
        produit=produit,
        panier="Produit ajouté au panier !" if added else None,
        user=user
    )

@app.route("/add_product/<int:product_id>", methods=["POST"])
@jwt_required()
def add_product(product_id):
    buyer_id = get_jwt_identity()
    claims = get_jwt()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, b.nom_boutique AS seller_name
        FROM products p
        JOIN buyers b ON p.seller_id = b.id
        WHERE p.id = %s
    """, (product_id,))
    produit = cursor.fetchone()

    if not produit:
        cursor.close()
        conn.close()
        return "Produit introuvable", 404

    quantite = int(request.form.get("quantite", 1))
    prix_total = quantite * float(produit["price"])

    cursor.execute("""
        INSERT INTO panier2 (
            buyer_id, buyer_first_name, buyer_last_name,
            product_id, product_name, product_price, product_description, product_image_url,
            seller_id, seller_name, quantite, prix_total
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        buyer_id, claims.get("first_name"), claims.get("last_name"),
        produit["id"], produit["name"], produit["price"], produit["description"], produit["image_url"],
        produit["seller_id"], produit["seller_name"], quantite, prix_total
    ))

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("vendeur_details", product_id=product_id, added=1))

@app.route("/profil_acheteur")
@jwt_required()
def profil_acheteur():
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM panier2 WHERE buyer_id = %s ORDER BY created_at DESC", (user_id,))
    cart_items = cursor.fetchall()
    total = sum(float(item.get("prix_total") or 0) for item in cart_items)
    cursor.close()
    conn.close()
    
    return render_template("profil_acheteur.html", user=claims, cart_items=cart_items, cart_total=total)

@app.route("/paiement")
@jwt_required()
def paiement():
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM panier2 WHERE buyer_id = %s ORDER BY created_at DESC", (user_id,))
    cart_items = cursor.fetchall()
    total = sum(float(item.get("prix_total") or 0) for item in cart_items)
    cursor.close()
    conn.close()
    
    return render_template("paiement.html", user=claims, cart_items=cart_items, cart_total=total)

@app.route("/checkout", methods=["POST"])
@jwt_required()
def checkout():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM panier2 WHERE buyer_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return render_template("paiement.html", user=get_jwt(), cart_items=[], cart_total=0, message="Paiement effectué avec succès !")

@app.route("/profil_vendeur")
@jwt_required()
def profil_vendeur():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE seller_id = %s", (user_id,))
    produits = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("profil_vendeur.html", user=get_jwt(), produits=produits)

@app.route("/ajouter_produit")
@jwt_required()
def ajouter_produit():
    return render_template("ajouter_produit.html", user=get_jwt())

@app.route("/enregistrer_produit", methods=["POST"])
@jwt_required()
def enregistrer_produit():
    user_id = get_jwt_identity()
    nom_produit = request.form.get("nom_produit")
    prix = request.form.get("prix")
    description = request.form.get("description")
    image_file = request.files.get("image_url")

    image_url = None
    if image_file and image_file.filename != "":
        filename = secure_filename(image_file.filename)
        image_path = os.path.join("static/uploads", filename)
        image_file.save(image_path)
        image_url = "/" + image_path.replace("\\", "/")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (seller_id, name, price, description, image_url) VALUES (%s, %s, %s, %s, %s)", 
                   (user_id, nom_produit, prix, description, image_url))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("profil_vendeur"))

@app.route("/notifications")
@jwt_required()
def notifications():
    return render_template("notif_vendeur.html", user=get_jwt())


@app.route("/modifier_profil")
@jwt_required()
def modifier_profil():
    # On récupère les données du token (claims) pour identifier l'utilisateur
    claims = get_jwt()
    
    # On renvoie le template en lui passant la variable 'user'
    return render_template("modifier_profil.html", user=claims)



if __name__ == "__main__":
    result = os.getenv("FLASK_ENV")
    app.run(debug= result)
    

