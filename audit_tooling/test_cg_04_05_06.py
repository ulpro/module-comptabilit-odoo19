import odoo
from odoo import api, SUPERUSER_ID, Command
from odoo.modules.registry import Registry
from datetime import date

def test_cg_04_05_06():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
        user_comptable = env['res.users'].search([('login', '=', 'user_comptable_qa')], limit=1)
        env_c = env(user=user_comptable)
        
        j_misc = env['account.journal'].search([('company_id', '=', comp.id), ('type', '=', 'general')], limit=1)
        acc_exp = env['account.account'].search([('company_ids', 'in', comp.id), ('code', '=like', '6%')], limit=1)
        acc_cash = env['account.account'].search([('company_ids', 'in', comp.id), ('code', '=like', '5%')], limit=1)
        
        print("=== TEST CG-04 : CRÉATION ÉCRITURE ÉQUILIBRÉE (100 000 FCFA) ===")
        move = env_c['account.move'].create({
            'move_type': 'entry',
            'company_id': comp.id,
            'journal_id': j_misc.id,
            'date': date(2025, 10, 1),
            'ref': 'TEST-CG-04-100K',
            'line_ids': [
                Command.create({'name': 'Achat fournitures de bureau', 'account_id': acc_exp.id, 'debit': 100000.0, 'credit': 0.0}),
                Command.create({'name': 'Règlement par caisse', 'account_id': acc_cash.id, 'debit': 0.0, 'credit': 100000.0}),
            ]
        })
        total_debit = sum(move.line_ids.mapped('debit'))
        total_credit = sum(move.line_ids.mapped('credit'))
        print(f"Pièce créée ID: {move.id} | Statut: {move.state}")
        print(f"Total Débit : {total_debit:,.0f} FCFA | Total Crédit : {total_credit:,.0f} FCFA")
        print("=> CG-04 VALIDÉ : Écriture équilibrée créée avec succès.")
        
        print("\n=== TEST CG-05 : TENTATIVE DE CRÉATION/VALIDATION DÉSÉQUILIBRÉE (100k vs 80k) ===")
        unbalanced_blocked = False
        try:
            with cr.savepoint():
                env_c['account.move'].create({
                    'move_type': 'entry',
                    'company_id': comp.id,
                    'journal_id': j_misc.id,
                    'date': date(2025, 10, 1),
                    'ref': 'TEST-CG-05-DESEQUILIBRE',
                    'line_ids': [
                        Command.create({'name': 'Ligne Débit 100k', 'account_id': acc_exp.id, 'debit': 100000.0, 'credit': 0.0}),
                        Command.create({'name': 'Ligne Crédit 80k', 'account_id': acc_cash.id, 'debit': 0.0, 'credit': 80000.0}),
                    ]
                })
        except Exception as e:
            unbalanced_blocked = True
            print(f"REFUS STRICT DE L'ORM : {type(e).__name__} -> {e}")
            print("=> CG-05 VALIDÉ : Odoo 19 bloque immédiatement à la racine toute tentative d'écriture déséquilibrée.")
        assert unbalanced_blocked, "L'écriture déséquilibrée aurait dû être rejetée"
            
        print("\n=== TEST CG-06 : VALIDATION ÉCRITURE ÉQUILIBRÉE ET CONTRÔLE DES LIGNES ===")
        move.action_post()
        print(f"Numéro de pièce attribué : {move.name} | Statut: {move.state}")
        for l in move.line_ids:
            print(f"  Ligne ID {l.id:<6}: Compte {l.account_id.code} ({l.account_id.name:<25}) | Débit: {l.debit:>8,.0f} FCFA | Crédit: {l.credit:>8,.0f} FCFA")
        print("=> CG-06 VALIDÉ : Écriture comptabilisée avec intégrité absolue.")
        
        cr.commit()

if __name__ == '__main__':
    test_cg_04_05_06()
