from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from num2words import num2words
import qrcode
import base64
from io import BytesIO
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') # Indispensable pour utiliser "session" et "flash"
# --- CONFIGURATION DE LA LIAISON DB ---
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT'))
app.config['MYSQL_SSL_CA'] = os.getenv('MYSQL_SSL_CA')
# ... (Ta configuration MySQL : HOST, USER, PASSWORD, DB, PORT) ...
# --- CONFIGURATION DE SÉCURITÉ POUR HUGGING FACE (IFRAME) ---
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
mysql = MySQL(app)
# --- Calcul du taux de repas ---
def calculer_taux_repas(date_dep_str, heure_dep_str, date_ret_str, heure_ret_str):
    if not heure_dep_str: heure_dep_str = "09:00"
    if not heure_ret_str: heure_ret_str = "23:00"
    
    try:
        format_date = "%Y-%m-%d %H:%M"
        depart = datetime.strptime(f"{date_dep_str} {heure_dep_str}", format_date)
        retour = datetime.strptime(f"{date_ret_str} {heure_ret_str}", format_date)
        
        nombre_repas = 0
        jour_actuel = depart.date()
        jour_fin = retour.date()

        while jour_actuel <= jour_fin:
            # 1. Tranche du Matin (Petit-déjeuner : 06h00 - 08h00)
            matin_debut = datetime.combine(jour_actuel, datetime.strptime("06:00", "%H:%M").time())
            matin_fin = datetime.combine(jour_actuel, datetime.strptime("08:00", "%H:%M").time())

            # 2. Tranche du Midi (Déjeuner : 11h30 - 14h00)
            midi_debut = datetime.combine(jour_actuel, datetime.strptime("11:30", "%H:%M").time())
            midi_fin = datetime.combine(jour_actuel, datetime.strptime("14:00", "%H:%M").time())
            
            # 3. Tranche du Soir (Dîner : 18h30 - 21h00)
            soir_debut = datetime.combine(jour_actuel, datetime.strptime("18:30", "%H:%M").time())
            soir_fin = datetime.combine(jour_actuel, datetime.strptime("21:00", "%H:%M").time())

            # --- LES VÉRIFICATIONS ---
            
            # MODIFICATION ICI : On vérifie que le jour actuel N'EST PAS le jour de départ (depart.date())
            if jour_actuel != depart.date() and depart <= matin_fin and retour >= matin_debut:
                nombre_repas += 1  # Ajout du petit-déjeuner

            if depart <= midi_fin and retour >= midi_debut:
                nombre_repas += 1  # Ajout du déjeuner

            if depart <= soir_fin and retour >= soir_debut:
                nombre_repas += 1  # Ajout du dîner

            # On passe au jour suivant
            jour_actuel += timedelta(days=1)

        return nombre_repas

    except Exception as e:
        print("Erreur de calcul des taux :", e)
        return 0
        # login :
@app.route('/')
def home():
    return render_template('login.html')

# --- LA NOUVELLE ROUTE POUR LE LOGIN ---
@app.route('/login', methods=['POST'])
def login():
    # 1. Récupérer les données saisies par l'utilisateur [cite: 52, 56]
    username = request.form.get('username')
    password = request.form.get('password')

    # 2. Interroger la base de données [cite: 55, 73, 74]
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # On cherche un utilisateur avec ce doti ET ce mot de passe
        cursor.execute("""
        SELECT c.*, u.service_affectation, u.nom, u.prenom 
        FROM compte_acces c
        INNER JOIN utilisateur u ON c.doti = u.doti 
        WHERE c.doti = %s 
    """, (username,))
        user = cursor.fetchone()
    finally:
        cursor.close()

    # 3. Vérifier le résultat [cite: 63, 64, 67]
   # 3. Vérifier le résultat
    if user and check_password_hash(user['mot_de_passe'], password):
        # Succès : Les informations sont correctes
        session['loggedin'] = True
        
        # Au lieu d'utiliser [1] ou [3], on utilise les vrais noms des colonnes !
        session['doti'] = user['doti']
        session['role'] = user['role']
        session['service'] = user['service_affectation']
        session['nom'] = user['nom']
        session['prenom'] = user['prenom']
        # On l'autorise à accéder à l'espace utilisateur
        return redirect(url_for('dashboard'))
    else:
        # Échec : On affiche l'erreur
        flash("DOTI ou mot de passe incorrect.", "danger")
        return redirect(url_for('home'))

