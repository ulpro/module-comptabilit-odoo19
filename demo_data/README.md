# Jeu de Données de Démonstration & Présentation (Odoo 19)

Ce dossier contient l'archive complète de démonstration de la suite **Odoo Mates Accounting 19** configurée pour l'environnement **CEMAC (XAF / SYSCOHADA)** et **Multi-sociétés**.

---

## 1. Contenu de l'archive `odoo19_cemac_presentation.zip`

* **Format :** Archive native Odoo (`dump.sql` compressé + `filestore/` avec logos, pièces jointes et modèles QWeb).
* **Sociétés configurées :**
  * **CEMAC Corp A** : Devise principale **XAF**, Plan comptable révisé **SYSCOHADA**.
  * **Europe Corp B** : Devise principale **EUR**, Plan comptable international.
* **Volumétrie & Données de test :**
  * **+33 000 pièces comptables** réparties sur les exercices 2024 (historique) et 2025 (courant).
  * **3 000 lignes de relevés bancaires** importées et rapprochées.
  * **200 partenaires** tiers (Clients et Fournisseurs qualifiés CEMAC).
  * **Grand Livre équilibré à la perfection** : 8 684 308 037 XAF (Débit = Crédit, écart 0.00 XAF).
* **Utilisateurs & Profils de test préconfigurés :**
  * `admin` / `admin` (Administrateur global)
  * `user_comptable_qa` / `admin` (Comptable en saisie & traitement)
  * `user_conseiller_qa` / `admin` (Conseiller & Clôtures)
  * `user_auditeur_qa` / `admin` (Auditeur - Consultation & Rapports)
  * `user_non_comptable_qa` / `admin` (Employé)

---

## 2. Restauration Automatique

Pour restaurer cette base sur n'importe quelle machine disposant de Docker :
```bash
# Depuis la racine du projet :
docker compose up -d
docker exec odoo19_accounting_web python3 /mnt/extra-addons/audit_tooling/restore_presentation_data.py
```

Ou sous Windows en double-cliquant sur :
`start_presentation.bat`
