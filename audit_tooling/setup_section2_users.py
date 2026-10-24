import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def setup_users():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
        
        # 1. Identifier les groupes disponibles
        group_user = env.ref('base.group_user')
        group_billing = env.ref('account.group_account_invoice')
        group_accountant = env.ref('account.group_account_user')
        group_advisor = env.ref('account.group_account_manager')
        group_readonly = env.ref('account.group_account_readonly', raise_if_not_found=False)
        
        # 2. Création / Mise à jour des rôles définis dans la section 2
        roles = {
            'comptable': {
                'name': 'Comptable (Saisie & Traitement)',
                'login': 'user_comptable_qa',
                'groups': [group_accountant.id, group_user.id]
            },
            'conseiller': {
                'name': 'Conseiller Comptable (Paramétrage & Clôture)',
                'login': 'user_conseiller_qa',
                'groups': [group_advisor.id, group_user.id]
            },
            'auditeur': {
                'name': 'Auditeur (Consultation & Rapports)',
                'login': 'user_auditeur_qa',
                'groups': [group_readonly.id if group_readonly else group_billing.id, group_user.id]
            },
            'non_comptable': {
                'name': 'Utilisateur Non Comptable (Ventes / Employé)',
                'login': 'user_non_comptable_qa',
                'groups': [group_user.id]
            }
        }
        
        print("=== CONFIGURATION DES RÔLES DE LA SECTION 2 ===")
        for role_key, role_data in roles.items():
            user = env['res.users'].search([('login', '=', role_data['login'])], limit=1)
            if not user:
                user = env['res.users'].create({
                    'name': role_data['name'],
                    'login': role_data['login'],
                    'email': f"{role_data['login']}@qa.test",
                    'company_id': comp.id,
                    'company_ids': [(6, 0, [comp.id])],
                    'group_ids': [(6, 0, role_data['groups'])],
                })
                print(f"[CRÉÉ] {role_data['name']} (login: {role_data['login']})")
            else:
                user.write({
                    'name': role_data['name'],
                    'company_id': comp.id,
                    'company_ids': [(6, 0, [comp.id])],
                    'group_ids': [(6, 0, role_data['groups'])],
                })
                print(f"[EXISTANT/MIS À JOUR] {role_data['name']} (login: {role_data['login']})")
                
        cr.commit()
        print("\n=> Rôles utilisateurs de la Section 2 créés et opérationnels avec succès !")

if __name__ == '__main__':
    setup_users()
