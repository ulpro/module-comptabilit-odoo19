import odoo
from odoo import api, SUPERUSER_ID, Command
from odoo.modules.registry import Registry
from odoo.exceptions import UserError
from datetime import date

def test_lock_dates():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
        
        # 1. Users setup: Advisor (Manager) vs Standard User (Invoicing / Billing)
        admin = env.ref('base.user_admin')
        # Create standard user if not exists
        std_user = env['res.users'].search([('login', '=', 'qa_billing_user')], limit=1)
        if not std_user:
            std_user = env['res.users'].create({
                'name': 'QA Billing User (Simple)',
                'login': 'qa_billing_user',
                'email': 'qa_billing@example.com',
                'company_id': comp.id,
                'company_ids': [(6, 0, [comp.id])],
                'group_ids': [(6, 0, [
                    env.ref('base.group_user').id,
                    env.ref('account.group_account_invoice').id,  # Billing user
                ])],
            })
            
        partner = env['res.partner'].search([], limit=1)
        acc_rev = env['account.account'].search([('account_type', '=', 'income'), ('company_ids', 'in', comp.id)], limit=1)
        acc_rec = env['account.account'].search([('account_type', '=', 'asset_receivable'), ('company_ids', 'in', comp.id)], limit=1)
        sale_journal = env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', comp.id)], limit=1)
        
        lock_date = date(2024, 12, 31)
        
        print("=== BANC D'ESSAI EXHAUSTIF DES DATES DE VERROUILLAGE (ODOO 19) ===")
        print(f"Date de verrouillage testée : {lock_date}")
        
        operations = ['creation', 'post', 'write', 'cancel', 'reset_to_draft', 'unlink']
        lock_types = ['fiscalyear_lock_date', 'hard_lock_date', 'tax_lock_date', 'sale_lock_date']
        
        for lock_field in lock_types:
            print(f"\n--- TEST DU VERROU : {lock_field} ({lock_date}) ---")
            comp.sudo().write({
                'fiscalyear_lock_date': False,
                'hard_lock_date': False,
                'tax_lock_date': False,
                'sale_lock_date': False,
                'purchase_lock_date': False,
                lock_field: lock_date,
            })
            
            for user_label, test_user in [("Conseiller (Manager)", admin), ("Utilisateur Simple (Facturation)", std_user)]:
                user_env = env(user=test_user.id)
                print(f"  > Rôle : {user_label}")
                
                # Test 1: Création d'une facture au 15/12/2024 (période verrouillée)
                try:
                    move = user_env['account.move'].create({
                        'move_type': 'out_invoice',
                        'partner_id': partner.id,
                        'invoice_date': date(2024, 12, 15),
                        'date': date(2024, 12, 15),
                        'journal_id': sale_journal.id,
                        'invoice_line_ids': [Command.create({'name': 'QA Lock Test', 'price_unit': 1000.0, 'account_id': acc_rev.id})],
                    })
                    print(f"    - Création brouillon : AUTORISÉE (id={move.id}, date={move.date})")
                except Exception as e:
                    print(f"    - Création brouillon : REFUSÉE ({type(e).__name__}: {str(e)[:70]})")
                    move = None
                    
                if move:
                    # Test 2: Comptabilisation (action_post)
                    try:
                        move.action_post()
                        print(f"    - Comptabilisation   : AUTORISÉE (state={move.state}, date={move.date})")
                    except Exception as e:
                        print(f"    - Comptabilisation   : REFUSÉE ({type(e).__name__}: {str(e)[:70]})")
                        
                    # Test 3: Modification (write)
                    try:
                        move.write({'ref': 'REF MODIF QA'})
                        print(f"    - Modification (ref) : AUTORISÉE")
                    except Exception as e:
                        print(f"    - Modification (ref) : REFUSÉE ({type(e).__name__}: {str(e)[:70]})")
                        
                    # Test 4: Annulation (button_cancel)
                    try:
                        move.button_cancel()
                        print(f"    - Annulation         : AUTORISÉE (state={move.state})")
                    except Exception as e:
                        print(f"    - Annulation         : REFUSÉE ({type(e).__name__}: {str(e)[:70]})")
                        
                    # Test 5: Remise en brouillon (button_draft)
                    try:
                        move.button_draft()
                        print(f"    - Remise en brouillon: AUTORISÉE (state={move.state})")
                    except Exception as e:
                        print(f"    - Remise en brouillon: REFUSÉE ({type(e).__name__}: {str(e)[:70]})")
                        
                    # Test 6: Suppression (unlink)
                    try:
                        move.unlink()
                        print(f"    - Suppression        : AUTORISÉE")
                    except Exception as e:
                        print(f"    - Suppression        : REFUSÉE ({type(e).__name__}: {str(e)[:70]})")

        # Nettoyage des verrous
        comp.sudo().write({
            'fiscalyear_lock_date': False,
            'hard_lock_date': False,
            'tax_lock_date': False,
            'sale_lock_date': False,
            'purchase_lock_date': False,
        })
        cr.rollback()

if __name__ == '__main__':
    test_lock_dates()
