-- MySQL dump 10.13  Distrib 8.0.46, for Linux (x86_64)
--
-- Host: localhost    Database: pm2_dashboard
-- ------------------------------------------------------
-- Server version	8.0.46-0ubuntu0.24.04.3

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `clients`
--

DROP TABLE IF EXISTS `clients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `clients` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` varchar(500) DEFAULT NULL,
  `created_by` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_clients_name` (`name`),
  KEY `created_by` (`created_by`),
  KEY `ix_clients_id` (`id`),
  CONSTRAINT `clients_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `clients`
--

LOCK TABLES `clients` WRITE;
/*!40000 ALTER TABLE `clients` DISABLE KEYS */;
INSERT INTO `clients` VALUES (2,'Amaze',NULL,1,'2026-07-14 04:56:43'),(3,'India Insure',NULL,1,'2026-07-14 11:14:29'),(4,'Rag Pipeline Server',NULL,2,'2026-07-15 07:04:20'),(5,'Policyparivaar',NULL,2,'2026-07-15 07:14:28'),(6,'Rahee',NULL,2,'2026-07-15 07:31:55'),(9,'Evervent',NULL,2,'2026-07-15 07:40:41'),(10,'Dubbal',NULL,2,'2026-07-15 07:44:42'),(11,'Sorigin',NULL,2,'2026-07-15 11:23:51'),(13,'EB',NULL,2,'2026-07-15 11:30:27'),(14,'JIO',NULL,2,'2026-07-15 12:00:09');
/*!40000 ALTER TABLE `clients` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `process_log_audit`
--

DROP TABLE IF EXISTS `process_log_audit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `process_log_audit` (
  `id` int NOT NULL AUTO_INCREMENT,
  `server_id` int NOT NULL,
  `process_name` varchar(255) NOT NULL,
  `user_id` int DEFAULT NULL,
  `viewed_at` datetime DEFAULT NULL,
  `note` text,
  PRIMARY KEY (`id`),
  KEY `server_id` (`server_id`),
  KEY `user_id` (`user_id`),
  KEY `ix_process_log_audit_id` (`id`),
  CONSTRAINT `process_log_audit_ibfk_1` FOREIGN KEY (`server_id`) REFERENCES `servers` (`id`),
  CONSTRAINT `process_log_audit_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=74 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `process_log_audit`
--

LOCK TABLES `process_log_audit` WRITE;
/*!40000 ALTER TABLE `process_log_audit` DISABLE KEYS */;
INSERT INTO `process_log_audit` VALUES (1,1,'Dev Integrations Next',1,'2026-07-14 06:06:38',NULL),(2,1,'Dev Node Integrations',1,'2026-07-14 06:06:55',NULL),(3,1,'Dev POS Backend',1,'2026-07-14 06:07:46',NULL),(4,1,'Dev Node Integrations',1,'2026-07-14 06:08:04',NULL),(5,1,'Dev Node Integrations',1,'2026-07-14 06:09:03',NULL),(6,1,'Dev Node Integrations',1,'2026-07-14 06:10:13',NULL),(7,1,'Dev Node Integrations',1,'2026-07-14 06:18:29',NULL),(8,1,'Dev Node Integrations',1,'2026-07-14 06:19:25',NULL),(9,1,'Dev Node Integrations',1,'2026-07-14 06:40:52',NULL),(10,1,'Dev POS Backend',1,'2026-07-14 06:41:22',NULL),(11,1,'Dev POS Frontend',1,'2026-07-14 06:48:54',NULL),(12,1,'Dev Node Integrations',1,'2026-07-14 06:49:08',NULL),(13,1,'Dev Node Integrations',1,'2026-07-14 07:51:49',NULL),(14,1,'Dev Node Integrations',1,'2026-07-14 10:52:16',NULL),(15,1,'Dev Quotes',1,'2026-07-14 10:52:27',NULL),(16,1,'Dev POS Backend',1,'2026-07-14 10:52:37',NULL),(17,1,'Dev Integrations Next',1,'2026-07-14 10:53:57',NULL),(18,1,'Dev Node Integrations',1,'2026-07-14 10:54:06',NULL),(19,1,'Dev Node Integrations',1,'2026-07-14 10:54:20',NULL),(20,1,'Dev Node Integrations',1,'2026-07-14 10:59:02',NULL),(21,1,'Dev Node Integrations',1,'2026-07-14 11:01:12',NULL),(22,1,'Dev Integrations Next',1,'2026-07-14 11:01:25',NULL),(23,1,'Dev Pre-Quote-V2',1,'2026-07-14 11:01:33',NULL),(24,1,'Dev Node Integrations',1,'2026-07-14 11:01:40',NULL),(25,6,'Prod Node Integrations',1,'2026-07-14 11:12:26',NULL),(26,6,'Stg My Account',1,'2026-07-14 11:13:04',NULL),(27,7,'Dev Node Integrations',1,'2026-07-14 11:18:20',NULL),(28,8,'Prod POS Backend',1,'2026-07-14 11:20:04',NULL),(29,8,'Prod Node Integrations',1,'2026-07-14 11:20:15',NULL),(30,8,'Stg Node Integrations',1,'2026-07-14 11:21:12',NULL),(31,8,'Stg Node Integrations',1,'2026-07-14 11:22:05',NULL),(32,8,'Prod Node Integrations',1,'2026-07-14 11:22:20',NULL),(33,8,'Prod B2C',1,'2026-07-14 11:23:41',NULL),(34,8,'Prod Node Integrations',1,'2026-07-14 11:23:53',NULL),(35,8,'Prod Node Integrations',1,'2026-07-14 11:26:45',NULL),(36,8,'Prod Node Integrations',1,'2026-07-14 11:32:23',NULL),(37,8,'Prod Node Integrations',1,'2026-07-14 11:32:33',NULL),(38,8,'Prod Node Integrations',1,'2026-07-14 11:33:16',NULL),(39,8,'Prod Node Integrations',1,'2026-07-14 11:33:35',NULL),(40,7,' Dev Node Integration',1,'2026-07-14 11:35:46',NULL),(41,7,' Dev Node Integration',1,'2026-07-14 11:35:56',NULL),(42,8,'Prod Node Integrations',1,'2026-07-14 11:37:28',NULL),(43,8,'Prod Node Integrations',1,'2026-07-14 11:52:23',NULL),(44,1,'Dev Node Integrations',1,'2026-07-14 12:55:23',NULL),(45,8,'Prod Node Integrations',1,'2026-07-14 13:18:37',NULL),(46,8,'Prod Node Integrations',2,'2026-07-15 02:51:00',NULL),(47,8,'Prod POS Backend',2,'2026-07-15 02:51:15',NULL),(48,1,'Dev Node Integrations',2,'2026-07-15 02:51:27',NULL),(49,7,' Dev Node Integration',3,'2026-07-15 02:52:27',NULL),(50,6,'Stg Node Integrations',2,'2026-07-15 03:31:48',NULL),(51,8,'Prod Node Integrations',2,'2026-07-15 04:06:17',NULL),(52,1,'Dev Amaze frontened next',2,'2026-07-15 04:48:38',NULL),(53,1,'Dev Integrations Node',2,'2026-07-15 06:24:20',NULL),(54,9,'Dev Backend Admin',4,'2026-07-15 07:06:27',NULL),(55,9,'Dev Backend Admin',4,'2026-07-15 07:14:47',NULL),(56,10,'Dev QuotesV2',2,'2026-07-15 07:17:18',NULL),(57,10,'Dev Form V2',2,'2026-07-15 07:17:29',NULL),(58,10,'Dev Form V2',2,'2026-07-15 07:17:38',NULL),(59,10,'Dev QuotesV2',2,'2026-07-15 07:17:55',NULL),(60,10,'Dev QuotesV2',2,'2026-07-15 07:18:25',NULL),(61,10,'Dev Node Integrations',2,'2026-07-15 07:20:02',NULL),(62,10,'Dev B2C V2',2,'2026-07-15 07:20:07',NULL),(63,10,'Dev Node Integrations',2,'2026-07-15 07:26:35',NULL),(64,10,'Dev Node Integrations',2,'2026-07-15 07:26:39',NULL),(65,10,'Dev POS Frontend',2,'2026-07-15 07:27:08',NULL),(66,12,'Dev Pos Backend',2,'2026-07-15 07:33:05',NULL),(67,1,'Dev Integrations Node',2,'2026-07-15 09:11:24',NULL),(68,20,'Feature EB Backend',2,'2026-07-15 11:26:30',NULL),(69,30,'Prod Node Integrations',2,'2026-07-15 12:10:01',NULL),(70,36,'Prod POS Backend',2,'2026-07-15 12:21:55',NULL),(71,30,'Prod Agentic-Middleware',2,'2026-07-15 15:20:16',NULL),(72,31,'Prod Agentic-Middleware',2,'2026-07-15 15:20:35',NULL),(73,31,'Prod Node Integrations',2,'2026-07-15 15:20:50',NULL);
/*!40000 ALTER TABLE `process_log_audit` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `secret_reveal_audit`
--

DROP TABLE IF EXISTS `secret_reveal_audit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `secret_reveal_audit` (
  `id` int NOT NULL AUTO_INCREMENT,
  `repo_name` varchar(255) NOT NULL,
  `env_file_path` varchar(500) NOT NULL,
  `key_name` varchar(255) NOT NULL,
  `user_id` int DEFAULT NULL,
  `revealed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_secret_reveal_audit_id` (`id`),
  CONSTRAINT `secret_reveal_audit_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `secret_reveal_audit`
--

LOCK TABLES `secret_reveal_audit` WRITE;
/*!40000 ALTER TABLE `secret_reveal_audit` DISABLE KEYS */;
/*!40000 ALTER TABLE `secret_reveal_audit` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `servers`
--

DROP TABLE IF EXISTS `servers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `client_id` int NOT NULL,
  `name` varchar(255) NOT NULL,
  `ip_address` varchar(100) NOT NULL,
  `ssh_port` int DEFAULT NULL,
  `ssh_username` varchar(100) DEFAULT NULL,
  `ssh_password` varchar(500) DEFAULT NULL,
  `ssh_private_key_path` varchar(500) DEFAULT NULL,
  `environment` enum('Dev','Prod','Stg','Other') DEFAULT NULL,
  `tag` varchar(100) DEFAULT NULL,
  `created_by` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `pm2_bin_path` varchar(500) DEFAULT NULL,
  `pm2_path` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `client_id` (`client_id`),
  KEY `created_by` (`created_by`),
  KEY `ix_servers_id` (`id`),
  CONSTRAINT `servers_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`),
  CONSTRAINT `servers_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `servers`
--

LOCK TABLES `servers` WRITE;
/*!40000 ALTER TABLE `servers` DISABLE KEYS */;
INSERT INTO `servers` VALUES (1,2,'Amaze Dev','164.52.208.158',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Dev','Amaze Dev',1,'2026-07-14 04:58:01','/home/app/.nvm/versions/node/v22.22.0/bin/pm2','/home/app/.nvm/versions/node/v22.22.0/bin/pm2'),(6,2,'Amaze Prod','10.3.176.6',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,1,'2026-07-14 11:12:08',NULL,'/home/app/.nvm/versions/node/v22.21.0/bin/pm2'),(7,3,'India Insure Dev','216.48.186.13',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Dev',NULL,1,'2026-07-14 11:18:13',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(8,3,'India insure Prod & STG','10.7.128.7',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,1,'2026-07-14 11:19:34',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(9,4,'Rag Server','172.16.16.45',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Other',NULL,2,'2026-07-15 07:05:13',NULL,'/usr/bin/pm2'),(10,5,'PolicyParivaar Dev','164.52.215.179',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Dev',NULL,2,'2026-07-15 07:17:06',NULL,'/home/app/.nvm/versions/node/v22.21.0/bin/pm2'),(11,5,'PolicyParivaar Prod','10.6.108.9',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,2,'2026-07-15 07:31:17',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(12,6,'Rahee Dev','164.52.201.235',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Dev',NULL,2,'2026-07-15 07:32:57',NULL,'/home/app/.nvm/versions/node/v22.21.1/bin/pm2'),(13,6,'Rahee Prod ','10.11.138.7',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,2,'2026-07-15 07:34:52',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(15,10,'Dubbal Fullstack','164.52.214.8',2222,'app',NULL,'/home/jenkins/.ssh/id_rsa','Other',NULL,2,'2026-07-15 07:45:53',NULL,'/home/app/.nvm/versions/node/v22.21.0/bin/pm2'),(16,9,'Evervent-Deployments','164.52.215.248',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Other',NULL,2,'2026-07-15 07:49:15',NULL,'/home/app/.nvm/versions/node/v22.21.0/bin/pm2'),(17,9,'Evervent-Rowley2','216.48.180.28',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Other',NULL,2,'2026-07-15 07:50:34',NULL,'/usr/local/bin/pm2'),(18,9,'Prod Insureops and Vjinsurance','164.52.202.173',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Other',NULL,2,'2026-07-15 11:21:57',NULL,'/home/app/.nvm/versions/node/v22.21.0/bin/pm2'),(20,11,'Sorigin Prod','164.52.210.147',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,2,'2026-07-15 11:26:25',NULL,'/home/app/.nvm/versions/node/v22.22.2/bin/pm2'),(22,13,'Sorigin','164.52.210.147',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,2,'2026-07-15 11:31:28',NULL,'/home/app/.nvm/versions/node/v22.22.2/bin/pm2'),(23,13,'PolicySquare','216.48.191.38',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,2,'2026-07-15 11:32:11',NULL,'/home/app/.nvm/versions/node/v22.22.2/bin/pm2'),(26,14,'Jio Dev','20.193.171.167',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Dev','Jio Dev',2,'2026-07-15 12:03:30',NULL,'/home/app/.nvm/versions/node/v22.21.1/bin/pm2'),(28,14,'Jio Frontend 1','10.0.0.6',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod','Frontend App 1',2,'2026-07-15 12:05:44',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(29,14,'Jio Frontend 2','10.0.0.7',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod','Frontend App 2',2,'2026-07-15 12:07:24',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(30,14,'Jio Prod Backend 1','10.0.0.13',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod','Jio Prod Backend 1',2,'2026-07-15 12:09:52',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(31,14,'Jio Prod Backend 2','10.0.0.14',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod','Jio Prod Backend 2',2,'2026-07-15 12:13:58',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(32,14,'Jio STG Backend 1','10.0.0.4',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Stg',NULL,2,'2026-07-15 12:17:08',NULL,'/home/app/.nvm/versions/node/v22.21.0/bin/pm2'),(33,14,'Jio STG Backend 2','10.0.0.4',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Stg',NULL,2,'2026-07-15 12:17:54',NULL,'/home/app/.nvm/versions/node/v22.21.0/bin/pm2'),(34,14,'Jio Cron Server','10.0.0.15',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,2,'2026-07-15 12:18:50',NULL,'/home/app/.nvm/versions/node/v22.22.1/bin/pm2'),(35,14,'Jio Prod & STG POS 1','10.0.0.11',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Other',NULL,2,'2026-07-15 12:20:28',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2'),(36,14,'Jio Prod & STG POS 2','10.0.0.12',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','Prod',NULL,2,'2026-07-15 12:21:45',NULL,'/home/app/.nvm/versions/node/v22.20.0/bin/pm2');
/*!40000 ALTER TABLE `servers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ssl_certificates`
--

DROP TABLE IF EXISTS `ssl_certificates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ssl_certificates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `server_id` int NOT NULL,
  `domain_name` varchar(255) DEFAULT NULL,
  `config_file` varchar(500) DEFAULT NULL,
  `cert_path` varchar(500) DEFAULT NULL,
  `expiry_date` datetime DEFAULT NULL,
  `days_remaining` int DEFAULT NULL,
  `last_checked_at` datetime DEFAULT NULL,
  `last_check_error` varchar(1000) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `server_id` (`server_id`),
  KEY `ix_ssl_certificates_id` (`id`),
  CONSTRAINT `ssl_certificates_ibfk_1` FOREIGN KEY (`server_id`) REFERENCES `ssl_servers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ssl_certificates`
--

LOCK TABLES `ssl_certificates` WRITE;
/*!40000 ALTER TABLE `ssl_certificates` DISABLE KEYS */;
INSERT INTO `ssl_certificates` VALUES (1,1,'clp.bimastreet.com','/etc/nginx/conf.d/clp.conf','/etc/nginx/ssl/ssl.crt','2026-07-11 06:12:10',-5,'2026-07-15 07:59:52',NULL),(2,1,'devapi.bimastreet.com','/etc/nginx/conf.d/devapi.conf','/etc/letsencrypt/live/devapi.bimastreet.com/fullchain.pem','2026-10-11 06:34:37',87,'2026-07-15 07:59:52',NULL),(3,1,'devcrm.bimastreet.com','/etc/nginx/conf.d/devcrm.conf','/etc/letsencrypt/live/devcrm.bimastreet.com/fullchain.pem','2026-10-11 06:37:14',87,'2026-07-15 07:59:52',NULL),(4,1,'devproposal.bimastreet.com','/etc/nginx/conf.d/devproposals.conf','/etc/letsencrypt/live/devproposal.bimastreet.com/fullchain.pem','2026-10-11 06:41:41',87,'2026-07-15 07:59:52',NULL),(5,1,'devstatic.bimastreet.com','/etc/nginx/conf.d/devstatic.conf','/etc/nginx/ssl/ssl.crt','2026-07-11 06:12:10',-5,'2026-07-15 07:59:52',NULL),(6,1,'devapiv2.bimastreet.com','/etc/nginx/conf.d/devapiv2.conf','/etc/nginx/ssl/ssl.crt','2026-07-11 06:12:10',-5,'2026-07-15 07:59:52',NULL),(7,1,'devstrapi.bimastreet.com','/etc/nginx/conf.d/devstrapi.conf','/etc/letsencrypt/live/devstrapi.bimastreet.com/fullchain.pem','2026-10-11 06:44:22',87,'2026-07-15 07:59:52',NULL),(8,1,'devnodeapi.bimastreet.com','/etc/nginx/conf.d/devnode.conf','/etc/letsencrypt/live/devnodeapi.bimastreet.com/fullchain.pem','2026-10-11 06:38:40',87,'2026-07-15 07:59:52',NULL),(9,1,'devpos.bimastreet.com','/etc/nginx/conf.d/devpos.conf','/etc/letsencrypt/live/devpos.bimastreet.com/fullchain.pem','2026-10-11 06:39:21',87,'2026-07-15 07:59:52',NULL),(10,1,'devposv2api.bimastreet.com','/etc/nginx/conf.d/devposv2api.conf','/etc/letsencrypt/live/devposv2api.bimastreet.com/fullchain.pem','2026-10-11 06:40:10',87,'2026-07-15 07:59:52',NULL),(11,1,'dev.bimastreet.com','/etc/nginx/conf.d/dev.conf','/etc/letsencrypt/live/dev.bimastreet.com/fullchain.pem','2026-10-11 06:36:15',87,'2026-07-15 07:59:52',NULL),(12,1,'deverp.bimastreet.com','/etc/nginx/conf.d/deverp.conf','/etc/letsencrypt/live/deverp.bimastreet.com/fullchain.pem','2026-10-11 06:37:52',87,'2026-07-15 07:59:52',NULL),(13,1,'devadmin.bimastreet.com','/etc/nginx/conf.d/integrations_admin.conf','/etc/letsencrypt/live/devadmin.bimastreet.com/fullchain.pem','2026-09-27 08:52:38',74,'2026-07-15 07:59:52',NULL),(14,2,'api.bimastreet.com','/etc/nginx/conf.d/api.conf','/etc/letsencrypt/live/api.bimastreet.com/fullchain.pem','2026-10-11 05:03:07',87,'2026-07-15 07:59:52',NULL),(15,2,'stgapi.bimastreet.com','/etc/nginx/conf.d/stgapi.conf','/etc/letsencrypt/live/stgapi.bimastreet.com/fullchain.pem','2026-10-11 05:40:26',87,'2026-07-15 07:59:52',NULL),(16,2,'static.bimastreet.com','/etc/nginx/conf.d/static.conf','/etc/nginx/ssl/ssl.crt','2026-07-11 06:12:10',-5,'2026-07-15 07:59:52',NULL),(17,2,'crm.bimastreet.com','/etc/nginx/conf.d/crm.conf','/etc/letsencrypt/live/crm.bimastreet.com/fullchain.pem','2026-10-11 05:04:48',87,'2026-07-15 07:59:52',NULL),(18,2,'pos.bimastreet.com','/etc/nginx/conf.d/pos.conf','/etc/letsencrypt/live/pos.bimastreet.com/fullchain.pem','2026-10-11 05:39:29',87,'2026-07-15 07:59:52',NULL),(19,2,'stgnodeapi.bimastreet.com','/etc/nginx/conf.d/stgnode.conf','/etc/letsencrypt/live/stgnodeapi.bimastreet.com/fullchain.pem','2026-10-11 06:01:13',87,'2026-07-15 07:59:52',NULL),(20,2,'strapi.bimastreet.com','/etc/nginx/conf.d/strapi.conf','/etc/letsencrypt/live/strapi.bimastreet.com/fullchain.pem','2026-10-11 06:44:59',87,'2026-07-15 07:59:52',NULL),(21,2,'cms.bimastreet.com','/etc/nginx/conf.d/clp_strapi.conf','/etc/nginx/ssl/ssl.crt','2026-07-11 06:12:10',-5,'2026-07-15 07:59:52',NULL),(22,2,'stg.bimastreet.com','/etc/nginx/conf.d/stgb2c.conf','/etc/letsencrypt/live/stg.bimastreet.com/fullchain.pem','2026-10-11 05:41:29',87,'2026-07-15 07:59:52',NULL),(23,2,'stgcrm.bimastreet.com','/etc/nginx/conf.d/stgcrm.conf','/etc/letsencrypt/live/stgcrm.bimastreet.com/fullchain.pem','2026-10-11 05:42:18',87,'2026-07-15 07:59:52',NULL),(24,2,'stg.crm.bimastreet.com','/etc/nginx/conf.d/stgcrm.conf','/etc/nginx/ssl/ssl.crt','2026-07-11 06:12:10',-5,'2026-07-15 07:59:52',NULL),(25,2,'erp.bimastreet.com','/etc/nginx/conf.d/erp.conf','/etc/letsencrypt/live/erp.bimastreet.com/fullchain.pem','2026-10-11 05:37:59',87,'2026-07-15 07:59:52',NULL),(26,2,'admin.bimastreet.com','/etc/nginx/conf.d/admin.conf','/etc/letsencrypt/live/admin.bimastreet.com/fullchain.pem','2026-10-11 05:02:12',87,'2026-07-15 07:59:52',NULL),(27,2,'nodeapi.bimastreet.com','/etc/nginx/conf.d/node.conf','/etc/letsencrypt/live/nodeapi.bimastreet.com/fullchain.pem','2026-10-11 05:38:47',87,'2026-07-15 07:59:52',NULL),(28,2,'bimastreet.com','/etc/nginx/conf.d/b2c.conf','/etc/letsencrypt/live/bimastreet.com/fullchain.pem','2026-10-11 04:13:11',87,'2026-07-15 07:59:52',NULL),(29,2,'stgerp.bimastreet.com','/etc/nginx/conf.d/stgerp.conf','/etc/letsencrypt/live/stgerp.bimastreet.com/fullchain.pem','2026-10-11 05:54:18',87,'2026-07-15 07:59:52',NULL);
/*!40000 ALTER TABLE `ssl_certificates` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ssl_domains`
--

DROP TABLE IF EXISTS `ssl_domains`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ssl_domains` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `ip_address` varchar(100) NOT NULL,
  `ssh_port` int DEFAULT NULL,
  `ssh_username` varchar(100) DEFAULT NULL,
  `ssh_password` varchar(500) DEFAULT NULL,
  `ssh_private_key_path` varchar(500) DEFAULT NULL,
  `config_path` varchar(500) NOT NULL,
  `threshold_days` int DEFAULT NULL,
  `domain_name` varchar(255) DEFAULT NULL,
  `expiry_date` datetime DEFAULT NULL,
  `days_remaining` int DEFAULT NULL,
  `last_checked_at` datetime DEFAULT NULL,
  `last_check_error` varchar(1000) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ssl_domains_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ssl_domains`
--

LOCK TABLES `ssl_domains` WRITE;
/*!40000 ALTER TABLE `ssl_domains` DISABLE KEYS */;
INSERT INTO `ssl_domains` VALUES (1,'Amaze B2C','164.52.208.158',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','/etc/nginx/conf.d/dev.conf',7,NULL,NULL,NULL,'2026-07-15 04:12:33','openssl से certificate नहीं पढ़ा जा सका: Could not open file or uri for loading certificate from /etc/letsencrypt/live/dev.bimastreet.com/fullchain.pem\n4067DC244B730000:error:16000069:STORE routines:ossl_store_get0_loader_int:unregistered scheme:../crypto/store/store_register.c:237:scheme=file\n4067DC244B730000:error:8000000D:system library:file_open:Permission denied:../providers/implementations/storemgmt/file_store.c:267:calling stat(/etc/letsencrypt/live/dev.bimastreet.com/fullchain.pem)\nUnable to load certificate','2026-07-15 04:12:01');
/*!40000 ALTER TABLE `ssl_domains` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ssl_servers`
--

DROP TABLE IF EXISTS `ssl_servers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ssl_servers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `ip_address` varchar(100) NOT NULL,
  `ssh_port` int DEFAULT NULL,
  `ssh_username` varchar(100) DEFAULT NULL,
  `ssh_password` varchar(500) DEFAULT NULL,
  `ssh_private_key_path` varchar(500) DEFAULT NULL,
  `conf_dir` varchar(500) DEFAULT NULL,
  `threshold_days` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ssl_servers_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ssl_servers`
--

LOCK TABLES `ssl_servers` WRITE;
/*!40000 ALTER TABLE `ssl_servers` DISABLE KEYS */;
INSERT INTO `ssl_servers` VALUES (1,'Amaze Dev','164.52.208.158',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','/etc/nginx/conf.d',7,'2026-07-15 07:40:32'),(2,'Amaze Prod','10.3.176.6',22,'app',NULL,'/home/jenkins/.ssh/id_rsa','/etc/nginx/conf.d',7,'2026-07-15 07:51:46');
/*!40000 ALTER TABLE `ssl_servers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `hashed_password` varchar(255) NOT NULL,
  `role` enum('admin','developer','viewer') NOT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'admin','admin@example.com','$2b$12$hRGqUKKzXQooNFQvUraWZuh23tZUjy5Txv7yTFPYhYOAhcWf4WIle','admin',1,'2026-07-14 02:52:39'),(2,'anjali','anjali.kumari@evervent.in','$2b$12$IiR6Tl4MJEV1zecfu7..P.xp1F9d.wu2JrkWgzqgTzGUsPJpEznty','admin',1,'2026-07-15 02:50:24'),(3,'ramjeet','ramjeet.prajapati@evervent.in','$2b$12$Mim7rbpAF9gpxPgR28URPeDh7vrHxCehUEKuiplHD.uheEgtPugqe','admin',1,'2026-07-15 02:52:05'),(4,'paramjeet',NULL,'$2b$12$fi8tJWdXLCjvZGoycODZV.eABZFj6wb6YLc2RuLlC/YsG3wQUD7US','viewer',1,'2026-07-15 07:04:04');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-15 21:47:32
