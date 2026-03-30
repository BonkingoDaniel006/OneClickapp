import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_passwords():
    # Connexion à ta base MySQL
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    cursor = db.cursor(dictionary=True)

    # 1. Récupérer tous les utilisateurs
    cursor.execute("SELECT id, password FROM buyers")
    users = cursor.fetchall()

    print(f"Mise à jour de {len(users)} utilisateurs...")

    for user in users:
        old_password = user['password']
        
        # On vérifie si c'est déjà un hash (pour éviter de hacher un hash !)
        if not old_password.startswith('$2b$'):
            # Hachage du mot de passe en clair
            hashed_pw = bcrypt.hashpw(old_password.encode('utf-8'), bcrypt.gensalt())
            
            # Mise à jour dans la base
            cursor.execute(
                "UPDATE buyers SET password = %s WHERE id = %s",
                (hashed_pw.decode('utf-8'), user['id'])
            )
            print(f"Utilisateur ID {user['id']} : OK")

    # 2. Valider les changements
    db.commit()
    cursor.close()
    db.close()
    print("Migration terminée avec succès !")

if __name__ == "__main__":
    migrate_passwords()
