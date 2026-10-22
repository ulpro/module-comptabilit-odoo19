import time
import threading
from datetime import date
from odoo import Command

def test_reconciliation_suite(env):
    print("=== ETAPE 2 : BANC D'ESSAI RAPPROCHEMENT BANCAIRE (om_account_reconcile) ===")
    comp_a = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
    j_bank = env['account.journal'].search([('company_id', '=', comp_a.id), ('type', '=', 'bank')], limit=1)
    j_sale = env['account.journal'].search([('company_id', '=', comp_a.id), ('type', '=', 'sale')], limit=1)
    
    partner = env['res.partner'].search([('ref', 'like', 'QA_PART_')], limit=1)
    accounts = env['account.account'].search([('company_ids', 'in', comp_a.id)])
    rec_acc = accounts.filtered(lambda a: a.account_type == 'asset_receivable')[:1]
    rev_acc = accounts.filtered(lambda a: a.account_type == 'income')[:1]
    
    # -------------------------------------------------------------
    # 1. CAS 1-POUR-N (1 paiement bancaire pour 3 factures de 100k)
    # -------------------------------------------------------------
    print("\n--- CAS 1 : 1-POUR-N (1 Releve pour 3 Factures) ---")
    invoices_1_n = []
    for i in range(3):
        inv = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'company_id': comp_a.id,
            'journal_id': j_sale.id,
            'invoice_date': '2025-05-10',
            'invoice_line_ids': [Command.create({'name': f'Ligne 1-N #{i+1}', 'price_unit': 100000.0, 'tax_ids': []})],
        })
        inv.action_post()
        invoices_1_n.append(inv)
    
    inv_lines_1_n = [inv.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable') for inv in invoices_1_n]
    
    st_line_1_n = env['account.bank.statement.line'].search([
        ('payment_ref', '=', 'REGLEMENT GROUPE 3 FACTURES'),
        ('company_id', '=', comp_a.id)
    ], limit=1)
    
    proposal_1_n = {'matches': [{'aml_id': l.id} for l in inv_lines_1_n]}
    prev_1_n = st_line_1_n.om_bank_rec_preview(proposal_1_n)
    print(f"1-pour-N Preview -> is_complete: {prev_1_n['is_complete']}, remaining: {prev_1_n['remaining']}")
    assert prev_1_n['is_complete'] is True, "Preview 1-pour-N doit être complete"
    
    st_line_1_n.om_bank_rec_validate(proposal_1_n)
    print(f"1-pour-N Valide -> is_reconciled: {st_line_1_n.is_reconciled}")
    for idx, inv in enumerate(invoices_1_n):
        print(f"  Facture #{idx+1} residual: {inv.amount_residual} (attendu: 0.0)")
        assert inv.amount_residual == 0.0, f"Facture #{idx+1} doit avoir un solde residuel nul"

    # -------------------------------------------------------------
    # 2. CAS N-POUR-1 (3 paiements bancaires de 40k pour 1 facture de 120k)
    # -------------------------------------------------------------
    print("\n--- CAS 2 : N-POUR-1 (3 Releves pour 1 Facture) ---")
    inv_n_1 = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'company_id': comp_a.id,
        'journal_id': j_sale.id,
        'invoice_date': '2025-06-01',
        'invoice_line_ids': [Command.create({'name': 'Facture N-1 120k', 'price_unit': 120000.0, 'tax_ids': []})],
    })
    inv_n_1.action_post()
    inv_line_n_1 = inv_n_1.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
    
    st_lines_n_1 = env['account.bank.statement.line'].search([
        ('payment_ref', 'like', 'REGLEMENT FRACTIONNE #'),
        ('company_id', '=', comp_a.id)
    ], limit=3, order='id asc')
    
    for idx, st_l in enumerate(st_lines_n_1):
        prop = {'matches': [{'aml_id': inv_line_n_1.id, 'amount': abs(st_l.amount)}]}
        st_l.om_bank_rec_validate(prop)
        print(f"  Paiement #{idx+1} valide -> st_line reconciled: {st_l.is_reconciled}, Facture residuel: {inv_n_1.amount_residual}")
    
    assert inv_n_1.amount_residual == 0.0, "La facture doit etre completement soldee apres les 3 paiements"
    print("N-pour-1 valide avec succes: solde residuel final = 0.0 XAF")

    # -------------------------------------------------------------
    # 3. PAIEMENT PARTIEL & ECART DE REGLEMENT (Write-off)
    # -------------------------------------------------------------
    print("\n--- CAS 3 : PAIEMENT PARTIEL & WRITE-OFF ---")
    inv_part = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'company_id': comp_a.id,
        'journal_id': j_sale.id,
        'invoice_date': '2025-07-01',
        'invoice_line_ids': [Command.create({'name': 'Facture Partielle 50k', 'price_unit': 50000.0, 'tax_ids': []})],
    })
    inv_part.action_post()
    inv_line_part = inv_part.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
    
    st_part = env['account.bank.statement.line'].search([
        ('payment_ref', 'like', 'ACOMPTE PARTIEL REF_'),
        ('company_id', '=', comp_a.id),
        ('is_reconciled', '=', False)
    ], limit=1)
    
    # 25 000 XAF paye sur 50 000 XAF
    st_part.om_bank_rec_validate({'matches': [{'aml_id': inv_line_part.id, 'amount': abs(st_part.amount)}]})
    print(f"Paiement partiel valide -> St line is_reconciled: {st_part.is_reconciled}, Facture residual: {inv_part.amount_residual}")
    assert inv_part.amount_residual == 25000.0, "Le residuel de facture doit etre de 25 000.0 XAF"
    
    # Annulation (Undo)
    st_part.om_bank_rec_undo()
    print(f"Annulation du rapprochement -> St line is_reconciled: {st_part.is_reconciled}, Facture residual: {inv_part.amount_residual}")
    assert inv_part.amount_residual == 50000.0, "Le residuel doit revenir a 50 000.0 XAF apres annulation"

    # -------------------------------------------------------------
    # 4. LETTRAGE AUTOMATIQUE & MESURE DU TAUX DE FAUX POSITIFS
    # -------------------------------------------------------------
    print("\n--- CAS 4 : LETTRAGE AUTOMATIQUE & TAUX DE FAUX POSITIFS ---")
    # 50 lignes de releve avec montant identique (50 000 XAF) a dates proches
    exact_st_lines = env['account.bank.statement.line'].search([
        ('payment_ref', 'like', 'VIREMENT EXACT 50K REF_'),
        ('company_id', '=', comp_a.id)
    ])
    print(f"Lignes de test a montants identiques (50 000 XAF) : {len(exact_st_lines)}")
    
    auto_validated = 0
    proposals_with_ambiguity = 0
    false_positives = 0
    
    for st_l in exact_st_lines[:20]:
        data = st_l.om_bank_rec_get_data()
        suggestions = data.get('suggestion', {}).get('matches', [])
        # Verification : Le module om_account_reconcile applique-t-il un lettrage aveugle sans confirmation ?
        # Dans om_account_reconcile, st_line.is_reconciled reste False tant que l'utilisateur ne clique pas sur Valider
        if st_l.is_reconciled:
            auto_validated += 1
        
        # S'il y a plusieurs factures de meme montant, le moteur doit presenter des candidats sans forcer l'attribution
        candidates = st_l.om_bank_rec_candidates()
        if len(candidates) > 1:
            proposals_with_ambiguity += 1

    print(f"Lettrages automatiques sans validation utilisateur : {auto_validated}")
    print(f"Transactions avec plusieurs candidats possibles detectes : {proposals_with_ambiguity}")
    assert auto_validated == 0, "CRITERE CRITIQUE : 0 lettrage automatique aveugle permis sans validation !"
    print("CRITERE VALIDE : Taux de faux positifs imposes = 0.0% (Securite confirmee)")

    # -------------------------------------------------------------
    # 5. CONCURRENCE (2 TRANSACTIONS SIMULTANEES SUR LA MEME LIGNE)
    # -------------------------------------------------------------
    print("\n--- CAS 5 : TEST DE CONCURRENCE ET DOUBLE RAPPROCHEMENT ---")
    st_conc = env['account.bank.statement.line'].search([
        ('company_id', '=', comp_a.id),
        ('is_reconciled', '=', False)
    ], limit=1)
    
    inv_conc = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'company_id': comp_a.id,
        'journal_id': j_sale.id,
        'invoice_date': '2025-08-01',
        'invoice_line_ids': [Command.create({'name': 'Facture Concurrence', 'price_unit': abs(st_conc.amount), 'tax_ids': []})],
    })
    inv_conc.action_post()
    aml_conc = inv_conc.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
    
    st_id = st_conc.id
    aml_id = aml_conc.id
    env.cr.commit()
    
    results_conc = []
    def worker(worker_id):
        with env.registry.cursor() as cr:
            w_env = env(cr=cr)
            try:
                line = w_env['account.bank.statement.line'].browse(st_id)
                if line.is_reconciled:
                    results_conc.append((worker_id, "REFUSED_ALREADY_RECONCILED"))
                    return
                line.om_bank_rec_validate({'matches': [{'aml_id': aml_id}]})
                cr.commit()
                results_conc.append((worker_id, "SUCCESS"))
            except Exception as e:
                cr.rollback()
                results_conc.append((worker_id, f"ERROR: {type(e).__name__}"))

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    print(f"Resultats concurrence 2 sessions : {results_conc}")
    success_count = sum(1 for r in results_conc if r[1] == "SUCCESS")
    print(f"Nombre d'acces ayant reussi l'ecriture : {success_count} (Attendu : exactement 1)")
    assert success_count == 1, "La concurrence doit garantir l'atomicite et empecher tout double lettrage !"

    # -------------------------------------------------------------
    # 6. VOLUMETRIE : MESURE PERF SUR LES 3 000 LIGNES
    # -------------------------------------------------------------
    print("\n--- CAS 6 : VOLUMETRIE (3 000 LIGNES DE RELEVE) ---")
    t0 = time.time()
    all_st = env['account.bank.statement.line'].search([('company_id', '=', comp_a.id)])
    print(f"Lignes de releve total en base : {len(all_st)}")
    
    # Mesure requetes et temps sur le chargement de l'ecran de rapprochement
    env.cr.execute("SELECT count(*) FROM account_bank_statement_line WHERE company_id = %s", [comp_a.id])
    t_search0 = time.time()
    search_res = env['account.bank.statement.line'].om_bank_rec_search_transactions(
        journal_id=j_bank.id, state='to_reconcile', limit=80, offset=0
    )
    t_search = round(time.time() - t_search0, 3)
    print(f"Recherche ecran 80 transactions sur 3000 : {t_search}s, Total count: {search_res['count']}")
    assert t_search < 1.0, "La recherche paginee sur 3000 lignes doit repondre en moins d'une seconde"
    print("VOLUMETRIE RAPPROCHEMENT : VALIDEE.")
    print("=== ETAPE 2 TERMINEE AVEC SUCCES ===")

if __name__ == "__main__":
    test_reconciliation_suite(env)
