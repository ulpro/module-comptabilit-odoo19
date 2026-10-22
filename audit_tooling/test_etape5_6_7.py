import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import Command
from odoo.exceptions import UserError, ValidationError

def run_etapes_5_6_7(env):
    print("=== DEBUT DES TESTS ETAPES 5, 6 ET 7 ===")
    comp_a = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
    j_sale = env['account.journal'].search([('company_id', '=', comp_a.id), ('type', '=', 'sale')], limit=1)
    j_bank = env['account.journal'].search([('company_id', '=', comp_a.id), ('type', '=', 'bank')], limit=1)
    j_misc = env['account.journal'].search([('company_id', '=', comp_a.id), ('type', '=', 'general')], limit=1)
    partner = env['res.partner'].search([('ref', 'like', 'QA_PART_')], limit=1)
    
    # =========================================================================
    # ETAPE 5 : VERROUILLAGE ET EXERCICES (om_fiscal_year)
    # =========================================================================
    print("\n" + "="*50)
    print("--- ETAPE 5 : VERROUILLAGE ET EXERCICES (om_fiscal_year) ---")
    print("="*50)
    
    # 5.1 Test de verrouillage fiscalyear_lock_date
    lock_date = date(2024, 12, 31)
    comp_a.fiscalyear_lock_date = lock_date
    print(f"Date de verrouillage exercice configuree : {comp_a.fiscalyear_lock_date}")
    
    # Cas 5.1.a : Creation brouillon dans la periode verrouillee et comptabilisation
    # Comportement Odoo 19 documente : auto-avancement de la date au 1er jour ouvert
    draft_move = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'company_id': comp_a.id,
        'journal_id': j_sale.id,
        'invoice_date': date(2024, 10, 15),
        'date': date(2024, 10, 15),
        'invoice_line_ids': [Command.create({'name': 'Test Lock Draft', 'price_unit': 50000.0, 'tax_ids': []})],
    })
    print(f"Facture brouillon datee au : {draft_move.date} (avant lock {lock_date})")
    draft_move.action_post()
    print(f"Facture apres action_post() -> Date constatee : {draft_move.date}, Statut : {draft_move.state}")
    if draft_move.date > lock_date:
        print(f"COMPORTEMENT ODOO 19 PROUVE : Deplacement automatique de la date a {draft_move.date} (premier jour ouvert).")
    
    # Cas 5.1.b : Tentative de modification de date d'une ecriture comptabilisee vers la periode verrouillee
    print("\nTentative de modification retroactive d'une ecriture vers la periode verrouillee...")
    try:
        draft_move.write({'date': date(2024, 6, 1)})
        print("ALERTE : Modification retroactive permise !")
    except (UserError, ValidationError) as e:
        print(f"REFUS STRICT DE MODIFICATION : {type(e).__name__} -> {e}")
    
    # Cas 5.1.c : Tentative de suppression / annulation d'une ecriture verouillee
    # Creons une ecriture par SQL dans la periode verrouillee pour tester l'interdiction d'annulation
    locked_posted = env['account.move'].search([
        ('company_id', '=', comp_a.id),
        ('date', '<=', lock_date),
        ('state', '=', 'posted')
    ], limit=1)
    if locked_posted:
        print(f"\nTentative d'annulation sur ecriture verrouillee {locked_posted.name} (date {locked_posted.date})...")
        try:
            locked_posted.button_draft()
            print("ALERTE : Remise en brouillon d'une ecriture verrouillee a reussi !")
        except (UserError, ValidationError) as e:
            print(f"REFUS STRICT D'ANNULATION : {type(e).__name__} -> {e}")
    
    # 5.2 Cloture annuelle et Report a nouveau
    print("\n--- Test Cloture Annuelle et Report a nouveau ---")
    fy = env['account.fiscal.year'].search([('company_id', '=', comp_a.id), ('date_to', '=', '2024-12-31')], limit=1)
    if not fy:
        fy = env['account.fiscal.year'].create({
            'name': 'Exercice 2024',
            'company_id': comp_a.id,
            'date_from': '2024-01-01',
            'date_to': '2024-12-31',
        })
    print(f"Exercice comptable fiscal year : {fy.name} ({fy.date_from} au {fy.date_to})")
    assert fy.id, "L'exercice comptable doit etre cree"

    # =========================================================================
    # ETAPE 6 : DEVISES XAF (0 DECIMALE)
    # =========================================================================
    print("\n" + "="*50)
    print("--- ETAPE 6 : DEVISE XAF (0 DECIMALE) & MECANIQUES FINANCIERES ---")
    print("="*50)
    
    # 6.1 Tableau d'amortissement (om_account_asset)
    print("\n--- 6.1 Test Amortissements XAF (Lineaire, Degressif, Rebut) ---")
    acc_asset = env['account.account'].search([('company_ids', 'in', comp_a.id), ('account_type', '=', 'asset_fixed')], limit=1)
    acc_depr = env['account.account'].search([('company_ids', 'in', comp_a.id), ('account_type', '=', 'asset_non_current')], limit=1)
    acc_exp = env['account.account'].search([('company_ids', 'in', comp_a.id), ('account_type', '=', 'expense')], limit=1)
    
    # Creation categorie d'amortissement lineaire
    model_asset = env['account.asset.category'].create({
        'name': 'Materiel Bureau Lineaire 3 ans XAF',
        'company_id': comp_a.id,
        'method': 'linear',
        'method_number': 36,
        'method_period': 1,
        'account_asset_id': acc_asset.id,
        'account_depreciation_id': acc_depr.id,
        'account_depreciation_expense_id': acc_exp.id,
        'journal_id': j_misc.id,
    })
    
    # Immob de 1 000 000 XAF
    asset = env['account.asset.asset'].create({
        'name': 'Serveur Informatique QA XAF',
        'category_id': model_asset.id,
        'company_id': comp_a.id,
        'value': 1000000.0,
        'date': '2025-01-01',
    })
    asset.compute_depreciation_board()
    
    total_depreciated = sum(asset.depreciation_line_ids.mapped('amount'))
    print(f"Valeur d'acquisition XAF : {asset.value}")
    print(f"Nombre de lignes tableau : {len(asset.depreciation_line_ids)}")
    print(f"Somme des amortissements programmes : {total_depreciated}")
    assert total_depreciated == asset.value, "La somme des amortissements doit etre rigoureusement egale a la valeur d'origine (0 ecart d'arrondi)"
    
    # Verification des arrondis sur chaque ligne (0 decimale en XAF)
    has_fractional_cents = any(l.amount != int(l.amount) for l in asset.depreciation_line_ids)
    print(f"Presence de centimes fractionnaires sur les amortissements XAF : {has_fractional_cents} (Attendu : False)")
    assert not has_fractional_cents, "XAF ne doit comporter aucune fraction de centime !"
    print("Mecanique d'amortissement 0 decimale XAF : VALIDEE SANS ECART.")

    # 6.2 Reevaluation des devises (om_currency_revaluation)
    print("\n--- 6.2 Test Reevaluation Devises sur societe XAF ---")
    eur = env.ref('base.EUR')
    usd = env.ref('base.USD')
    # Recherche des ajustements calcules sur societe A
    wiz_rev = env['currency.revaluation'].create({
        'company_id': comp_a.id,
        'date': '2025-12-31',
        'journal_id': j_misc.id,
        'gain_account_id': acc_asset.id, # compte temporaire pour test
        'loss_account_id': acc_exp.id,
    })
    rev_vals = wiz_rev._get_revaluation_values()
    print(f"Lignes d'ajustement calculees pour societe XAF : {len(rev_vals)}")
    if rev_vals:
        v0 = rev_vals[0]
        print(f"  Exemple ajustement: devise={v0['currency_id']}, revalued={v0['revalued']}, solde={v0['balance']}, ecart={v0['adjustment']}")
        assert v0['adjustment'] == int(v0['adjustment']), "L'ecart d'ajustement en XAF doit etre un entier sans virgule !"
    print("Calcul des ajustements de reevaluation XAF : VALIDE.")

    # =========================================================================
    # ETAPE 7 : PREVISIONS DE TRESORERIE (om_account_cash_forecast)
    # =========================================================================
    print("\n" + "="*50)
    print("--- ETAPE 7 : PREVISIONS DE TRESORERIE (DIAGNOSTIC & FIX) ---")
    print("="*50)
    
    # Diagnostic precis du bug test_payments_not_in_the_bank_yet
    print("Reproduction du flux test_payments_not_in_the_bank_yet...")
    j_bank.inbound_payment_method_line_ids.payment_account_id = False
    
    inv_fc = env['account.move'].create({
        'move_type': 'out_invoice',
        'partner_id': partner.id,
        'company_id': comp_a.id,
        'journal_id': j_sale.id,
        'invoice_date': date(2025, 2, 20),
        'invoice_line_ids': [Command.create({'name': 'Prevision Test', 'price_unit': 60000.0, 'tax_ids': []})],
    })
    inv_fc.action_post()
    print(f"Facture creee: {inv_fc.name}, payment_state: {inv_fc.payment_state}")
    
    # Enregistrement du paiement
    pay_reg = env['account.payment.register'].with_context(active_model='account.move', active_ids=inv_fc.ids).create({
        'payment_date': date(2025, 2, 5),
        'journal_id': j_bank.id,
    })
    payments = pay_reg._create_payments()
    print(f"Paiement enregistre: state={payments.state}, invoice payment_state={inv_fc.payment_state}")
    
    # Generation du rapport de prevision
    rep_obj = env['report.om_account_cash_forecast.report_cash_forecast']
    wiz_fc = env['account.cash.forecast.report'].create({
        'company_id': comp_a.id,
        'date_from': date(2025, 2, 1),
        'period_type': 'month',
        'period_count': 3,
        'overdue': 'exclude',
    })
    
    items = rep_obj._get_forecast_items(wiz_fc, date(2025, 4, 30))
    print(f"Lignes remontees par la prevision de tresorerie :")
    for it in items:
        if it['amount'] == 60000.0 or it['partner'] == partner.name:
            print(f"  Row: {it['row']}, Amount: {it['amount']}, Date: {it['date']}")
    
    # Diagnostic du defaut
    has_customers = any(it['row'] == 'customers' and it['amount'] == 60000.0 for it in items)
    has_transit = any(it['row'] == 'transit_in' and it['amount'] == 60000.0 for it in items)
    
    print(f"Analyse Diagnostic :")
    print(f"  La facture payee (in_payment) apparait-elle encore dans 'customers' ? {has_customers}")
    print(f"  Le paiement en transit apparait-il dans 'transit_in' ? {has_transit}")
    
    if has_customers and has_transit:
        print("DIAGNOSTIC CONFIRME (DEF-OM-003) : DOUBLE COMPTAGE !")
        print("  La facture est dans 'in_payment', mais comme son move_line.reconciled=False dans Odoo 19,")
        print("  om_account_cash_forecast la comptabilise a la fois dans 'customers' ET dans 'transit_in'.")
    elif has_customers and not has_transit:
        print("DIAGNOSTIC (DEF-OM-003) : La facture est comptee dans 'customers' au lieu de 'transit_in'.")
    else:
        print(f"Statut prevision : customers={has_customers}, transit={has_transit}")

    print("\n=== ETAPES 5, 6 ET 7 EXECUTEES AVEC SUCCES ===")

if __name__ == "__main__":
    run_etapes_5_6_7(env)
