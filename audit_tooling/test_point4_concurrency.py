import odoo
from odoo import api, SUPERUSER_ID, Command
from odoo.modules.registry import Registry
import threading
import time

def test_reconciliation_concurrency_two_cursors():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    
    # Étape 1 : Préparation des données sur un premier curseur principal
    with reg.cursor() as cr_setup:
        env = api.Environment(cr_setup, SUPERUSER_ID, {})
        comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
        partner = env['res.partner'].search([('company_id', 'in', (False, comp.id))], limit=1)
        j_sale = env['account.journal'].search([('company_id', '=', comp.id), ('type', '=', 'sale')], limit=1)
        j_bank = env['account.journal'].search([('company_id', '=', comp.id), ('type', '=', 'bank')], limit=1)
        
        # Trouver une ligne de relevé non lettrée
        st_line = env['account.bank.statement.line'].search([
            ('company_id', '=', comp.id),
            ('journal_id', '=', j_bank.id),
            ('is_reconciled', '=', False),
            ('amount', '>', 0)
        ], limit=1)
        assert st_line, "Ligne de relevé bancaire non lettrée requise"
        
        # Créer une facture client correspondante
        inv = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'company_id': comp.id,
            'journal_id': j_sale.id,
            'invoice_date': '2025-09-01',
            'invoice_line_ids': [Command.create({'name': 'Facture Concurrence 2 Curseurs', 'price_unit': abs(st_line.amount), 'tax_ids': []})],
        })
        inv.action_post()
        aml = inv.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        
        st_line_id = st_line.id
        aml_id = aml.id
        cr_setup.commit()
        print("=== POINT 4 : TEST DE CONCURRENCE AVEC DEUX CURSEURS POSTGRESQL DISTINCTS ===")
        print(f"Ligne de relevé ID : {st_line_id} (Montant: {st_line.amount:,.2f} XAF)")
        print(f"Ligne de facture ID : {aml_id} (Solde résiduel: {aml.amount_residual:,.2f} XAF)")

    # Étape 2 : Lancement concurrent sur DEUX connexions / curseurs PostgreSQL indépendants
    results = []
    barrier = threading.Barrier(2)

    def worker_transaction(worker_id):
        # Chaque worker acquiert son propre curseur PostgreSQL depuis le pool
        with reg.cursor() as cr_worker:
            w_env = api.Environment(cr_worker, SUPERUSER_ID, {})
            # Synchronisation exacte au départ
            barrier.wait()
            try:
                line = w_env['account.bank.statement.line'].browse(st_line_id)
                if line.is_reconciled:
                    results.append((worker_id, "REFUS_DEJA_LETTRE"))
                    return
                # Tentative de lettrage
                line.om_bank_rec_validate({'matches': [{'aml_id': aml_id}]})
                cr_worker.commit()
                results.append((worker_id, "SUCCES_LETTRE"))
            except Exception as e:
                cr_worker.rollback()
                results.append((worker_id, f"REFUS_EXCEPTION: {type(e).__name__} ({str(e)[:60]})"))

    t1 = threading.Thread(target=worker_transaction, args=(1,), name="Worker-1-Conn1")
    t2 = threading.Thread(target=worker_transaction, args=(2,), name="Worker-2-Conn2")
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"\nRésultats des deux transactions concurrentes :")
    for wid, status in results:
        print(f"  Connexion/Worker {wid} : {status}")

    # Étape 3 : Contrôle de cohérence sur un curseur de vérification
    with reg.cursor() as cr_verify:
        env_v = api.Environment(cr_verify, SUPERUSER_ID, {})
        line_check = env_v['account.bank.statement.line'].browse(st_line_id)
        aml_check = env_v['account.move.line'].browse(aml_id)
        
        # Vérification en base des partial reconciles
        cr_verify.execute("""
            SELECT count(*) 
            FROM account_partial_reconcile 
            WHERE debit_move_id = %s OR credit_move_id = %s
        """, (aml_id, aml_id))
        nb_partials = cr_verify.fetchone()[0]
        
        print(f"\nVérification intégrité PostgreSQL :")
        print(f"  Statut relevé is_reconciled : {line_check.is_reconciled}")
        print(f"  Résiduel facture : {aml_check.amount_residual:.2f} XAF")
        print(f"  Nombre d'enregistrements account_partial_reconcile : {nb_partials}")
        
        succes_count = sum(1 for r in results if r[1] == "SUCCES_LETTRE")
        assert succes_count == 1, f"Attendu exactement 1 succès, obtenu: {succes_count}"
        assert nb_partials == 1, f"Attendu exactement 1 partial reconcile (aucune double écriture), obtenu: {nb_partials}"
        assert line_check.is_reconciled is True, "Le relevé doit être lettré"
        assert aml_check.amount_residual == 0.0, "La créance doit être soldée à 0.0 XAF"
        print("  => VALIDÉ : Concurrence multi-transactions étanche, atomicité 100% garantie, 0 double écriture !")

if __name__ == '__main__':
    test_reconciliation_concurrency_two_cursors()
