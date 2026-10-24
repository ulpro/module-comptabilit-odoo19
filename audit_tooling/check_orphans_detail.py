import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        cr.execute("""
            SELECT model, count(*)
            FROM ir_model_data
            WHERE (module LIKE 'om_%' OR module = 'accounting_pdf_reports')
              AND model NOT IN (SELECT model FROM ir_model)
            GROUP BY model
        """)
        print("Models in ir_model_data not in ir_model:")
        for r in cr.fetchall():
            print(f"  Model '{r[0]}' : {r[1]} records")
            
        cr.execute("""
            SELECT column_name FROM information_schema.columns WHERE table_name = 'ir_cron'
        """)
        print("Columns of ir_cron:", [r[0] for r in cr.fetchall()])
        
        cr.execute("""
            SELECT c.id, d.name, d.module
            FROM ir_cron c
            JOIN ir_model_data d ON d.model = 'ir.cron' AND d.res_id = c.id
            WHERE (d.module LIKE 'om_%' OR d.module = 'accounting_pdf_reports')
        """)
        print("Crons defined by OM modules:")
        for r in cr.fetchall():
            print(f"  Cron ID {r[0]}: {r[2]}.{r[1]}")

if __name__ == '__main__':
    check()