# ==========================================
# CONSULTATION DES ORDRES DE MISSION
# ==========================================
@app.route('/liste_om')
def liste_om():
    if 'loggedin' not in session:
        flash("Veuillez vous connecter.", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # On récupère les infos de la personne connectée
    role_utilisateur = session.get('role')
    doti_utilisateur = session.get('doti')
    service_utilisateur = session.get('service')

    # 1. Le Directeur ou l'Admin voient TOUT l'historique
    if role_utilisateur in ['Admin', 'Directeur']:
        cursor.execute("""
            SELECT om.*, u.nom, u.prenom 
            FROM ordre_mission om
            JOIN utilisateur u ON om.doti_employe = u.doti
            ORDER BY om.date_creation DESC
        """)
        
    # 2. Le Chef de Service voit UNIQUEMENT les OM de son propre service
    elif role_utilisateur == 'Chef de service':
        cursor.execute("""
            SELECT om.*, u.nom, u.prenom 
            FROM ordre_mission om
            JOIN utilisateur u ON om.doti_employe = u.doti
            WHERE om.service_demandeur = %s
            ORDER BY om.date_creation DESC
        """, (service_utilisateur,))
        
    # 3. Les autres (fonctionnaires) voient UNIQUEMENT leurs propres missions
    else:
        cursor.execute("""
            SELECT om.*, u.nom, u.prenom 
            FROM ordre_mission om
            JOIN utilisateur u ON om.doti_employe = u.doti
            WHERE om.doti_employe = %s
            ORDER BY om.date_creation DESC
        """, (doti_utilisateur,))

    missions = cursor.fetchall()
    cursor.close()

    return render_template('admin/liste_om.html', missions=missions)
# --- ROUTE POUR SUPPRIMER UN OM ---
@app.route('/supprimer_om/<int:id_om>')
def supprimer_om(id_om):
    # Sécurité : On vérifie que c'est bien un Admin ou Directeur
    if 'loggedin' not in session or session.get('role') not in ['Admin', 'Directeur']:
        flash("Action non autorisée. Seul un administrateur peut supprimer un OM.", "danger")
        return redirect(url_for('liste_om'))

    cursor = mysql.connection.cursor()
    try:
        # On supprime la ligne qui correspond à cet ID
        cursor.execute("DELETE FROM ordre_mission WHERE id_om = %s", (id_om,))
        mysql.connection.commit()
        flash("L'Ordre de Mission a été supprimé avec succès.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash("Erreur lors de la suppression.", "danger")
        print("Erreur SQL :", e)
    finally:
        cursor.close()

    return redirect(url_for('liste_om'))

# ==========================================
# IMPRESSION DE L'ORDRE DE MISSION (AVEC QR CODE)
# ==========================================
@app.route('/imprimer_om/<id_om>')
def imprimer_om(id_om):
    # Sécurité de connexion
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # On récupère toutes les informations d'un coup (OM + Utilisateur + Véhicule)
        cursor.execute("""
            SELECT om.*, u.nom, u.prenom, u.cin, u.grade, u.fonction, u.doti, v.matricule 
            FROM ordre_mission om
            JOIN utilisateur u ON om.doti_employe = u.doti
            LEFT JOIN vehicule v ON om.id_vehicule = v.id_vehicule
            WHERE om.id_om = %s
        """, (id_om,))
        
        mission = cursor.fetchone()

        if not mission:
            flash("Cet Ordre de Mission n'existe pas.", "danger")
            return redirect(url_for('liste_om')) # Ou ta page d'historique

        # ------------------------------------------
        # GÉNÉRATION DU QR CODE SÉCURISÉ
        # ------------------------------------------
        # 1. Le texte caché dans le QR Code
        texte_securise = f"""--- DIRECTION PROVINCIALE OUARZAZATE ---
Document authentique généré électroniquement.
Ordre de Mission N° : {mission.get('numero_om', 'N/A')}
Bénéficiaire : {mission.get('nom', '')} {mission.get('prenom', '')}
Destination : {mission.get('itineraire', 'N/A')}
Départ le : {mission.get('date_depart', 'N/A')}"""

        # 2. Création de l'image
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data(texte_securise)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")

        # 3. Conversion en format lisible par le HTML (Base64)
        buffered = BytesIO()
        img_qr.save(buffered, format="PNG")
        qr_code_base64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Envoi de la variable "mission" et "qr_code" au fichier HTML
        # (On n'envoie plus "employe" séparément car tout est dans "mission")
        return render_template('admin/impression_om.html', 
                               mission=mission, 
                               qr_code=qr_code_base64)
                               
    except Exception as e:
        print(f"🚨 ERREUR CRITIQUE DANS IMPRIMER_OM : {str(e)}", flush=True)
        flash("Erreur lors de la génération du document.", "danger")
        return redirect(request.referrer or url_for('dashboard'))
    finally:
        cursor.close()
        # --- LA ROUTE DU TABLEAU DE BORD (DASHBOARD) ---
@app.route('/dashboard')
def dashboard():
    # On vérifie si l'utilisateur est bien connecté avant d'afficher la page
    if 'loggedin' in session:
        return render_template('dashboard.html', role=session['role'])
    
    # S'il n'est pas connecté, on le renvoie au login
    return redirect(url_for('home'))
# --- LA ROUTE DE DÉCONNEXION ---
@app.route('/logout')
def logout():
    # 1. On vide entièrement la mémoire de la session
    session.clear()
    
    # 2. On affiche un petit message de confirmation
    flash("Vous avez été déconnecté avec succès.", "success")
    
    # 3. On renvoie vers la page de connexion (la fonction 'home')
    return redirect(url_for('home'))

# ==========================================
# GESTION DES UTILISATEURS (Admin & Chefs)
# ==========================================
@app.route('/utilisateurs') # J'ai enlevé '/admin' de l'URL car les chefs y accèdent aussi
def gestion_utilisateurs():
    # 1. Vérifier si l'utilisateur est connecté
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    role_utilisateur = session.get('role')
    service_utilisateur = session.get('service')

    # 2. Sécurité : On expulse les simples les fonctionnaires ou le Parc Auto
    if role_utilisateur not in ['Admin', 'Directeur', 'Chef de service']:
        flash("Accès refusé. Vous n'avez pas les droits pour gérer les utilisateurs.", "danger")
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 3. L'Admin et le Directeur voient TOUT LE MONDE
    if role_utilisateur in ['Admin', 'Directeur']:
        cursor.execute("""
            SELECT u.doti, u.nom, u.prenom, u.service_affectation, u.grade, c.role 
            FROM utilisateur u
            LEFT JOIN compte_acces c ON u.doti = c.doti
            ORDER BY u.service_affectation ASC, u.nom ASC
        """)
        
    # 4. Le Chef de Service ne voit QUE les fonctionnaires DE SON SERVICE
    elif role_utilisateur == 'Chef de service':
        cursor.execute("""
            SELECT u.doti, u.nom, u.prenom, u.service_affectation, u.grade, c.role 
            FROM utilisateur u
            LEFT JOIN compte_acces c ON u.doti = c.doti
            WHERE u.service_affectation = %s
            ORDER BY u.nom ASC
        """, (service_utilisateur,))

    utilisateurs = cursor.fetchall()
    cursor.close()

    return render_template('admin/gestion_utilisateurs.html', utilisateurs=utilisateurs)
# ==========================================
# SUPPRIMER UN UTILISATEUR
# ==========================================
@app.route('/supprimer_utilisateur/<doti>')
def supprimer_utilisateur(doti):
    if 'loggedin' not in session or session.get('role') not in ['Admin', 'Directeur', 'Chef de service']:
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor()
    try:
# Sécurité : Un Chef de service ne peut pas supprimer un Admin ou un autre Chef
        if session.get('role') == 'Chef de service':
            cursor.execute("SELECT role FROM compte_acces WHERE doti = %s", (doti,))
            user_role = cursor.fetchone()
            if user_role and user_role[0] in ['Admin', 'Directeur', 'Chef de service']:
                flash("Vous ne pouvez pas supprimer ce type de compte.", "danger")
                return redirect(url_for('gestion_utilisateurs'))

        # Il faut supprimer dans les 2 tables ! D'abord le compte d'accès, puis l'identité.
        cursor.execute("DELETE FROM compte_acces WHERE doti = %s", (doti,))
        cursor.execute("DELETE FROM utilisateur WHERE doti = %s", (doti,))
        mysql.connection.commit()
        
        flash("Utilisateur supprimé avec succès.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash("Erreur lors de la suppression.", "danger")
        print(f"🚨 ERREUR CRITIQUE : {str(e)}", flush=True)
    finally:
        cursor.close()

    return redirect(url_for('gestion_utilisateurs'))

# ==========================================
# AJOUTER UN UTILISATEUR
# ==========================================
@app.route('/ajouter_utilisateur', methods=['GET', 'POST'])
def ajouter_utilisateur():

    if 'loggedin' not in session or session.get('role') not in ['Admin', 'Directeur', 'Chef de service']:
        return redirect(url_for('dashboard'))

    tous_les_services = [
       "CPSI (Centre Provincial du Système d'Information)",
                                     "Encadrement des Établissements et Orientation",
                                     "Affaires Pédagogiques", "Gestion des Ressources Humaines",
                                       "Affaires Administratives et Financières", "Planification et Carte Scolaire",
                                         "Centre Provincial des Examens", "Affaires Juridiques et Partenariats", 
                                         "Constructions, Équipements et Patrimoine"
    ]

    # Logique de restriction (comme pour les OM)
    if session['role'] in ['Admin', 'Directeur']:
        services_disponibles = tous_les_services
        est_chef = False
    else:
        services_disponibles = [session.get('service')]
        est_chef = True

    if request.method == 'POST':
        doti = request.form.get('doti')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        cin = request.form.get('cin')
        echelle = request.form.get('echelle')
        grade = request.form.get('grade')
        fonction = request.form.get('fonction')
        service = request.form.get('service_affectation')
        banque = request.form.get('banque')
        rib = request.form.get('rib')
        role = request.form.get('role')
        password = request.form.get('password')
        # Récupération des données du formulaire
        password_hash= generate_password_hash(password) if password else None
        # 1. On supprime les espaces (au cas où l'utilisateur a fait un copier/coller avec des espaces)
        if rib:
            rib = rib.replace(" ", "")
            
        # 2. On vérifie si la longueur est de 24 et si ce ne sont QUE des chiffres
        if not rib or not rib.isdigit() or len(rib) != 24:
            flash("Erreur : Le RIB doit être composé de 24 chiffres exactement.", "danger")
            return redirect(url_for('ajouter_utilisateur')) # Renvoie l'utilisateur vers la page précédente
        cursor = mysql.connection.cursor()
        try:
            # 1. Vérifier si le DOTI existe déjà
            cursor.execute("SELECT doti FROM utilisateur WHERE doti = %s", (doti,))
            if cursor.fetchone():
                flash("Ce DOTI existe déjà dans le système.", "danger")
                return redirect(url_for('ajouter_utilisateur'))

            # 2. TOUJOURS insérer l'identité (La personne physique)
            cursor.execute("""
                INSERT INTO utilisateur (doti, nom, prenom, cin, echelle, grade, fonction, service_affectation, banque, rib) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (doti, nom, prenom, cin, echelle, grade, fonction, service, banque, rib))

            # 3. Insérer la sécurité UNIQUEMENT si ce n'est pas un simple fonctionnaire
            if role != "Aucun":
                cursor.execute("""
                    INSERT INTO compte_acces (doti, mot_de_passe, role) 
                    VALUES (%s, %s, %s)
                """, (doti, password_hash, role))

            mysql.connection.commit()
            flash("Nouvel utilisateur ajouté avec succès.", "success")
            return redirect(url_for('gestion_utilisateurs'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash("Erreur lors de l'enregistrement.", "danger")
            print("Erreur SQL:", e)
        finally:
            cursor.close()
    return render_template('admin/ajouter_utilisateur.html', services=services_disponibles, est_chef=est_chef)

# ==========================================
# MODIFIER UN UTILISATEUR (Mise à jour)
# ==========================================
@app.route('/modifier_utilisateur/<doti>', methods=['GET', 'POST'])
def modifier_utilisateur(doti):
    if 'loggedin' not in session or session.get('role') not in ['Admin', 'Directeur', 'Chef de service']:
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. Sécurité (Chef de service)
    if session['role'] == 'Chef de service':
        cursor.execute("SELECT service_affectation FROM utilisateur WHERE doti = %s", (doti,))
        verif_service = cursor.fetchone()
        if not verif_service or verif_service['service_affectation'] != session['service']:
            flash("Vous ne pouvez modifier que les fonctionnaires de votre propre service.", "danger")
            return redirect(url_for('gestion_utilisateurs'))

    tous_les_services = [
        "CPSI (Centre Provincial du Système d'Information)",
                                     "Encadrement des Établissements et Orientation",
                                     "Affaires Pédagogiques", "Gestion des Ressources Humaines",
                                       "Affaires Administratives et Financières", "Planification et Carte Scolaire",
                                         "Centre Provincial des Examens", "Affaires Juridiques et Partenariats", 
                                         "Constructions, Équipements et Patrimoine"
    ]

    if session['role'] in ['Admin', 'Directeur']:
        services_disponibles = tous_les_services
        est_chef = False
    else:
        services_disponibles = [session.get('service')]
        est_chef = True

    # 2. TRAITEMENT DU FORMULAIRE (Quand on clique sur Enregistrer)
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        cin = request.form.get('cin')
        echelle = request.form.get('echelle')
        grade = request.form.get('grade')
        fonction = request.form.get('fonction')
        service = request.form.get('service_affectation')
        banque = request.form.get('banque')
        rib = request.form.get('rib')
        role = request.form.get('role')
        nouveau_password = request.form.get('password') 
        if nouveau_password:
            nouveau_password = generate_password_hash(nouveau_password)
             
        # 1. On supprime les espaces (au cas où l'utilisateur a fait un copier/coller avec des espaces)
        if rib:
            rib = rib.replace(" ", "")
            
        # 2. On vérifie si la longueur est de 24 et si ce ne sont QUE des chiffres
        if not rib or not rib.isdigit() or len(rib) != 24:
            flash("Erreur : Le RIB doit être composé de 24 chiffres exactement.", "danger")
            return redirect(url_for('ajouter_utilisateur')) # Renvoie l'utilisateur vers la page précédente
        try:
            # A. Mise à jour de l'identité (Ça, ça ne change pas)
            cursor.execute("""
                UPDATE utilisateur 
                SET nom = %s, prenom = %s, cin = %s, echelle = %s, grade = %s, fonction = %s, service_affectation = %s, banque = %s, rib = %s
                WHERE doti = %s
            """, (nom, prenom, cin, echelle, grade, fonction, service, banque, rib, doti))

            # B. La logique de transition des accès
            # On vérifie si l'utilisateur avait DÉJÀ un compte d'accès avant la modification
            cursor.execute("SELECT doti FROM compte_acces WHERE doti = %s", (doti,))
            avait_compte = cursor.fetchone()

            if role == "Aucun":
                # Cas 1 : On le transforme en "Simple Fonctionnaire"
                # S'il avait un compte avant, on le supprime par sécurité
                if avait_compte:
                    cursor.execute("DELETE FROM compte_acces WHERE doti = %s", (doti,))
            else:
                # Cas 2 : Il doit avoir un rôle actif
                if avait_compte:
                    # Il avait déjà un compte, on le met juste à jour
                    cursor.execute("UPDATE compte_acces SET role = %s WHERE doti = %s", (role, doti))
                    if nouveau_password: # S'il a tapé un nouveau mot de passe
                        cursor.execute("UPDATE compte_acces SET mot_de_passe = %s WHERE doti = %s", (nouveau_password, doti))
                else:
                    # Il était "Simple Fonctionnaire" et on lui donne un accès !
                    # Il faut donc lui CRÉER son compte (mot de passe obligatoire)
                    if not nouveau_password:
                        flash("Vous donnez un accès à ce fonctionnaire. Un mot de passe est obligatoire.", "warning")
                        return redirect(url_for('modifier_utilisateur', doti=doti))
                        
                    cursor.execute("""
                        INSERT INTO compte_acces (doti, mot_de_passe, role) 
                        VALUES (%s, %s, %s)
                    """, (doti, nouveau_password, role))

            mysql.connection.commit()
            flash("Le profil a été mis à jour avec succès.", "success")
            return redirect(url_for('gestion_utilisateurs'))

        except Exception as e:
            mysql.connection.rollback()
            flash("Erreur lors de la mise à jour.", "danger")
            print("Erreur SQL:", e)

    # 3. AFFICHAGE DU FORMULAIRE (Quand on arrive sur la page)
    # L'ASTUCE EST ICI : On utilise un LEFT JOIN pour qu'il trouve le fonctionnaire même s'il n'a pas de compte
    cursor.execute("""
        SELECT u.*, c.role 
        FROM utilisateur u 
        LEFT JOIN compte_acces c ON u.doti = c.doti 
        WHERE u.doti = %s
    """, (doti,))
    user_data = cursor.fetchone()
    cursor.close()

    if not user_data:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for('gestion_utilisateurs'))

    # Si la personne n'avait pas de compte (role est vide), on force la valeur à "Aucun" pour le HTML
    if not user_data['role']:
        user_data['role'] = 'Aucun'

    return render_template('admin/modifier_utilisateur.html', user=user_data, services=services_disponibles, est_chef=est_chef)# --- ROUTE POUR CRÉER UN OM ---
# ==========================================
# cree om
# ==========================================

@app.route('/creer_om', methods=['GET', 'POST'])
def creer_om():
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    tous_les_services = [
       "CPSI (Centre Provincial du Système d'Information)",
                                     "Encadrement des Établissements et Orientation",
                                     "Affaires Pédagogiques", "Gestion des Ressources Humaines",
                                       "Affaires Administratives et Financières", "Planification et Carte Scolaire",
                                         "Centre Provincial des Examens", "Affaires Juridiques et Partenariats", 
                                         "Constructions, Équipements et Patrimoine"]
    if session['role'] in ['Admin', 'Directeur']:
        services_disponibles = tous_les_services
        est_chef = False
    else:
        services_disponibles = [session.get('service')]
        est_chef = True

    if request.method == 'POST':
        service_demandeur = request.form.get('service_demandeur')
        doti_employe = request.form.get('doti_employe')
        destination = request.form.get('destination')
        objet_mission = request.form.get('objet_mission')
        itineraire = request.form.get('itineraire')
        date_depart = request.form.get('date_depart')
        heure_depart = request.form.get('heure_depart')
        date_retour = request.form.get('date_retour')
        heure_retour = request.form.get('heure_retour')
        accompagne_de = request.form.get('accompagne_de')

        # === NOUVELLE SÉCURITÉ : FORCER 23:00 SI LA CASE EST VIDE ===
        if not heure_retour:
            heure_retour = "23:00"
        
        date_creation = date.today()
        annee_en_cours = date_creation.year

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        try:
            # === LE CALCUL MAGIQUE DU NUMÉRO OM ===
            # 1. On compte combien d'OM existent pour ce service, pour cette année
# === LE CALCUL MAGIQUE DU NUMÉRO OM (CORRIGÉ) ===
        # 1. On cherche le numéro le PLUS ÉLEVÉ (MAX) pour ce service et cette année
            cursor.execute("""
                SELECT MAX(CAST(SUBSTRING_INDEX(numero_om, '/', 1) AS UNSIGNED)) as max_num
                FROM ordre_mission
                WHERE service_demandeur = %s AND YEAR(date_creation) = %s
            """, (service_demandeur, annee_en_cours))
            
            resultat = cursor.fetchone()
            
            # Astuce pour éviter les erreurs si c'est le tout premier OM de l'année
            # (Vérifie si resultat est un dictionnaire ou un tuple selon ta config)
            if type(resultat) is dict:
                valeur_max = resultat['max_num']
            else:
                valeur_max = resultat[0] if resultat else None

            if valeur_max is not None:
                compteur_actuel = int(valeur_max)
            else:
                compteur_actuel = 0  # Aucun OM n'existe encore pour ce service cette année
                
            # 2. Le prochain numéro est le maximum + 1
            prochain_numero = compteur_actuel + 1
            
            # 3. On crée la chaîne de caractères finale (Ex: "1/2026")
            numero_om_calcule = f"{prochain_numero}/{annee_en_cours}"
                # === INSERTION DANS LA BASE ===
            # ... (récupération de tes autres variables : date_depart, heure_depart, etc.)
        
            # 1. On calcule le nombre de taux automatiquement
            nombre_taux = calculer_taux_repas(date_depart, heure_depart, date_retour, heure_retour)

            # 2. On l'ajoute dans la requête SQL
            cursor.execute("""
                INSERT INTO ordre_mission (
                    numero_om, service_demandeur, doti_employe, destination, objet_mission, 
                    itineraire, date_depart, heure_depart, date_retour, heure_retour, 
                    nombre_taux, accompagne_de, date_creation, statut
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Attente Parc')
            """, (
                numero_om_calcule, service_demandeur, doti_employe, destination, objet_mission, 
                itineraire, date_depart, heure_depart, date_retour, heure_retour, 
                nombre_taux, accompagne_de, date_creation
            ))
            
            mysql.connection.commit()
            flash(f"L'Ordre de Mission N° {numero_om_calcule} a été généré avec succès.", "success")
            return redirect(url_for('dashboard'))

        except Exception as e:
            mysql.connection.rollback()
            flash("Erreur lors de l'enregistrement.", "danger")
            print(f"🚨 ERREUR CRITIQUE DANS créer OM : {str(e)}", flush=True)
        finally:
            cursor.close()

    return render_template('admin/form_om.html', 
                           services=services_disponibles, 
                           est_chef=est_chef)
@app.route('/modifier_taux/<int:id>', methods=['POST'])
def modifier_taux(id):
    # --- 1. SÉCURITÉ : Vérifier si l'utilisateur est connecté ---
    # (Adapte 'doti' ou 'role' selon ce que tu utilises dans tes autres routes pour vérifier la connexion)
    if 'role' not in session: 
        flash("Accès refusé. Veuillez vous connecter.", "danger")
        return redirect(url_for('login')) # Remplace 'login' par le nom de ta route de connexion si besoin

    # --- (Optionnel) SÉCURITÉ 2 : Restreindre selon le rôle ---
    # Si tu veux que seuls l'Admin ou le Directeur puissent modifier le taux, décommente ces lignes :
    # if session.get('role') not in ['Admin', 'Directeur']:
    #     flash("Vous n'avez pas l'autorisation de modifier ce taux.", "danger")
    #     return redirect(url_for('liste_om'))

    # --- 2. TRAITEMENT DE LA MODIFICATION ---
    nouveau_taux = request.form.get('nouveau_taux')
    
    if nouveau_taux and nouveau_taux.isdigit():
        cursor = mysql.connection.cursor()
        try:
            # Mise à jour dans la base de données
            cursor.execute("UPDATE ordre_mission SET nombre_taux = %s WHERE id_om = %s", (nouveau_taux, id))
            mysql.connection.commit()
            flash("Le nombre de taux a été mis à jour avec succès.", "success")
        except Exception as e:
            mysql.connection.rollback()
            print(f"🚨 ERREUR DANS MODIFIER_TAUX : {str(e)}", flush=True)
            flash("Erreur lors de la modification du taux.", "danger")
            
    # On redirige vers la page du tableau
    return redirect(url_for('liste_om'))
@app.route('/modifier_om/<int:id>', methods=['GET', 'POST'])
def modifier_om(id):
    # Sécurité : Vérifier si connecté
    if 'role' not in session:
        flash("Accès refusé. Veuillez vous connecter.", "danger")
        return redirect(url_for('login'))
    tous_les_services = [
       "CPSI (Centre Provincial du Système d'Information)",
                                     "Encadrement des Établissements et Orientation",
                                     "Affaires Pédagogiques", "Gestion des Ressources Humaines",
                                       "Affaires Administratives et Financières", "Planification et Carte Scolaire",
                                         "Centre Provincial des Examens", "Affaires Juridiques et Partenariats", 
                                         "Constructions, Équipements et Patrimoine"]
    if session['role'] in ['Admin', 'Directeur']:
        services_disponibles = tous_les_services
        est_chef = False
    else:
        services_disponibles = [session.get('service')]
        est_chef = True
    cursor = mysql.connection.cursor()

    if request.method == 'POST':
        # 1. On récupère les nouvelles données tapées dans le formulaire
        destination = request.form.get('destination')
        objet_mission = request.form.get('objet_mission')
        itineraire = request.form.get('itineraire')
        date_depart = request.form.get('date_depart')
        heure_depart = request.form.get('heure_depart')
        date_retour = request.form.get('date_retour')
        heure_retour = request.form.get('heure_retour')
        moyen_transport = request.form.get('moyen_transport')
        accompagne_de = request.form.get('accompagne_de')

        try:
            # 2. On met à jour la base de données
            cursor.execute("""
                UPDATE ordre_mission 
                SET destination = %s, objet_mission = %s, itineraire = %s,
                    date_depart = %s, heure_depart = %s, date_retour = %s, 
                    heure_retour = %s, moyen_transport = %s, accompagne_de = %s
                WHERE id_om = %s
            """, (destination, objet_mission, itineraire, date_depart, heure_depart, 
                  date_retour, heure_retour, moyen_transport, accompagne_de, id))
            
            mysql.connection.commit()
            flash("L'Ordre de Mission a été modifié avec succès.", "success")
            return redirect(url_for('liste_om'))
            
        except Exception as e:
            mysql.connection.rollback()
            print(f"🚨 ERREUR UPDATE OM : {str(e)}", flush=True)
            flash("Erreur lors de la modification de l'OM.", "danger")

  # Si c'est un GET (affichage de la page) : on récupère les infos actuelles de l'OM
    cursor.execute("SELECT * FROM ordre_mission WHERE id_om = %s", (id,))
    row = cursor.fetchone()
    
    if not row:
        flash("Ordre de mission introuvable.", "danger")
        return redirect(url_for('liste_om'))

    # MAGIE PYTHON : On transforme le 'tuple' (liste) en dictionnaire grâce aux noms des colonnes
    colonnes = [col[0] for col in cursor.description]
    om_dict = dict(zip(colonnes, row))

    return render_template('admin/modifier_om.html', om=om_dict, services=services_disponibles, est_chef=est_chef)
# ==========================================
# ESPACE CHEF DE PARC : GESTION DES VÉHICULES
# ==========================================

@app.route('/gestion_parc')
def gestion_parc():
    if 'loggedin' not in session or session['role'] != 'Chef de parc':
        flash("Accès refusé.", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. Les missions qui attendent une voiture
    cursor.execute("""
        SELECT om.id_om, om.numero_om, om.destination, om.service_demandeur, om.date_depart, u.nom, u.prenom 
        FROM ordre_mission om
        JOIN utilisateur u ON om.doti_employe = u.doti
        WHERE om.statut = 'Attente Parc'
    """)
    missions_attente = cursor.fetchall()

    # 2. Les missions actuellement sur la route (pour valider le retour)
    # cursor.execute("""
    #     SELECT om.id_om, om.numero_om, om.destination, v.matricule
    #     FROM ordre_mission om
    #     JOIN vehicule v ON om.id_vehicule = v.id_vehicule
    #     WHERE om.statut = 'Terminée' AND om.km_retour IS NULL
    # """)
    missions_en_cours = cursor.fetchall()

    # 3. Les véhicules garés au parking
    cursor.execute("""
        SELECT * FROM vehicule 
        WHERE id_vehicule NOT IN (
            SELECT id_vehicule 
            FROM ordre_mission 
            WHERE id_vehicule IS NOT NULL 
            AND CONCAT(date_retour, ' ', heure_retour) >= NOW()
        )
    """)
    vehicules_disponibles = cursor.fetchall()

    cursor.close()
    return render_template('chef_parc/gestion_parc.html', 
                           missions=missions_attente, 
                           missions_en_cours=missions_en_cours, 
                           vehicules=vehicules_disponibles)


# --- ACTION 1 : VALIDER LE DÉPART (Assigner la voiture) ---
@app.route('/chef_parc/valider_depart', methods=['POST'])
def valider_depart():
    id_om = request.form.get('id_om')
    moyen_transport = request.form.get('moyen_transport')
    
    cursor = mysql.connection.cursor()
    try:
        if moyen_transport == 'CTM':
            # Passe directement en 'Terminée'
            cursor.execute("""
                UPDATE ordre_mission 
                SET moyen_transport = %s, statut = 'Terminée' 
                WHERE id_om = %s
            """, (moyen_transport, id_om))
            flash("Mission validée via CTM et clôturée avec succès !", "success")

        else:
            id_vehicule = request.form.get('id_vehicule')
            
            if id_vehicule == "nouveau":
                nouveau_matricule = request.form.get('nouveau_matricule')
                cursor.execute("""
                    INSERT INTO vehicule (matricule, type_vehicule, est_disponible) 
                    VALUES (%s, 'Non spécifié', FALSE)
                """, (nouveau_matricule,))
                id_vehicule = cursor.lastrowid
            else:
                cursor.execute("UPDATE vehicule SET est_disponible = FALSE WHERE id_vehicule = %s", (id_vehicule,))

            # Passe directement en 'Terminée' (plus de km_depart)
            cursor.execute("""
                UPDATE ordre_mission 
                SET moyen_transport = %s, id_vehicule = %s, statut = 'Terminée' 
                WHERE id_om = %s
            """, (moyen_transport, id_vehicule, id_om))
            flash("Véhicule assigné et mission clôturée avec succès !", "success")

        mysql.connection.commit()
        
    except Exception as e:
        mysql.connection.rollback()
        flash("Erreur lors de la validation.", "danger")
        print("Erreur SQL:", e)
    finally:
        cursor.close()

    return redirect(url_for('gestion_parc'))
# ==========================================
# ESPACE SERVICE FINANCIER
# ==========================================
@app.route('/finance')
def espace_finance():
    if 'loggedin' not in session:
        return redirect(url_for('dashboard'))

    # NOUVELLE SÉCURITÉ PLUS INTELLIGENTE
    role = session.get('role')
    service = session.get('service')
    
    acces_autorise = role in ['Admin', 'Directeur', 'Financière'] or (role == 'Chef de service' and service == 'Affaires Administratives et Financières')

    if not acces_autorise:
        flash("Accès refusé. Cette page est réservée au service financier.", "danger")
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # LA REQUÊTE INTELLIGENTE : 
        # On groupe par employé et on compte combien de missions "Terminées" il possède.
        cursor.execute("""
            SELECT u.doti, u.nom, u.prenom, u.grade, u.banque, u.rib, COUNT(om.id_om) as nb_missions
            FROM utilisateur u
            JOIN ordre_mission om ON u.doti = om.doti_employe
            WHERE om.statut = 'Terminée' and statut_financier = 'Non payé'
            GROUP BY u.doti, u.nom, u.prenom, u.grade, u.banque, u.rib
        """)
        employes_a_payer = cursor.fetchall()
        cursor.execute("""
            SELECT u.doti, u.nom, u.prenom, u.grade, u.banque, u.rib, COUNT(om.id_om) as nb_missions
            FROM utilisateur u
            JOIN ordre_mission om ON u.doti = om.doti_employe
            WHERE om.statut = 'Terminée' and statut_financier = 'payé'
            GROUP BY u.doti, u.nom, u.prenom, u.grade, u.banque, u.rib
                       
        """)
        employes_payes = cursor.fetchall()
    except Exception as e:
        print("Erreur SQL Finance :", e)
        employes_payes = []
    finally:
        cursor.close()
    return render_template('finance_dashboard.html', employes=employes_a_payer, employes_payes=employes_payes)

# ==========================================
# ACTION : MARQUER UN OM COMME PAYÉ
# ==========================================
@app.route('/marquer_paye_employe/<doti>')
def marquer_paye_employe(doti):
    if 'loggedin' not in session:
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor()
    try:
        # On met à jour TOUS les OM de cet employé qui sont encore "Non payé"
        cursor.execute("""
            UPDATE ordre_mission 
            SET statut_financier = 'Payé' 
            WHERE doti_employe = %s AND statut_financier = 'Non payé'
        """, (doti,))
        
        mysql.connection.commit()
        flash("Tous les remboursements de cet employé ont été validés avec succès !", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        print("Erreur paiement :", e)
        flash("Erreur lors de la mise à jour.", "danger")
    finally:
        cursor.close()

    return redirect(url_for('espace_finance'))

# ==========================================
# GÉNÉRER L'ÉTAT DES FRAIS (DOCUMENT IMPRIMABLE)
# ==========================================
@app.route('/finance/generer_etat/<doti>/<statut>')
def generer_etat_frais(doti, statut):
    # Sécurité
    role = session.get('role')
    service = session.get('service')
    acces_autorise = role in ['Admin', 'Directeur', 'Financière'] or (role == 'Chef de service' and service == 'Affaires Administratives et Financières')
    
    if not acces_autorise:
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # 1. Récupérer l'identité de l'employé
        cursor.execute("SELECT * FROM utilisateur WHERE doti = %s", (doti,))
        employe = cursor.fetchone()

        # 2. Récupérer toutes ses missions "Terminées"
        cursor.execute("""
            SELECT * FROM ordre_mission,utilisateur 
            WHERE doti_employe = %s AND statut = 'Terminée' AND statut_financier = %s AND ordre_mission.doti_employe = utilisateur.doti
            ORDER BY date_depart ASC
        """, (doti,statut))
        missions = cursor.fetchall()
        # 3. LES MATHÉMATIQUES
        # Le taux de base (à adapter selon le grade plus tard si besoin)
        echelle_employe = str(missions[0].get('echelle', '')).upper()

        # On détermine le taux de base selon l'échelle/grade
        if 'HE' in echelle_employe or 'HORS' in echelle_employe:
            taux_base = 100
        elif '11' in echelle_employe or 'PREMIER' in echelle_employe:
            taux_base = 80
        elif '10' in echelle_employe or 'DEUX' in echelle_employe:
            taux_base = 60
        else:
            taux_base = 60  # Valeur par défaut si le grade n'est pas reconnu        
        total_taux = 0
        total_montant = 0

        # On parcourt chaque mission pour calculer l'argent
        for mission in missions:
            # On récupère DIRECTEMENT la valeur depuis ta base de données
            # (On utilise 'or 0' au cas où la case serait vide dans la base)
            nombre_taux = int(mission['nombre_taux'] or 0)
            
            # Calcul du montant pour cette mission
            montant = nombre_taux * taux_base
            
            # On sauvegarde le montant dans le dictionnaire pour l'afficher en HTML
            mission['montant'] = montant
            
            # On ajoute aux grands totaux de la page
            total_taux += nombre_taux
            total_montant += montant
            # Traduction du montant total en lettres (en français)
        # S'il y a une erreur ou si le total est 0, on met un texte par défaut
        try:
            montant_lettres = num2words(total_montant, lang='fr').capitalize()
        except:
            montant_lettres = "Zéro"

        return render_template('etat_frais.html', 
                               employe=employe, 
                               missions=missions,
                               taux_base=taux_base, 
                               total_taux=total_taux, 
                               total_montant=total_montant,
                               montant_lettres=montant_lettres)
                               
    except Exception as e:
        print("Erreur Génération État:", e)
        flash("Erreur lors de la génération du document.", "danger")
        return redirect(url_for('espace_finance'))
    finally:
        cursor.close()

# ==========================================
# CHANGER LE MOT DE PASSE (PROFIL UTILISATEUR)
# ==========================================
@app.route('/changer_password', methods=['POST'])
def changer_password():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    doti_utilisateur = session.get('doti') 
    
    # On récupère les 3 champs du formulaire
    ancien_mdp = request.form.get('ancien_mdp')
    nouveau_mdp = request.form.get('nouveau_mdp')
    confirm_mdp = request.form.get('confirm_mdp')

    # Important : On utilise DictCursor pour lire facilement le résultat
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # 1. On va chercher le vrai mot de passe actuel dans la base de données
        cursor.execute("SELECT mot_de_passe FROM compte_acces WHERE doti = %s", (doti_utilisateur,))
        user = cursor.fetchone()

        # 2. On compare avec ce que l'utilisateur a tapé
        if not user or not check_password_hash(user['mot_de_passe'], ancien_mdp):
            flash("Erreur : L'ancien mot de passe est incorrect.", "danger")
            return redirect(request.referrer or url_for('dashboard'))

        # 3. On vérifie que les deux nouveaux mots de passe sont identiques
        if nouveau_mdp != confirm_mdp:
            flash("Erreur : Les nouveaux mots de passe ne correspondent pas.", "warning")
            return redirect(request.referrer or url_for('dashboard'))

        # 4. Si tout est bon, on met à jour !
        nouveau_mdp_hash=generate_password_hash(nouveau_mdp)
        cursor.execute("""
            UPDATE compte_acces 
            SET mot_de_passe = %s 
            WHERE doti = %s
        """, (nouveau_mdp_hash, doti_utilisateur))
        
        mysql.connection.commit()
        flash("Votre mot de passe a été modifié avec succès !", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        print("Erreur lors du changement de mot de passe :", e)
        flash("Une erreur est survenue lors de la modification.", "danger")
    finally:
        cursor.close()

    return redirect(request.referrer or url_for('dashboard'))

if __name__ == '__main__':
    # On met le port 7860 pour Hugging Face
    app.run(host='0.0.0.0', port=7860, debug=False)
