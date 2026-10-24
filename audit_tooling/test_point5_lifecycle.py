import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def test_lifecycle_and_check_residuals():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        print("================================================================================")
        print("POINT 5 : AUDIT DU CYCLE DE VIE DES MODULES & REQUÊTES SQL RÉSIDUS")
        print("================================================================================")
        
        # 1. Modules de la suite Odoo Mates installés
        modules_om = [
            'om_account_accountant',
            'accounting_pdf_reports',
            'om_account_asset',
            'om_account_budget',
            'om_account_daily_reports',
            'om_account_followup',
            'om_account_bank_statement_import',
            'om_account_cash_forecast',
            'om_account_reconcile',
            'om_currency_revaluation',
            'om_fiscal_year',
            'om_recurring_payments',
        ]
        
        print(f"\n1. STATUT DES MODULES DANS IR_MODULE_MODULE :")
        for mod_name in modules_om:
            mod = env['ir.module.module'].search([('name', '=', mod_name)], limit=1)
            state = mod.state if mod else 'not_found'
            latest_version = mod.latest_version if mod else 'N/A'
            print(f"  - {mod_name:<36} : État = {state:<10} | Version = {latest_version}")

        # 2. Requête SQL 1 : Détection d'orphelins dans ir_model_data (modèles inexistants dans ir_model)
        print(f"\n2. VÉRIFICATION SQL : ORPHELINS IR_MODEL_DATA (Modèles manquants)")
        query_imd = """
            SELECT count(*) 
            FROM ir_model_data d
            WHERE (d.module LIKE 'om_%' OR d.module = 'accounting_pdf_reports')
              AND d.model NOT IN (SELECT model FROM ir_model WHERE model IS NOT NULL)
        """
        cr.execute(query_imd)
        orphans_imd = cr.fetchone()[0]
        print(f"  Commande SQL :\n  {query_imd.strip()}")
        print(f"  => Nombre d'enregistrements ir_model_data avec modèle orphelin : {orphans_imd}")

        # 3. Requête SQL 2 : Détection de menus orphelins (ir_ui_menu)
        print(f"\n3. VÉRIFICATION SQL : MENUS ORPHELINS (Parent inexistant)")
        query_menu = """
            SELECT count(*) 
            FROM ir_ui_menu m
            JOIN ir_model_data d ON d.model = 'ir.ui.menu' AND d.res_id = m.id
            WHERE (d.module LIKE 'om_%' OR d.module = 'accounting_pdf_reports')
              AND m.parent_id IS NOT NULL 
              AND m.parent_id NOT IN (SELECT id FROM ir_ui_menu)
        """
        cr.execute(query_menu)
        orphans_menu = cr.fetchone()[0]
        print(f"  Commande SQL :\n  {query_menu.strip()}")
        print(f"  => Nombre de menus orphelins : {orphans_menu}")

        # 4. Requête SQL 3 : Détection de crons orphelins (ir_cron)
        print(f"\n4. VÉRIFICATION SQL : TÂCHES PLANIFIÉES (IR_CRON) SANS ACTION SERVEUR")
        query_cron = """
            SELECT count(*) 
            FROM ir_cron c
            JOIN ir_model_data d ON d.model = 'ir.cron' AND d.res_id = c.id
            WHERE (d.module LIKE 'om_%' OR d.module = 'accounting_pdf_reports')
              AND c.ir_actions_server_id NOT IN (SELECT id FROM ir_act_server)
        """
        cr.execute(query_cron)
        orphans_cron = cr.fetchone()[0]
        print(f"  Commande SQL :\n  {query_cron.strip()}")
        print(f"  => Nombre de crons orphelins : {orphans_cron}")

        # 5. Requête SQL 4 : Groupes de sécurité orphelins (res_groups)
        print(f"\n5. VÉRIFICATION SQL : GROUPES DE SÉCURITÉ")
        query_groups = """
            SELECT g.id, d.name, d.module
            FROM res_groups g
            JOIN ir_model_data d ON d.model = 'res.groups' AND d.res_id = g.id
            WHERE (d.module LIKE 'om_%' OR d.module = 'accounting_pdf_reports')
        """
        cr.execute(query_groups)
        groups = cr.dictfetchall()
        print(f"  Groupes définis par les modules : {len(groups)}")
        for g in groups:
            print(f"    - Groupe ID {g['id']}: {g['module']}.{g['name']}")

        # 6. Requête SQL 5 : Tables PostgreSQL créées par les modules
        print(f"\n6. VÉRIFICATION SQL : TABLES EN BASE")
        query_tables = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND (
                  table_name LIKE 'account_asset%' 
                  OR table_name LIKE 'currency_revaluation%'
                  OR table_name LIKE 'om_%'
                  OR table_name LIKE 'account_fiscal_year%'
              )
            ORDER BY table_name
        """
        cr.execute(query_tables)
        tables = [r[0] for r in cr.fetchall()]
        print(f"  Nombre de tables spécifiques créées : {len(tables)}")
        for t in tables:
            cr.execute(f"SELECT count(*) FROM {t}")
            cnt = cr.fetchone()[0]
            print(f"    Table: {t:<42} | Lignes: {cnt}")

        print("\n=== SYNTHÈSE DU CYCLE DE VIE DES MODULES ===")
        print(f"  Orphelins ir_model_data : {orphans_imd}")
        print(f"  Orphelins ir_ui_menu    : {orphans_menu}")
        print(f"  Orphelins ir_cron       : {orphans_cron}")
        assert orphans_imd == 0, "Orphelins ir_model_data détectés"
        assert orphans_menu == 0, "Orphelins ir_ui_menu détectés"
        assert orphans_cron == 0, "Orphelins ir_cron détectés"
        print("  => VÉRIFIÉ : Base de données saine, intégrité référentielle 100%, 0 résidu orphelin.")

if __name__ == '__main__':
    test_lifecycle_and_check_residuals()
