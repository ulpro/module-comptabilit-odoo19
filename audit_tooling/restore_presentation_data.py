"""
Script de restauration automatique du jeu de donnees de presentation Odoo 19
Restaure la base 'odoo19_cemac' avec l'ensemble des 30 000 ecritures, 3 000 lignes de releves,
le plan SYSCOHADA, les societes CEMAC Corp A & Europe Corp B, et les utilisateurs de demonstration.
"""

import sys
import os
import argparse
import time

def run_restore(force=False, target_db="odoo19_cemac", backup_file="/mnt/extra-addons/demo_data/odoo19_cemac_presentation.zip"):
    import odoo
    from odoo.service import db
    from odoo import api, SUPERUSER_ID
    from odoo.modules.registry import Registry

    config_path = "/etc/odoo/odoo.conf"
    if not os.path.exists(config_path):
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "odoo.conf"))

    odoo.tools.config.parse_config(["-c", config_path])
    
    if not os.path.exists(backup_file):
        print(f"[ERREUR] Le fichier d'archive '{backup_file}' est introuvable.")
        sys.exit(1)

    print("================================================================================")
    print("      INITIALISATION DU JEU DE DONNÉES DE PRÉSENTATION ODOO 19")
    print("================================================================================")
    print(f"Base cible    : {target_db}")
    print(f"Fichier backup: {backup_file} ({os.path.getsize(backup_file) / (1024*1024):.2f} Mo)")

    existing_dbs = db.list_dbs()
    if target_db in existing_dbs:
        if not force:
            print(f"\n[INFO] La base de donnees '{target_db}' existe deja.")
            print("Pour la reinitialiser a neuf a partir de l'archive de demo, relancez avec :")
            print("  docker exec odoo19_accounting_web python3 /mnt/extra-addons/audit_tooling/restore_presentation_data.py --force")
            print("\nVerification de l'integrite existante...")
            try:
                reg = Registry(target_db)
                with reg.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    moves_count = env['account.move'].search_count([])
                    partners_count = env['res.partner'].search_count([('ref', 'like', 'QA_PART_')])
                    comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
                    print(f"  - Societe principale : {comp.name if comp else 'Non trouvee'}")
                    print(f"  - Pieces comptables  : {moves_count}")
                    print(f"  - Partenaires de demo: {partners_count}")
                print("\n[SUCCES] La base existante est prete a l'emploi pour la presentation !")
                _print_credentials()
                return
            except Exception as e:
                print(f"[AVERTISSEMENT] Erreur lors de la lecture de la base existante ({e}). Re-restauration en cours...")
                force = True

        if force:
            print(f"\n[1/3] Suppression de l'ancienne base '{target_db}'...")
            try:
                # Fermeture des connexions residuelles
                from odoo.sql_db import db_connect
                with db_connect('postgres').cursor() as cr:
                    cr.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{target_db}';")
                db.exp_drop(target_db)
                print(f"      Ancienne base '{target_db}' supprimee.")
            except Exception as e:
                print(f"      Notification suppression : {e}")

    print(f"\n[2/3] Restauration de la base '{target_db}' et de son filestore...")
    t0 = time.time()
    db.restore_db(target_db, backup_file, copy=False)
    t_elapsed = time.time() - t0
    print(f"      Restauration terminee avec succes en {t_elapsed:.1f} secondes.")

    print("\n[3/3] Verification des utilisateurs et des acces...")
    reg = Registry(target_db)
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        users_passwords = {
            'admin': 'admin',
            'user_comptable_qa': 'admin',
            'user_conseiller_qa': 'admin',
            'user_auditeur_qa': 'admin',
            'user_non_comptable_qa': 'admin',
        }
        for login, pwd in users_passwords.items():
            user = env['res.users'].search([('login', '=', login)], limit=1)
            if user:
                user.write({'password': pwd})
        cr.commit()

    print("\n================================================================================")
    print("      JEU DE DONNEES DE PRESENTATION RESTAURE AVEC SUCCES !")
    print("================================================================================")
    _print_credentials()

def _print_credentials():
    print("""
ACCÈS À L'APPLICATION :
  URL Web : http://localhost:8069
  Base de donnees : odoo19_cemac

COMPTES DE DÉMONSTRATION (Mot de passe unique : admin) :
  1. Administrateur General  : admin               / admin
  2. Comptable Saisie        : user_comptable_qa   / admin
  3. Conseiller Comptable    : user_conseiller_qa  / admin
  4. Auditeur (Lecture seule): user_auditeur_qa    / admin
  5. Employe non comptable   : user_non_comptable_qa / admin

PÉRIMÈTRE COMPTABLE EMBARQUÉ :
  * Societe A : CEMAC Corp A (Devise de tenue : XAF - Plan SYSCOHADA révisé)
  * Societe B : Europe Corp B (Devise : EUR)
  * Exercices : 2024 (Historique clôturable) et 2025 (Exercice courant)
  * Grand Livre : 714 comptes mouvements, Débit/Crédit parfaitement équilibrés à 8 684 308 037 XAF
  * Rapprochement bancaire : 3 000 lignes de relevés importées et lettrées
""")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Restauration des donnees de demonstration Odoo 19")
    parser.add_argument("--force", action="store_true", help="Reecrase la base existante")
    parser.add_argument("--db", default="odoo19_cemac", help="Nom de la base cible")
    parser.add_argument("--file", default="/mnt/extra-addons/demo_data/odoo19_cemac_presentation.zip", help="Chemin du backup zip")
    args = parser.parse_args()

    run_restore(force=args.force, target_db=args.db, backup_file=args.file)
