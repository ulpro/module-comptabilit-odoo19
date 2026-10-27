# Guide de Déploiement et d'Installation Client — Suite Comptable Odoo 19

**Package :** Suite Comptable Complète Odoo 19 Community Edition  
**Module Chapeau :** `om_account_accountant` (Installation 1-Click)  
**Version :** 19.0.1.3.0 — Validée et Localisée en Français  
**Référentiel Cible :** SYSCOHADA Révisé / CEMAC (Devise FCFA/XAF) ou International (EUR/USD)

---

## 1. Vue d'Ensemble de la Suite Livrable

Cette suite logicielle transforme Odoo 19 Community en une solution de gestion financière et comptable complète, sans aucune dépendance envers la version Enterprise.

L'ensemble repose sur un **module chapeau unique (`om_account_accountant`)** qui orchestre et installe automatiquement les **17 modules métiers** suivants :

| Module Technique | Fonctionnalité Métier | Bénéfice Opérationnel Client |
| :--- | :--- | :--- |
| **`om_account_accountant`** | Module chapeau & tableau de bord | Activation en 1 clic de toute la suite avec menus unifiés. |
| **`accounting_pdf_reports`** | Rapports financiers légaux (PDF) | Bilan, Compte de résultat, Grand Livre, Balance, Balance âgée, TVA. |
| **`om_account_asset`** | Gestion des Immobilisations | Tableaux d'amortissement linéaires/dégressifs, dotations automatiques, cessions/rebuts. |
| **`om_account_budget`** | Gestion Budgétaire | Suivi budgétaire prévisionnel vs réalisé, calcul prorata temporis et dépassements. |
| **`om_fiscal_year`** | Clôture d'Exercice & Reports | Exercices fiscaux, clôture annuelle, génération automatique des reports à nouveau (AN) et verrouillages. |
| **`om_account_reconcile`** | Rapprochement Bancaire | Lettrage manuel et automatique des flux bancaires avec les factures et paiements. |
| **`om_account_daily_reports`** | Journaux Quotidiens | Livre de caisse, livre de banque et journalier de contrôle. |
| **`om_account_followup`** | Relances Clients & Recouvrement | Échéanciers, lettres de relance à plusieurs niveaux, gestion des litiges et promesses. |
| **`om_account_check_printing`** | Impression des Chèques | Modèles de chèques configurables, montants en lettres, protection anti-fraude par étoiles `***`. |
| **`om_recurring_payments`** | Écritures & Paiements Récurrents | Automatisation des loyers, abonnements et dotations périodiques. |
| **`om_account_cash_forecast`** | Prévisions de Trésorerie | Anticipation des flux financiers hebdomadaires et mensuels. |
| **`om_currency_revaluation`** | Réévaluation des Devises | Écarts de conversion latents au bilan et contrepassation automatique. |
| **`om_currency_rate_update`** | Cours de Devises Automatiques | Synchronisation planifiée des devises étrangères. |
| **`om_account_bank_statement_import`** | Import de Relevés Bancaires | Support natif des relevés CSV, CAMT.053, MT940 et OFX. |
| **`om_spreadsheet_account`** *(+ asset, budget, followup)* | Tableaux de Bord Analytiques | Feuilles de calcul dynamiques intégrées à Odoo. |

---

## 2. Pré-requis sur le Serveur du Client

Avant de copier les modules sur le serveur de votre client, assurez-vous des éléments suivants :

1. **Serveur Odoo 19 Community Edition** installé et opérationnel (Ubuntu 22.04 / 24.04 LTS ou conteneur Docker).
2. **Bibliothèques Python requises :**
   ```bash
   pip install reportlab openpyxl xlsxwriter pdfminer.six
   ```
3. **Moteur PDF Wkhtmltopdf :**
   * Version recommandée : `0.12.5` ou `0.12.6` avec support Qt (`wkhtmltopdf --version`).
   * Indispensable pour l'édition haute fidélité des rapports comptables et des chèques.

---

## 3. Procédure de Déploiement en 4 Étapes (Installation Clé en Main)

### Étape 1 : Copie des modules sur le serveur
Copiez l'ensemble du dossier contenant les 18 répertoires dans le dossier des extensions (*addons*) de votre client (par exemple `/opt/odoo/custom-addons/` ou le volume monté dans Docker) :
```bash
cp -r /chemin/vers/suite_comptable/* /opt/odoo/custom-addons/
chown -R odoo:odoo /opt/odoo/custom-addons/
```

