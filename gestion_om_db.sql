-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : 127.0.0.1:3307
-- Généré le : dim. 03 mai 2026 à 13:30
-- Version du serveur : 10.4.32-MariaDB
-- Version de PHP : 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de données : `gestion_om_db`
--
CREATE DATABASE IF NOT EXISTS `gestion_om_db` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `gestion_om_db`;

-- --------------------------------------------------------

--
-- Structure de la table `compte_acces`
--

DROP TABLE IF EXISTS `compte_acces`;
CREATE TABLE IF NOT EXISTS `compte_acces` (
  `id_acces` int(11) NOT NULL AUTO_INCREMENT,
  `doti` varchar(50) DEFAULT NULL,
  `mot_de_passe` varchar(255) NOT NULL,
  `role` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id_acces`),
  UNIQUE KEY `doti` (`doti`)
) ENGINE=InnoDB AUTO_INCREMENT=122141 DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Déchargement des données de la table `compte_acces`
--

INSERT DELAYED IGNORE INTO `compte_acces` (`id_acces`, `doti`, `mot_de_passe`, `role`) VALUES
(122136, 'parc', '1111', 'Chef de parc'),
(122137, 'chef', '1111', 'Chef de service'),
(122138, 'ADMIN', '1111', 'Admin'),
(122139, 'fin', '1111', 'Financière'),
(122140, 'chef_fin', '1111', 'Chef de service');

-- --------------------------------------------------------

--
-- Structure de la table `ordre_mission`
--

DROP TABLE IF EXISTS `ordre_mission`;
CREATE TABLE IF NOT EXISTS `ordre_mission` (
  `id_om` int(11) NOT NULL AUTO_INCREMENT,
  `numero_om` varchar(20) NOT NULL,
  `service_demandeur` varchar(150) DEFAULT NULL,
  `doti_employe` varchar(50) NOT NULL,
  `destination` varchar(150) NOT NULL,
  `objet_mission` text NOT NULL,
  `itineraire` varchar(255) DEFAULT NULL,
  `date_depart` date NOT NULL,
  `heure_depart` time DEFAULT NULL,
  `date_retour` date NOT NULL,
  `heure_retour` time DEFAULT NULL,
  `nombre_taux` int(11) DEFAULT NULL,
  `moyen_transport` varchar(30) NOT NULL,
  `id_vehicule` int(11) DEFAULT NULL,
  `accompagne_de` text DEFAULT NULL,
  `date_creation` date DEFAULT NULL,
  `statut` varchar(50) DEFAULT 'En attente de validation',
  `statut_financier` varchar(20) DEFAULT 'Non payé',
  PRIMARY KEY (`id_om`),
  KEY `doti_employe` (`doti_employe`),
  KEY `id_vehicule` (`id_vehicule`)
) ENGINE=InnoDB AUTO_INCREMENT=44 DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Déchargement des données de la table `ordre_mission`
--

INSERT DELAYED IGNORE INTO `ordre_mission` (`id_om`, `numero_om`, `service_demandeur`, `doti_employe`, `destination`, `objet_mission`, `itineraire`, `date_depart`, `heure_depart`, `date_retour`, `heure_retour`, `nombre_taux`, `moyen_transport`, `id_vehicule`, `accompagne_de`, `date_creation`, `statut`, `statut_financier`) VALUES
(34, '1/2026', 'CPSI (Centre Provincial du Système d\'Information)', 'fct', 'Errachidia', 'Reunion', 'OUARZAZATE ERRACHIDIA OUARZAZATE', '2026-04-22', '13:00:00', '2026-04-22', '13:03:00', 1, 'Véhicule de service', NULL, 'AZAZAZ', '2026-04-22', 'Terminée', 'Payé'),
(35, '2/2026', 'CPSI (Centre Provincial du Système d\'Information)', 'fct', 'Errachidia', 'fortionK', 'OUAZ_ERR_OUAZ', '2026-04-22', '13:07:00', '2026-04-23', '23:00:00', 5, 'Véhicule de service', NULL, '', '2026-04-22', 'Terminée', 'Payé'),
(36, '1/2026', 'Affaires Administratives et Financières', 'fct', 'Errachidia', 'Reunion', 'OUAZ_ERR_OUAZ', '2026-04-23', '10:54:00', '2026-04-24', '23:00:00', 5, 'CTM', NULL, '2 stagires', '2026-04-23', 'Terminée', 'Payé'),
(37, '1/2026', 'Centre Provincial des Examens', 'chef', 'KELAA', 'lk', 'OZTE KELAA OZTE ', '2026-05-01', '08:00:00', '2026-05-08', '16:52:00', 23, 'CTM', NULL, '', '2026-04-23', 'Terminée', 'Payé'),
(39, '2/2026', 'Centre Provincial des Examens', 'fct', 'KELAA', 'LWRD', 'Ouarzazate-Kelaa mgouna-Ouarzazate', '2026-04-27', '12:44:00', '2026-04-29', '23:00:00', 8, 'Véhicule de service', 10, '', '2026-04-27', 'Terminée', 'Payé'),
(40, '3/2026', 'CPSI (Centre Provincial du Système d\'Information)', 'fct', 'KELAA', 'LWRD', 'Ouarzazate-Kelaa mgouna-Ouarzazate', '2026-04-30', '10:00:00', '2026-05-04', '23:00:00', 14, 'Véhicule de service', 10, '', '2026-04-30', 'Terminée', 'Payé'),
(41, '4/2026', 'CPSI (Centre Provincial du Système d\'Information)', 'fct', 'Errachidia', 'Reunion', 'OUAZ_ERR_OUAZ', '2026-05-02', '11:27:00', '2026-05-09', '23:00:00', 23, 'CTM', NULL, '', '2026-05-02', 'Terminée', 'Payé'),
(42, '2/2026', 'Affaires Administratives et Financières', 'fct', 'Errachidia', 'Reunion', 'OUAZ_ERR_OUAZ', '2026-05-02', '00:47:00', '2026-05-07', '23:00:00', 18, 'CTM', NULL, '', '2026-05-02', 'Terminée', 'Payé'),
(43, '1/2026', 'Constructions, Équipements et Patrimoine', 'chef', 'Errachidia', 'Reunion', 'OUAZ_ERR_OUAZ', '2026-05-23', '13:00:00', '2026-05-29', '23:00:00', 20, '', NULL, '', '2026-05-02', 'Attente Parc', 'Non payé');

-- --------------------------------------------------------

--
-- Structure de la table `utilisateur`
--

DROP TABLE IF EXISTS `utilisateur`;
CREATE TABLE IF NOT EXISTS `utilisateur` (
  `doti` varchar(50) NOT NULL,
  `cin` varchar(20) DEFAULT NULL,
  `nom` varchar(50) DEFAULT NULL,
  `prenom` varchar(50) DEFAULT NULL,
  `grade` varchar(150) DEFAULT NULL,
  `echelle` varchar(20) DEFAULT NULL,
  `service_affectation` varchar(150) DEFAULT NULL,
  `banque` varchar(100) DEFAULT NULL,
  `rib` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`doti`),
  UNIQUE KEY `cin` (`cin`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Déchargement des données de la table `utilisateur`
--

INSERT DELAYED IGNORE INTO `utilisateur` (`doti`, `cin`, `nom`, `prenom`, `grade`, `echelle`, `service_affectation`, `banque`, `rib`) VALUES
('ADMIN', 'P7777', 'Bahaj', 'moh', 'professeur', '1er', '', NULL, NULL),
('chef', 'ER1234', 'Elghazouani', 'mohamed', 'adjoint', '1er', 'CPSI (Centre Provincial du Système d\'Information)', NULL, NULL),
('chef_fin', 'Z22112', 'flan', 'bnflan', 'Chef de Service', '1er', 'Affaires Administratives et Financières', 'BARID BANK', '1112223332123456'),
('fct', 'EF2212', 'Sadiq', 'mohamed', 'spécialiste en réseau et sécurite', '1er', 'CPSI (Centre Provincial du Système d\'Information)', 'BANK CHAABI OZTE', '123456789123456679121212'),
('fin', 'E221122', 'ALAOUI', 'ALI', 'financiere', '1er', 'Affaires Administratives et Financières', 'atiijari tabount', '123456789123456789121212'),
('parc', 'CD67890', 'Zakaria', 'Elqabli', 'Chef de parc', '1er', 'Constructions, Équipements et Patrimoine', NULL, NULL);

-- --------------------------------------------------------

--
-- Structure de la table `vehicule`
--

DROP TABLE IF EXISTS `vehicule`;
CREATE TABLE IF NOT EXISTS `vehicule` (
  `id_vehicule` int(11) NOT NULL AUTO_INCREMENT,
  `matricule` varchar(50) NOT NULL,
  `type_vehicule` varchar(100) NOT NULL,
  `est_disponible` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_vehicule`),
  UNIQUE KEY `matricule` (`matricule`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Déchargement des données de la table `vehicule`
--

INSERT DELAYED IGNORE INTO `vehicule` (`id_vehicule`, `matricule`, `type_vehicule`, `est_disponible`) VALUES
(10, 'M 234414', 'dacia', 0);

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `compte_acces`
--
ALTER TABLE `compte_acces`
  ADD CONSTRAINT `compte_acces_ibfk_1` FOREIGN KEY (`doti`) REFERENCES `utilisateur` (`doti`) ON DELETE CASCADE;

--
-- Contraintes pour la table `ordre_mission`
--
ALTER TABLE `ordre_mission`
  ADD CONSTRAINT `ordre_mission_ibfk_1` FOREIGN KEY (`doti_employe`) REFERENCES `utilisateur` (`doti`) ON DELETE CASCADE,
  ADD CONSTRAINT `ordre_mission_ibfk_2` FOREIGN KEY (`id_vehicule`) REFERENCES `vehicule` (`id_vehicule`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
