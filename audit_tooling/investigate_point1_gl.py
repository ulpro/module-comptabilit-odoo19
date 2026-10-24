import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def investigate_gl():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
        
        print("=== INVESTIGATION POINT 1 : GRAND LIVRE ===")
        print(f"Societe : {comp.name} (id={comp.id})")
        
        # 1. Verification de la base globale
        cr.execute("""
            SELECT count(*) as nb_lines, 
                   count(distinct move_id) as nb_moves,
                   COALESCE(SUM(debit), 0) as tot_debit,
                   COALESCE(SUM(credit), 0) as tot_credit
            FROM account_move_line
            WHERE company_id = %s AND parent_state = 'posted'
        """, (comp.id,))
        r_all = cr.dictfetchone()
        print(f"Total Base Globale (toutes dates confondues, posted) :")
        print(f"  Nb pieces : {r_all['nb_moves']}, Nb lignes : {r_all['nb_lines']}")
        print(f"  Debit : {r_all['tot_debit']:,.2f} | Credit : {r_all['tot_credit']:,.2f}")
        
        # 2. Decomposition par annee (2024 vs 2025)
        for yr in [2024, 2025]:
            cr.execute("""
                SELECT count(*) as nb_lines,
                       count(distinct move_id) as nb_moves,
                       COALESCE(SUM(debit), 0) as tot_debit,
                       COALESCE(SUM(credit), 0) as tot_credit,
                       COALESCE(SUM(debit - credit), 0) as balance
                FROM account_move_line
                WHERE company_id = %s AND parent_state = 'posted'
                  AND date >= %s AND date <= %s
            """, (comp.id, f"{yr}-01-01", f"{yr}-12-31"))
            r_yr = cr.dictfetchone()
            print(f"\nExercice {yr} (du 01/01/{yr} au 31/12/{yr}, posted) :")
            print(f"  Nb pieces : {r_yr['nb_moves']}, Nb lignes : {r_yr['nb_lines']}")
            print(f"  Debit : {r_yr['tot_debit']:,.2f} | Credit : {r_yr['tot_credit']:,.2f} | Solde : {r_yr['balance']:,.2f}")

        # 3. Pieces de cloture existantes
        cr.execute("""
            SELECT id, name, date, ref, state
            FROM account_move
            WHERE company_id = %s AND (ref ILIKE '%%cloture%%' OR ref ILIKE '%%closing%%' OR name ILIKE '%%MISC/2025%%' OR name ILIKE '%%MISC/2024%%')
        """, (comp.id,))
        closing_moves = cr.dictfetchall()
        print(f"\nPieces de cloture detectees en base : {len(closing_moves)}")
        for cm in closing_moves:
            print(f"  Piece ID {cm['id']}: {cm['name']} | Date: {cm['date']} | Ref: {cm['ref']} | State: {cm['state']}")
            cr.execute("SELECT account_id, debit, credit, name FROM account_move_line WHERE move_id = %s", (cm['id'],))
            for cml in cr.dictfetchall():
                acc = env['account.account'].browse(cml['account_id'])
                print(f"    Compte {acc.code} ({acc.name}): Debit={cml['debit']:,.2f}, Credit={cml['credit']:,.2f}, Libelle={cml['name']}")

        # 4. Simulation du wizard account.report.general.ledger
        rep_model = env['report.accounting_pdf_reports.report_general_ledger']
        
        # Test 4A: Exercice 2025 AVEC initial_balance = True
        wiz_2025_init = env['account.report.general.ledger'].with_company(comp).create({
            'date_from': '2025-01-01',
            'date_to': '2025-12-31',
            'target_move': 'posted',
            'initial_balance': True,
            'display_account': 'all',
        })
        act_2025_init = wiz_2025_init.with_context(active_model='account.report.general.ledger', active_ids=wiz_2025_init.ids, active_id=wiz_2025_init.id).check_report()
        res_2025_init = rep_model.with_context(active_model='account.report.general.ledger', active_ids=wiz_2025_init.ids)._get_report_values(wiz_2025_init.ids, data=act_2025_init.get('data'))
        
        tot_deb_2025_init = sum(a['debit'] for a in res_2025_init.get('Accounts', []))
        tot_crd_2025_init = sum(a['credit'] for a in res_2025_init.get('Accounts', []))
        print(f"\nWizard 2025 AVEC initial_balance=True :")
        print(f"  Total Debit  : {tot_deb_2025_init:,.2f}")
        print(f"  Total Credit : {tot_crd_2025_init:,.2f}")
        print(f"  Ecart (Debit - Credit) : {tot_deb_2025_init - tot_crd_2025_init:,.2f}")

        # Test 4B: Exercice 2025 SANS initial_balance
        wiz_2025_noinit = env['account.report.general.ledger'].with_company(comp).create({
            'date_from': '2025-01-01',
            'date_to': '2025-12-31',
            'target_move': 'posted',
            'initial_balance': False,
            'display_account': 'all',
        })
        act_2025_noinit = wiz_2025_noinit.with_context(active_model='account.report.general.ledger', active_ids=wiz_2025_noinit.ids, active_id=wiz_2025_noinit.id).check_report()
        res_2025_noinit = rep_model.with_context(active_model='account.report.general.ledger', active_ids=wiz_2025_noinit.ids)._get_report_values(wiz_2025_noinit.ids, data=act_2025_noinit.get('data'))
        
        tot_deb_2025_noinit = sum(a['debit'] for a in res_2025_noinit.get('Accounts', []))
        tot_crd_2025_noinit = sum(a['credit'] for a in res_2025_noinit.get('Accounts', []))
        print(f"\nWizard 2025 SANS initial_balance :")
        print(f"  Total Debit  : {tot_deb_2025_noinit:,.2f}")
        print(f"  Total Credit : {tot_crd_2025_noinit:,.2f}")
        print(f"  Ecart (Debit - Credit) : {tot_deb_2025_noinit - tot_crd_2025_noinit:,.2f}")

        # Test 4C: Totalite 2024-2025 (sans dates ou dates 2024-01-01 a 2025-12-31)
        wiz_all = env['account.report.general.ledger'].with_company(comp).create({
            'date_from': '2024-01-01',
            'date_to': '2025-12-31',
            'target_move': 'posted',
            'initial_balance': False,
            'display_account': 'all',
        })
        act_all = wiz_all.with_context(active_model='account.report.general.ledger', active_ids=wiz_all.ids, active_id=wiz_all.id).check_report()
        res_all = rep_model.with_context(active_model='account.report.general.ledger', active_ids=wiz_all.ids)._get_report_values(wiz_all.ids, data=act_all.get('data'))
        
        tot_deb_all = sum(a['debit'] for a in res_all.get('Accounts', []))
        tot_crd_all = sum(a['credit'] for a in res_all.get('Accounts', []))
        print(f"\nWizard Periode Complete 2024-2025 SANS initial_balance :")
        print(f"  Total Debit  : {tot_deb_all:,.2f}")
        print(f"  Total Credit : {tot_crd_all:,.2f}")
        print(f"  Ecart (Debit - Credit) : {tot_deb_all - tot_crd_all:,.2f}")

if __name__ == '__main__':
    investigate_gl()