### Étape 2 : Redémarrage d'Odoo
Redémarrez le service pour qu'Odoo référence les nouveaux modules :
```bash
sudo systemctl restart odoo
# Ou sous Docker :
docker restart <nom_du_conteneur_odoo>
```

### Étape 3 : Mise à jour de la liste des applications
1. Connectez-vous sur l'instance du client en tant qu'**Administrateur**.
2. Activez le **Mode Développeur** (*Paramètres ➔ Activer le mode développeur*).
3. Allez dans le menu **Applications**.
4. Dans la barre supérieure, cliquez sur **Mettre à jour la liste des applications** (*Update Apps List*) ➔ Validez.

### Étape 4 : Installation en 1 Clic
1. Toujours dans **Applications**, supprimez le filtre par défaut *« Applications »* dans la barre de recherche.
2. Recherchez : **`Odoo 19 Accounting Community`** (ou `om_account_accountant`).
3. Cliquez sur **Installer**.
4. **Constat :** Odoo installe automatiquement les 17 sous-modules en une seule opération. Tous les menus (*Comptabilité*, *Tableau de bord*, *Fournisseurs*, *Clients*, *Rapports*, *Analyses*) apparaissent directement dans l'interface, entièrement en français.

---

## 4. Checklist de Configuration Initiale chez le Client (Démarrage Immédiat)

Une fois l'installation achevée, effectuez ces 4 réglages de démarrage :

### 1. Devise de Référence de la Société
* Menu : **Comptabilité ➔ Configuration ➔ Paramètres**.
* Pour la zone CEMAC / UEMOA : sélectionner **FCFA (XAF ou XOF)** avec **0 décimale**.
* Pour les autres pays : sélectionner la devise nationale (EUR, USD, etc.).

### 2. Plan Comptable
* Si le client démarre sur une base vierge : installer le package comptable correspondant à sa juridiction fiscale (ex: *SYSCOHADA révisé* pour l'Afrique centrale et de l'ouest, ou *Plan Général Français*).
* Si le client a déjà des comptes : lier simplement les comptes de tiers (`401...`, `411...`) et de trésorerie (`521...`, `571...`).

### 3. Journaux Financiers et Modèles de Chèques
* Aller dans **Configuration ➔ Journaux comptables** :
  * Configurer le compte bancaire sur le journal **Banque**.
  * Si le client imprime ses chèques par imprimante : dans l'onglet *Paiements entrants/sortants*, activer le **Format de chèque configurable** et sélectionner le modèle A4 ou chèque feuille.

### 4. Attribution des Rôles et Droits d'Accès aux Collaborateurs
Grâce à la mise à jour des groupes intégrée dans la suite, l'attribution se fait en toute simplicité :
* Menu : **Paramètres ➔ Utilisateurs & Sociétés ➔ Utilisateurs** (ou via le menu **Groupes**).
* Repérez la ligne **Comptabilité** pour chaque employé :
  * **Directeur / DAF / Chef Comptable :** Sélectionner **`Conseiller / Administrateur`** (droits absolus, clôtures, réouvertures).
  * **Comptable Général :** Sélectionner **`Comptable`** (saisie OD, rapprochements, balances et états financiers).
  * **Aide-comptable / Facturier :** Sélectionner **`Facturation`** (saisie factures ventes/achats).
  * **Commissaire aux Comptes / Auditeur :** Sélectionner **`Auditeur (Lecture seule)`** (consultation intégrale sans modification possible).
  * **Commerciaux / Employés terrain :** Laisser **`Aucun`** (comptabilité invisible).

---

## 5. Garanties et Étanchéité de la Suite Livrée

* **Code Propre (Production Ready) :** Aucun fichier temporaire `.pyc`, aucun cache parasite `__pycache__`, fichier `.gitignore` inclus.
* **Localisation Française Intégrée :** Tous les modules critiques disposent de leur fichier de traduction [`fr.po`](file:///c:/Users/ulrich/Downloads/om_account_accountant-19.0.1.3.0/om_account_check_printing/i18n/fr.po) officiel.
* **Sécurité & Multi-Sociétés :** Respect strict des règles de cloisonnement des sociétés (`ir.rule`) et des droits d'accès (`ir.model.access`).
* **Zéro Fraude :** Verrouillage strict des exercices fiscaux après clôture (empêchant toute altération d'écritures antérieures) et protection par astérisques sur les pièces émises.
