-- =====================================================================
-- Projet : Comparateur d'offres télécom FR
-- Fichier : data_model.sql
-- Description : Schéma de la BDD MySQL — à exécuter via phpMyAdmin
-- Version : 2.0 (ajout tables ARCEP + préparation Phase 3 cartographique)
-- =====================================================================

-- Création de la base
CREATE DATABASE IF NOT EXISTS telecom_comparator
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE telecom_comparator;

-- Drop dans l'ordre inverse des dépendances (FK)
DROP TABLE IF EXISTS prices_history;
DROP TABLE IF EXISTS coverage_fibre;
DROP TABLE IF EXISTS coverage_mobile;
DROP TABLE IF EXISTS offer_options;
DROP TABLE IF EXISTS options;
DROP TABLE IF EXISTS fibre_specs;
DROP TABLE IF EXISTS mobile_specs;
DROP TABLE IF EXISTS offers;
DROP TABLE IF EXISTS communes;
DROP TABLE IF EXISTS operators;

-- =====================================================================
-- TABLE : operators (les 4 opérateurs FR)
-- =====================================================================
CREATE TABLE operators (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(50)  NOT NULL UNIQUE,
  slug         VARCHAR(50)  NOT NULL UNIQUE,
  logo_url     VARCHAR(255),
  website_url  VARCHAR(255),
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : communes (référentiel INSEE — Phase 2 ARCEP, Phase 3 carte)
-- =====================================================================
CREATE TABLE communes (
  code_insee   VARCHAR(5) PRIMARY KEY,         -- code INSEE 5 caractères
  name         VARCHAR(100) NOT NULL,
  postal_code  VARCHAR(5) NOT NULL,
  department   VARCHAR(3) NOT NULL,            -- code département INSEE (01-95, 971...)
  region       VARCHAR(50),
  population   INT NULL,
  lat          DECIMAL(10,7) NULL,             -- latitude centroïde (Phase 3)
  lng          DECIMAL(10,7) NULL,             -- longitude centroïde (Phase 3)

  INDEX idx_postal (postal_code),
  INDEX idx_department (department),
  INDEX idx_name (name)
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : offers (commune fibre/mobile/bundle)
-- =====================================================================
CREATE TABLE offers (
  id                     INT AUTO_INCREMENT PRIMARY KEY,
  operator_id            INT NOT NULL,
  type                   ENUM('fibre', 'mobile', 'bundle') NOT NULL,
  name                   VARCHAR(255) NOT NULL,
  monthly_price          DECIMAL(6,2) NOT NULL,
  promo_price            DECIMAL(6,2) NULL,
  promo_duration_months  INT NULL,
  commitment_months      INT DEFAULT 0,
  setup_fee              DECIMAL(6,2) DEFAULT 0,
  source_url             VARCHAR(500) NOT NULL,
  score                  DECIMAL(3,1) NULL,
  is_active              BOOLEAN DEFAULT TRUE,
  first_seen_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_scraped_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_offers_operator
    FOREIGN KEY (operator_id) REFERENCES operators(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  UNIQUE KEY uk_offer_identity (operator_id, type, name),
  INDEX idx_operator_type (operator_id, type),
  INDEX idx_price (monthly_price),
  INDEX idx_score (score)
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : fibre_specs (1-1 avec offers)
-- =====================================================================
CREATE TABLE fibre_specs (
  offer_id           INT PRIMARY KEY,
  download_mbps      INT NOT NULL,
  upload_mbps        INT NOT NULL,
  technology         ENUM('FTTH', 'FTTLA', 'VDSL', 'ADSL') NOT NULL,
  wifi_standard      VARCHAR(20),
  has_tv             BOOLEAN DEFAULT FALSE,
  tv_channels_count  INT NULL,
  has_landline       BOOLEAN DEFAULT TRUE,

  CONSTRAINT fk_fibre_offer
    FOREIGN KEY (offer_id) REFERENCES offers(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : mobile_specs (1-1 avec offers)
-- =====================================================================
CREATE TABLE mobile_specs (
  offer_id          INT PRIMARY KEY,
  data_gb_france    INT NOT NULL,
  data_gb_eu        INT NULL,
  network_5g        BOOLEAN DEFAULT FALSE,
  calls_unlimited   BOOLEAN DEFAULT TRUE,
  sms_unlimited     BOOLEAN DEFAULT TRUE,

  CONSTRAINT fk_mobile_offer
    FOREIGN KEY (offer_id) REFERENCES offers(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : options (Netflix, Disney+, Cloud, etc.)
-- =====================================================================
CREATE TABLE options (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  name      VARCHAR(100) NOT NULL UNIQUE,
  category  ENUM('streaming', 'storage', 'tv', 'gaming', 'other') NOT NULL
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : offer_options (relation N-N)
-- =====================================================================
CREATE TABLE offer_options (
  offer_id     INT NOT NULL,
  option_id    INT NOT NULL,
  is_included  BOOLEAN NOT NULL DEFAULT TRUE,
  extra_price  DECIMAL(6,2) NULL,

  PRIMARY KEY (offer_id, option_id),

  CONSTRAINT fk_oo_offer
    FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
  CONSTRAINT fk_oo_option
    FOREIGN KEY (option_id) REFERENCES options(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : coverage_mobile (Phase 2 — données ARCEP "Mon Réseau Mobile")
-- =====================================================================
CREATE TABLE coverage_mobile (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  code_insee           VARCHAR(5) NOT NULL,
  operator_id          INT NOT NULL,
  has_4g               BOOLEAN DEFAULT FALSE,
  has_5g               BOOLEAN DEFAULT FALSE,
  coverage_4g_quality  ENUM('none', 'limited', 'good', 'very_good') DEFAULT 'none',
  coverage_5g_quality  ENUM('none', 'limited', 'good', 'very_good') DEFAULT 'none',
  has_5g_3500mhz       BOOLEAN DEFAULT FALSE,        -- 5G "premium" bande 3.5 GHz (n78)
  data_source          VARCHAR(100),                  -- ex: "ARCEP MRM 2026-Q1"
  captured_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uk_commune_operator (code_insee, operator_id),

  CONSTRAINT fk_cm_commune FOREIGN KEY (code_insee) REFERENCES communes(code_insee) ON DELETE CASCADE,
  CONSTRAINT fk_cm_operator FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE,

  INDEX idx_cm_commune (code_insee),
  INDEX idx_cm_operator (operator_id)
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : coverage_fibre (Phase 2 — Observatoire THD ARCEP)
-- =====================================================================
CREATE TABLE coverage_fibre (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  code_insee            VARCHAR(5) NOT NULL,
  operator_id           INT NULL,                     -- NULL = données agrégées
  locaux_total          INT,
  locaux_raccordables   INT,
  pct_couverture        DECIMAL(5,2),                 -- % de locaux raccordables
  data_source           VARCHAR(100),                 -- ex: "ARCEP THD 2026-Q1"
  captured_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_cf_commune FOREIGN KEY (code_insee) REFERENCES communes(code_insee) ON DELETE CASCADE,
  CONSTRAINT fk_cf_operator FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE,

  INDEX idx_cf_commune (code_insee),
  INDEX idx_cf_operator (operator_id)
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE : prices_history (séries temporelles de prix)
-- =====================================================================
CREATE TABLE prices_history (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  offer_id       INT NOT NULL,
  monthly_price  DECIMAL(6,2) NOT NULL,
  captured_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_ph_offer
    FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,

  INDEX idx_offer_time (offer_id, captured_at)
) ENGINE=InnoDB;

-- =====================================================================
-- DONNÉES DE BASE
-- =====================================================================
INSERT INTO operators (name, slug, website_url) VALUES
  ('Orange',    'orange',    'https://www.orange.fr'),
  ('SFR',       'sfr',       'https://www.sfr.fr'),
  ('Bouygues',  'bouygues',  'https://www.bouyguestelecom.fr'),
  ('Free',      'free',      'https://www.free.fr');

INSERT INTO options (name, category) VALUES
  ('Netflix',          'streaming'),
  ('Disney+',          'streaming'),
  ('Prime Video',      'streaming'),
  ('Canal+',           'streaming'),
  ('Cloud 100Go',      'storage'),
  ('Cloud 1To',        'storage'),
  ('TV 180 chaînes',   'tv'),
  ('Décodeur 4K',      'tv'),
  ('Xbox Game Pass',   'gaming');

-- Note : la table communes sera peuplée en Phase 2 via un seed depuis
-- le fichier officiel INSEE (code-postal-code-insee-2024.csv) ou data.gouv.fr
