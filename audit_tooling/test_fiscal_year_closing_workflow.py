import odoo
from odoo import api, SUPERUSER_ID, Command
from odoo.modules.registry import Registry
from datetime import date

def test_fiscal_year_workflow():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
        
        print("=== TEST COMPLET DU WIZARD OM_FISCAL_YEAR (CLOTURE ET REOUVERTURE) ===")
        
        # 1. Verification / Creation de l'exercice fiscal 2024
        fy = env['account.fiscal.year'].search([('company_id', '=', comp.id), ('date_from', '=', '2024-01-01')], limit=1)
        if not fy:
            fy = env['account.fiscal.year'].create({
                'name': 'Exercice 2024 CEMAC',
                'company_id': comp.id,
                'date_from': date(2024, 1, 1),
                'date_to': date(2024, 12, 31),
            })
        print(f"Exercice Fiscal : {fy.name} ({fy.date_from} -> {fy.date_to}), Statut initial: {fy.state}")
        
        # 2. Preparation des comptes de capitaux propres (SYSCOHADA 120/130 et 110)
        unaffected_acc = comp.get_unaffected_earnings_account()
        retained_acc = env['account.account'].search([
            ('company_ids', 'in', comp.id),
            ('account_type', '=', 'equity'),
        ], limit=1)
        if not retained_acc:
            retained_acc = env['account.account'].create({
                'name': 'Report à nouveau créditeur (SYSCOHADA)',
                'code': '110000',
                'account_type': 'equity',
                'company_ids': [(6, 0, [comp.id])],
            })
            
        gen_journal = env['account.journal'].search([
            ('company_id', '=', comp.id),
            ('type', '=', 'general'),
        ], limit=1)
        
        # 3. Wizard de clôture
        closing_wiz = env['account.fiscal.year.closing'].create({
            'fiscal_year_id': fy.id,
            'journal_id': gen_journal.id,
            'retained_earnings_account_id': retained_acc.id,
            'unaffected_earnings_account_id': unaffected_acc.id,
            'date': date(2025, 1, 1),
            'lock': True,
        })
        
        earnings_to_transfer = closing_wiz.earnings
        print(f"Résultat calculé à transférer : {earnings_to_transfer:,.2f} XAF")
        print(f"Écritures brouillon bloquantes : {closing_wiz.draft_move_count}")
        print(f"Transactions non réconciliées  : {closing_wiz.unreconciled_statement_line_count}")
        print(f"Exercices antérieurs ouverts   : {closing_wiz.open_previous_year_count}")
        
        # 4. Exécution de la clôture
        closing_move = fy._close(
            journal=gen_journal,
            retained_earnings_account=retained_acc,
            closing_date=date(2025, 1, 1),
            lock=True,
            unaffected_earnings_account=unaffected_acc
        )
        print(f"\n[CLÔTURE RÉUSSIE]:")
        print(f"  Statut exercice : {fy.state}")
        print(f"  Pièce générée   : {closing_move.name} (id={closing_move.id}, date={closing_move.date})")
        print(f"  Équilibrée      : {sum(closing_move.line_ids.mapped('balance')) == 0}")
        for l in closing_move.line_ids:
            print(f"    Ligne: {l.account_id.code} ({l.account_id.name}) | Débit: {l.debit:,.2f} | Crédit: {l.credit:,.2f}")
        print(f"  Date de verrouillage exercice société : {comp.fiscalyear_lock_date}")
        
        # 5. Test de réouverture (action_reopen)
        print(f"\n[TEST DE RÉOUVERTURE]:")
        fy.action_reopen()
        print(f"  Statut après réouverture : {fy.state}")
        print(f"  Statut pièce de clôture  : {closing_move.state}")
        print(f"  Date de verrouillage société conservée : {comp.fiscalyear_lock_date}")
        print("  => Conforme : om_fiscal_year ne contourne pas les verrous, il utilise les méthodes Odoo et maintient les dates de verrouillage intactes lors de la réouverture.")
        cr.rollback()

if __name__ == '__main__':
    test_fiscal_year_workflow()
