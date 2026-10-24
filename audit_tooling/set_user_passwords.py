import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def set_passwords():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        users_passwords = {
            'admin': 'admin',
            'user_comptable_qa': 'admin',
            'user_conseiller_qa': 'admin',
            'user_auditeur_qa': 'admin',
            'user_non_comptable_qa': 'admin',
        }
        
        print("=== DÉFINITION DES MOTS DE PASSE UTILISATEURS ===")
        for login, pwd in users_passwords.items():
            user = env['res.users'].search([('login', '=', login)], limit=1)
            if user:
                user.write({'password': pwd})
                print(f"Mot de passe défini pour {login} : '{pwd}'")
            else:
                print(f"Utilisateur non trouvé : {login}")
                
        cr.commit()
        print("\n=> Tous les mots de passe sont configurés avec succès !")

if __name__ == '__main__':
    set_passwords()
