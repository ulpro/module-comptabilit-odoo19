# GUIDE DE CLONAGE, DÉPLOIEMENT & PRÉSENTATION
## Suite Comptabilité Odoo 19 (Odoo Mates Accounting 19.0.1.3.0)

Ce guide décrit la procédure pas à pas pour cloner ce projet sur un nouvel ordinateur (Windows, Linux ou macOS), initialiser les données de test en 1 clic et réussir votre présentation commerciale ou technique.

---

## 1. PRÉREQUIS SUR LE NOUVEAU PC

Avant de commencer sur le nouveau PC, assurez-vous d'avoir installé :
1. **Git** : [https://git-scm.com/](https://git-scm.com/)
2. **Docker Desktop** : [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
   * Sous Windows : Vérifiez que Docker Desktop est démarré et que le moteur WSL2 est actif.

---

## 2. ÉTAPE 1 : CLONER LE PROJET

Ouvrez un terminal (PowerShell, Command Prompt ou Bash) sur le nouveau PC et lancez :

```bash
git clone https://github.com/ulpro/module-comptabilit-odoo19.git
cd module-comptabilit-odoo19
```

> **Note :** L'archive complète des données de test (`demo_data/odoo19_cemac_presentation.zip`, ~9 Mo) est directement embarquée dans le dépôt Git.

---

## 3. ÉTAPE 2 : DÉMARRER ET RESTAURER LES DONNÉES (1-CLIC)

### Option A — Sous Windows (Méthode recommandée)
Double-cliquez simplement sur le fichier :
👉 **`start_presentation.bat`**

Le script effectue automatiquement :
1. Le démarrage des conteneurs Odoo 19 et PostgreSQL 16.
2. La détection et restauration complète de la base de données de test (`odoo19_cemac`) et de ses fichiers joints (`filestore`).
3. L'ouverture de l'application dans votre navigateur par défaut à l'adresse : **`http://localhost:8069`**.

---

### Option B — En ligne de commande (Windows, Linux, macOS)
```bash
# 1. Démarrer les conteneurs en arrière-plan
docker compose up -d

# 2. Restaurer et initialiser les données de démonstration
docker exec odoo19_accounting_web python3 /mnt/extra-addons/audit_tooling/restore_presentation_data.py
```

Rendez-vous ensuite sur : **[http://localhost:8069](http://localhost:8069)**.

---

## 4. IDENTIFIANTS DE CONNEXION POUR LA PRÉSENTATION

| Rôle | Identifiant (Login) | Mot de passe | Usage recommandé en présentation |
| :--- | :--- | :--- | :--- |
| **Administrateur Général** | `admin` | `admin` | Démonstration complète, paramétrages, modules et configuration avancée. |
| **Comptable (Saisie)** | `user_comptable_qa` | `admin` | Saisie de factures, lettrage bancaire, écritures d'inventaire. |
| **Conseiller Comptable** | `user_conseiller_qa` | `admin` | Clôture d'exercice, verrouillage des dates, validation financière. |
| **Auditeur (Lecture Seule)** | `user_auditeur_qa` | `admin` | Consultation des rapports financiers, grand livre, sans droit de modification. |

* **Mot de passe Master Odoo Database Manager :** `admin_secret_token`  
  Accessible via : `http://localhost:8069/web/database/manager`

---

## 5. DÉROULÉ RECOMMANDÉ POUR LA PRÉSENTATION (STORYLINE)

### 📌 Scénario 1 : Le Tableau de Bord Comptable et Multi-sociétés
1. Connectez-vous avec `admin` / `admin`.
2. Ouvrez le menu **Facturation / Comptabilité**.
3. Montrez le sélecteur multi-sociétés en haut à droite :
   * **CEMAC Corp A** : Devise principale **XAF (FCFA)**.
   * **Europe Corp B** : Devise principale **EUR**.
4. Présentez la vue d'ensemble avec les journaux de Factures Clients, Fournisseurs et Banque.

### 📌 Scénario 2 : Le Grand Livre & les Rapports Comptables PDF (Preuve de Robustesse)
1. Allez dans **Comptabilité > Rapports > Grand Livre (General Ledger)**.
2. Cochez **Initial Balance** pour l'exercice 2025.
3. Imprimez ou prévisualisez :
   * **714 comptes mouvementés**.
   * **Débit : 8 684 308 037 XAF** | **Crédit : 8 684 308 037 XAF**.
   * **Écart strictement nul (0.00 XAF)**.
4. Expliquez que le moteur SQL a été audité et patché contre les régressions d'Odoo 19 Community.

### 📌 Scénario 3 : Rapprochement et Relevés Bancaires
1. Dans le tableau de bord, cliquez sur le journal **Banque**.
2. Montrez les opérations importées (3 000 lignes de relevés bancaires traitées).
3. Ouvrez le widget de lettrage/rapprochement (`om_account_reconcile`) pour démontrer la vitesse d'association automatique facture <-> paiement.

### 📌 Scénario 4 : Prévisions de Trésorerie (Cash Forecast)
1. Allez dans le menu **Trésorerie / Cash Forecast**.
2. Démontrez la prise en compte des décaissements prévisionnels, des factures ouvertes et des paiements en cours de transit.

### 📌 Scénario 5 : Clôture Fiscale et Verrouillage des Dates
1. Allez dans **Configuration > Exercices Fiscaux** (`om_fiscal_year`).
2. Montrez l'exercice 2024 clôturé et les dates de verrouillage empêchant toute saisie rétroactive par un utilisateur non autorisé.

---

## 6. COMMENT RÉINITIALISER LES DONNÉES EN COURS DE DÉMONSTRATION ?

Si au cours de vos tests vous créez des factures ou modifiez les données et que vous souhaitez revenir à l'état propre d'origine pour une nouvelle présentation :

* Sous Windows : Double-cliquez sur **`restore_demo_data.bat`**.
* Ou dans un terminal :
  ```bash
  docker exec odoo19_accounting_web python3 /mnt/extra-addons/audit_tooling/restore_presentation_data.py --force
  ```
En **30 secondes**, la base de données est remise à neuf à son état parfait de référence !
