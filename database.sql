CREATE TABLE utilisateur (
    doti VARCHAR(50) PRIMARY KEY,
    cin VARCHAR(20) UNIQUE,
    nom VARCHAR(50),
    prenom VARCHAR(50),
    grade VARCHAR(150),
    echelle VARCHAR(20)
);

-- 3. Table des accès (Uniquement pour les chefs/directeur)
CREATE TABLE compte_acces (
    id_acces INT PRIMARY KEY AUTO_INCREMENT,
    doti VARCHAR(50) UNIQUE,
    mot_de_passe VARCHAR(255) NOT NULL,
    role VARCHAR(30), 
    FOREIGN KEY (doti) REFERENCES utilisateur(doti) ON DELETE CASCADE
);

-- 4. Création de ton compte Administrateur de test
-- D'abord, on crée ton profil d'employé :
INSERT INTO utilisateur (doti, cin, nom, prenom, grade, echelle) 
VALUES ('ADMIN01', 'AB12345', 'Directeur', 'Test', 'Administrateur', 'Echelle 11'),
('zaki', 'CD67890', 'Zaki', 'Responsable', 'Responsable', 'Echelle 10'),
('elgh', 'EF13579', 'Elgh', 'Chef', 'Chef de Service', 'Echelle 9')
;

-- Ensuite, on te donne les clés pour te connecter :
INSERT INTO compte_acces (doti, mot_de_passe, role) 
VALUES ('ADMIN01', '1234', 'Admin'),
('zaki', '1111', 'responsable'),
('elgh', '2222', 'chef');




DROP TABLE IF EXISTS ordre_mission;

CREATE TABLE ordre_mission (
    id_om INT PRIMARY KEY AUTO_INCREMENT,
    numero_om VARCHAR(20),          -- Correspond à la case "1 / 2026"
    service_demandeur VARCHAR(150), -- Correspond à "Service ... C.P.S.I"
    doti_employe VARCHAR(50) NOT NULL,
    
    destination VARCHAR(150) NOT NULL,   -- "De se Rendre à"
    objet_mission TEXT NOT NULL,         -- "Objet de la Mission"
    itineraire VARCHAR(255),             -- "Itinéraire"
    
    date_depart DATE NOT NULL,
    heure_depart TIME,                   -- "Heure de Départ"
    date_retour DATE NOT NULL,
    heure_retour TIME,                   -- "Heure de Retour"
    
    moyen_transport VARCHAR(100) NOT NULL,
    immatriculation VARCHAR(50),         -- "M 234414" (Si véhicule de service)
    accompagne_de TEXT,                  -- "Accompagné de"
    
    date_creation DATE,                  -- "A Ouarzazate le :"
    statut VARCHAR(50) DEFAULT 'En attente de validation',
    
    FOREIGN KEY (doti_employe) REFERENCES utilisateur(doti) ON DELETE CASCADE
);
-- On ajoute les deux compteurs
ALTER TABLE ordre_mission 
ADD COLUMN km_depart INT AFTER moyen_transport,
ADD COLUMN km_retour INT AFTER km_depart;

-- Note : Tu as déjà un champ "kilometrage" dans ta table pour stocker la différence.
ALTER TABLE ordre_mission 
ADD COLUMN kilometrage INT AFTER km_retour;

-- 1. On supprime l'ancienne colonne texte "immatriculation"
ALTER TABLE ordre_mission DROP COLUMN immatriculation;

-- 2. On ajoute la colonne pour l'ID du véhicule
ALTER TABLE ordre_mission ADD COLUMN id_vehicule INT AFTER moyen_transport;

-- 3. On crée le lien officiel (Clé étrangère) entre les deux tables
ALTER TABLE ordre_mission ADD FOREIGN KEY (id_vehicule) REFERENCES vehicule(id_vehicule) ON DELETE SET NULL;