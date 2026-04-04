import mysql.connector
from werkzeug.security import generate_password_hash

# 1. Connexion à ta base MySQL
db = mysql.connector.connect(host="localhost", user="root", password="Daniel12349", database="botayexpress")
cursor = db.cursor(dictionary=True)

# 2. Récupérer tous les utilisateurs
cursor.execute("SELECT id, password FROM buyers")
utilisateurs = cursor.fetchall()

for user in utilisateurs:
    # On vérifie si le mot de passe est déjà haché (astuce : un hash commence souvent par 'pbkdf2')
    if not user['password'].startswith('pbkdf2'):
        # On hache l'ancien mot de passe en clair
        nouveau_hash = generate_password_hash(user['password'])
        
        # 3. On met à jour la ligne dans la DB
        cursor.execute("UPDATE buyers SET password = %s WHERE id = %s", (nouveau_hash, user['id']))

db.commit()
print("Migration terminée : Tous les mots de passe sont hachés !")