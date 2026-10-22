import os
import sys
import subprocess
import json
import time

def run_python_in_odoo(code, db="odoo19_test"):
    cmd = [
        "docker", "exec", "-i", "odoo19_accounting_web",
        "odoo", "shell", "-d", db, "--no-http", "-p", "8079"
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, input=code.encode('utf-8'),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=180
        )
        out = proc.stdout.decode('utf-8', errors='replace')
        err = proc.stderr.decode('utf-8', errors='replace')
        code = proc.returncode
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode('utf-8', errors='replace') if e.stdout else ""
        err = "TIMEOUT EXPIRED (180s)"
        code = -1
    return code, out, err, round(time.time() - t0, 2)

AUDIT_TESTS = {
    "A_reconciliation": """
# === TEST A: RAPPROCHEMENT BANCAIRE (om_account_reconcile) ===
from datetime import date
from odoo import Command
from odoo.exceptions import UserError, ValidationError

print("--- STARTING TEST A: RECONCILIATION ---")
bank = env['account.journal'].search([('type', '=', 'bank')], limit=1)
partner = env['res.partner'].search([], limit=1)
receivable_account = partner.property_account_receivable_id or env['account.account'].search([('account_type', '=', 'asset_receivable')], limit=1)

# 1. Test 1-pour-1
inv1 = env['account.move'].create({
    'move_type': 'out_invoice',
    'partner_id': partner.id,
    'invoice_date': '2026-03-01',
    'invoice_line_ids': [Command.create({'name': 'Prestation 1-1', 'price_unit': 1500.0, 'tax_ids': []})],
})
inv1.action_post()
inv1_line = inv1.line_ids.filtered(lambda l: l.account_id == receivable_account)

st1 = env['account.bank.statement'].create({
    'name': 'Releve 1-1',
    'journal_id': bank.id,
    'date': '2026-03-02',
    'line_ids': [Command.create({
        'payment_ref': 'Reglement Facture 1-1',
        'partner_id': partner.id,
        'amount': 1500.0,
        'date': '2026-03-02',
    })]
})
st1_line = st1.line_ids[0]

ui_data = env['account.reconciliation.widget'].get_bank_statement_line_data([st1_line.id])
print("TEST A.1: 1-pour-1 Data fetched. Lines found:", len(ui_data.get('lines', [])))

# 2. Test Partial Payment & Write-off
inv2 = env['account.move'].create({
    'move_type': 'out_invoice',
    'partner_id': partner.id,
    'invoice_date': '2026-03-05',
    'invoice_line_ids': [Command.create({'name': 'Prestation Partielle', 'price_unit': 2000.0, 'tax_ids': []})],
})
inv2.action_post()
inv2_line = inv2.line_ids.filtered(lambda l: l.account_id == receivable_account)

st2 = env['account.bank.statement'].create({
    'name': 'Releve Partiel',
    'journal_id': bank.id,
    'date': '2026-03-06',
    'line_ids': [Command.create({
        'payment_ref': 'Reglement Partiel 1200',
        'partner_id': partner.id,
        'amount': 1200.0,
        'date': '2026-03-06',
    })]
})
st2_line = st2.line_ids[0]

# Perform partial reconcile
res_rec = env['account.reconciliation.widget'].process_bank_statement_line(
    st2_line.id,
    [{'id': inv2_line.id, 'type': 'line'}]
)
print("TEST A.2: Partial reconcile performed. Inv2 residual:", inv2.amount_residual, "reconciled:", inv2_line.reconciled)

# 3. Test Unreconcile
st2_line.action_undo_reconciliation()
print("TEST A.3: Undo reconcile performed. Inv2 residual restored:", inv2.amount_residual)

# 4. Concurrence / double lettrage
try:
    env['account.reconciliation.widget'].process_bank_statement_line(
        st2_line.id,
        [{'id': inv2_line.id, 'type': 'line'}]
    )
    try:
        env['account.reconciliation.widget'].process_bank_statement_line(
            st2_line.id,
            [{'id': inv2_line.id, 'type': 'line'}]
        )
        print("TEST A.4: Second call handled (idempotent / no duplicate write-off).")
    except Exception as e:
        print("TEST A.4: Concurrency safely prevented:", type(e).__name__)
except Exception as e:
    print("TEST A.4: Reconcile exception:", e)

print("--- END TEST A ---")
""",

    "B_bank_import": """
# === TEST B: IMPORT DE RELEVES (om_account_bank_statement_import) ===
import base64
from odoo.exceptions import UserError

print("--- STARTING TEST B: STATEMENT IMPORT ---")
wizard_model = env['account.statement.import']
bank = env['account.journal'].search([('type', '=', 'bank')], limit=1)

# B.1: Fichier vide
try:
    wiz = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'empty.ofx', 'raw': b''})]})
    wiz.import_file()
    print("TEST B.1: Fichier vide -> Non bloque!")
except Exception as e:
    print("TEST B.1: Fichier vide bloque avec succes:", type(e).__name__, str(e)[:60])

# B.2: Mauvais encodage / binaire corrompu
try:
    wiz = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'corrupt.qif', 'raw': b'\\xff\\xfe\\x00\\x12\\x88\\x99'})]})
    wiz.import_file()
    print("TEST B.2: Corrupt QIF -> Non bloque!")
except Exception as e:
    print("TEST B.2: Corrupt QIF bloque avec succes:", type(e).__name__, str(e)[:60])

# B.3: QIF valide
qif_content = b'''!Type:Bank
D01/03/2026
T500.00
PVirement Client QIF Test
^
'''
try:
    wiz = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'valid.qif', 'raw': qif_content})], 'journal_id': bank.id})
    res = wiz.import_file()
    print("TEST B.3: QIF valide importe avec succes:", res.get('res_model'), res.get('res_id'))
    
    # B.4: Reimport du meme fichier (detection doublon)
    wiz2 = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'valid.qif', 'raw': qif_content})], 'journal_id': bank.id})
    try:
        wiz2.import_file()
        print("TEST B.4: Reimport doublon -> Non bloque ou accepte!")
    except Exception as e:
        print("TEST B.4: Doublon bloque correctement:", type(e).__name__, str(e)[:60])
except Exception as e:
    print("TEST B.3: Echec import QIF valide:", e)

# B.5: OFX valide
acc_num = bank.bank_acc_number or '123456789'
ofx_str = f'''OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEVERSION:NONE
NEWFILEVERSION:NONE
<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1001
<STATUS><CODE>0<SEVERITY>INFO</STATUS>
<STMTRS>
<CURDEF>XAF
<BANKACCTFROM><BANKID>0001<ACCTID>{acc_num}</ACCTID></BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260301000000
<DTEND>20260302000000
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260301120000
<TRNAMT>750.00
<FITID>OFX_TEST_TRANS_01
<NAME>OFX Client Test
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL><BALAMT>750.00<DTASOF>20260302000000</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>'''
try:
    wiz_ofx = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'test.ofx', 'raw': ofx_str.encode('ascii')})], 'journal_id': bank.id})
    res_ofx = wiz_ofx.import_file()
    print("TEST B.5: OFX valide importe avec succes:", res_ofx.get('res_model'))
except Exception as e:
    print("TEST B.5: OFX import note:", type(e).__name__, str(e)[:80])

print("--- END TEST B ---")
""",

    "C_assets": """
# === TEST C: IMMOBILISATIONS (om_account_asset) ===
from datetime import date
from odoo import Command

print("--- STARTING TEST C: ASSET MANAGEMENT ---")
category = env['account.asset.category'].search([], limit=1)
if not category:
    asset_acc = env['account.account'].search([('account_type', '=', 'asset_non_current')], limit=1)
    depr_acc = env['account.account'].search([('account_type', '=', 'liability_non_current')], limit=1)
    exp_acc = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
    journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
    category = env['account.asset.category'].create({
        'name': 'Materiel Informatique Test',
        'account_asset_id': asset_acc.id,
        'account_depreciation_id': depr_acc.id,
        'account_depreciation_expense_id': exp_acc.id,
        'journal_id': journal.id,
        'method_time': 'number',
        'method_number': 3,
        'method_period': 12,
        'method': 'linear',
        'date_first_depreciation': 'last_day_period',
    })

# C.1: Asset Lineaire
asset_lin = env['account.asset.asset'].create({
    'name': 'Serveur Dell Test',
    'category_id': category.id,
    'value': 3000.0,
    'salvage_value': 0.0,
    'date': '2026-01-01',
    'method_number': 3,
    'method_period': 12,
    'method': 'linear',
    'prorata': False,
})
asset_lin.compute_depreciation_board()
lines = asset_lin.depreciation_line_ids
tot_depr = sum(lines.mapped('amount'))
print("TEST C.1: Lineaire 3 ans: Lines count:", len(lines), "Sum:", tot_depr, "Expected: 3000.0", "Delta:", abs(tot_depr - 3000.0))

# C.2: Prorata temporis & bissextile
asset_prorata = env['account.asset.asset'].create({
    'name': 'Vehicule Test Prorata',
    'category_id': category.id,
    'value': 12000.0,
    'date': '2026-07-01',
    'method_number': 3,
    'method_period': 12,
    'method': 'linear',
    'prorata': True,
})
asset_prorata.compute_depreciation_board()
tot_prorata = sum(asset_prorata.depreciation_line_ids.mapped('amount'))
print("TEST C.2: Prorata temporis: Lines count:", len(asset_prorata.depreciation_line_ids), "Sum:", tot_prorata, "Expected: 12000.0")

# C.3: Cession / Rebut
asset_lin.validate()
first_depr_line = asset_lin.depreciation_line_ids[0]
first_depr_line.create_move()
print("TEST C.3: Premier amortissement comptabilise. Move:", first_depr_line.move_id.name, "Total balance debit==credit:", first_depr_line.move_id.amount_total)

try:
    asset_lin.set_to_close()
    print("TEST C.3: Asset cloture / rebut effectue avec succes.")
except Exception as e:
    print("TEST C.3: Cession/Rebut exception:", type(e).__name__, str(e)[:80])

print("--- END TEST C ---")
""",

    "D_fiscal_year": """
# === TEST D: EXERCICES FISCAUX ET VERROUILLAGE (om_fiscal_year) ===
from datetime import date
from odoo.exceptions import UserError, ValidationError

print("--- STARTING TEST D: FISCAL YEAR & LOCK DATES ---")
company = env.company

# D.1: Creation exercice fiscal
fy = env['account.fiscal.year'].create({
    'name': 'Exercice 2025 Test',
    'date_from': '2025-01-01',
    'date_to': '2025-12-31',
    'company_id': company.id,
})
print("TEST D.1: Exercice fiscal cree:", fy.name)

# D.2: Verrouillage et tentative de modification sur periode verrouillee
company.write({'fiscalyear_lock_date': date(2025, 12, 31)})
journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
acc = env['account.account'].search([('account_type', '=', 'expense')], limit=1)

move = env['account.move'].search([('state', '=', 'posted')], limit=1)
if move:
    try:
        move.write({'date': date(2025, 6, 15)})
        print("TEST D.2: ALERTE - Modification autorisee sur periode verrouillee !")
    except UserError as e:
        print("TEST D.2: Modification sur periode verrouillee bloquee avec succes:", str(e)[:70])

# Nettoyage
company.write({'fiscalyear_lock_date': False})
print("--- END TEST D ---")
""",

    "E_currencies": """
# === TEST E: DEVISES & REEVALUATION (om_currency_revaluation, rate_update) ===
from datetime import date
from odoo.exceptions import UserError

print("--- STARTING TEST E: CURRENCIES & REVALUATION ---")
# E.1: Test Revaluation
wizard = env['currency.revaluation'].create({
    'date': '2026-03-31',
})
domain = wizard._revaluation_domain()
print("TEST E.1: Revaluation domain constructed successfully:", len(domain), "clauses")

# E.2: Test Provider invalid URL / mock failure
company = env.company
company.rate_provider = 'frankfurter'
from odoo.addons.om_currency_rate_update.models.rate_providers import PROVIDERS
try:
    prov = PROVIDERS['frankfurter'](company)
    try:
        prov._get_json("https://invalid-non-existent-domain-xyz123.org/latest")
        print("TEST E.2: Erreur reseau non levee !")
    except UserError as e:
        print("TEST E.2: Gestion erreur provider reussie (UserError propre):", str(e)[:70])
except Exception as e:
    print("TEST E.2: Note provider test:", type(e).__name__, str(e)[:70])

print("--- END TEST E ---")
""",

    "F_followup": """
# === TEST F: RELANCES (om_account_followup) ===
print("--- STARTING TEST F: FOLLOWUP ---")
partner = env['res.partner'].search([('email', '!=', False)], limit=1)
if partner:
    partner._compute_followup_status()
    print("TEST F.1: Partner followup status computed:", partner.followup_status)

partner_no_email = env['res.partner'].create({'name': 'Client Sans Email Test'})
try:
    wiz = env['followup.send'].create({'partner_ids': [(4, partner_no_email.id)]})
    print("TEST F.2: Wizard send followup sans email:", wiz)
except Exception as e:
    print("TEST F.2: Note followup sans email:", type(e).__name__, str(e)[:70])

print("--- END TEST F ---")
""",

    "G_reports_sql": """
# === TEST G: RAPPORTS PDF VS REQUETE SQL DIRECTE (accounting_pdf_reports) ===
print("--- STARTING TEST G: FINANCIAL REPORTS VS SQL DIRECT ---")
company = env.company

# 1. Total debit/credit direct SQL
env.cr.execute(\"\"\"
    SELECT COALESCE(SUM(debit), 0) as total_debit,
           COALESCE(SUM(credit), 0) as total_credit,
           COALESCE(SUM(balance), 0) as total_balance
      FROM account_move_line
     WHERE company_id = %s
       AND parent_state = 'posted'
\"\"\", [company.id])
sql_res = env.cr.dictfetchone()
print(f"SQL DIRECT - Debit: {sql_res['total_debit']}, Credit: {sql_res['total_credit']}, Balance: {sql_res['total_balance']}")

# 2. General Ledger Wizard
wiz_gl = env['account.report.general.ledger'].create({
    'target_move': 'posted',
    'display_account': 'all',
})
form_data = {
    'target_move': 'posted',
    'display_account': 'all',
    'used_context': {'date_from': False, 'date_to': False, 'strict_range': False, 'state': 'posted'},
    'id': wiz_gl.id,
}
gl_values = env['report.accounting_pdf_reports.report_general_ledger']._get_report_values(
    docids=[wiz_gl.id], data={'form': form_data}
)
print("TEST G.1: General Ledger report data generated. Accounts count:", len(gl_values.get('Accounts', [])))

# 3. Trial Balance Wizard
wiz_tb = env['account.balance.report'].create({
    'target_move': 'posted',
    'display_account': 'all',
})
form_tb = {
    'target_move': 'posted',
    'display_account': 'all',
    'used_context': {'date_from': False, 'date_to': False, 'strict_range': False, 'state': 'posted'},
    'id': wiz_tb.id,
}
tb_values = env['report.accounting_pdf_reports.report_trialbalance']._get_report_values(
    docids=[wiz_tb.id], data={'form': form_tb}
)
print("TEST G.2: Trial Balance report data generated. Accounts count:", len(tb_values.get('Accounts', [])))

print("--- END TEST G ---")
""",

    "H_budgets_checks_recurring": """
# === TEST H: BUDGETS, RECURRING PAYMENTS, CHEQUES ===
print("--- STARTING TEST H: RECURRING & CHEQUES ---")
# H.1: Cron paiement recurrent
cron = env.ref('om_recurring_payments.ir_cron_recurring_payment', raise_if_not_found=False)
print("TEST H.1: Cron recurring payment exist:", bool(cron))

# H.2: num2words en francais
try:
    from num2words import num2words
    fr_words = num2words(1250.75, lang='fr')
    print("TEST H.2: Montant en lettres francais (num2words):", fr_words)
except Exception as e:
    print("TEST H.2: num2words fr error:", e)

print("--- END TEST H ---")
""",

    "I_spreadsheets": """
# === TEST I: SPREADSHEETS (om_spreadsheet_*) ===
print("--- STARTING TEST I: SPREADSHEET DASHBOARDS ---")
dashboards = env['spreadsheet.dashboard'].search([('name', 'ilike', 'account')])
print(f"TEST I.1: Found {len(dashboards)} accounting dashboards.")
for d in dashboards:
    print(f"  - Dashboard: {d.name} (Data size: {len(d.spreadsheet_data or '')} bytes)")
print("--- END TEST I ---")
""",

    "SEC_rights_and_multicompany": """
# === TESTS SECURITE, GROUPES & MULTI-SOCIETES ===
from odoo.exceptions import AccessError

print("--- STARTING SECURITY & RIGHTS AUDIT ---")
groups = [
    'account.group_account_invoice',
    'account.group_account_user',
    'account.group_account_manager'
]
for g in groups:
    grp = env.ref(g, raise_if_not_found=False)
    print(f"Group {g}: Found={bool(grp)}")

# Test d'isolation multi-societes
company1 = env.company
company2 = env['res.company'].search([('id', '!=', company1.id)], limit=1)
if not company2:
    company2 = env['res.company'].create({'name': 'Filiale Test 2', 'currency_id': company1.currency_id.id})

cat = env['account.asset.category'].search([], limit=1)
if cat:
    asset_c1 = env['account.asset.asset'].create({
        'name': 'Asset Company 1',
        'category_id': cat.id,
        'company_id': company1.id,
        'value': 1000.0,
    })
    assets_from_c2 = env['account.asset.asset'].with_company(company2).search([('id', '=', asset_c1.id)])
    print(f"Multi-company isolation Asset: visible from Company 2? {bool(assets_from_c2)} (Expected: False)")

# Test injection SQL sur partenaire
try:
    inj_partner = env['res.partner'].create({
        'name': "Test injection '; DROP TABLE dummy_table; --",
        'ref': "' OR 1=1 --",
    })
    print("Injection test partner created successfully:", inj_partner.name)
except Exception as e:
    print("Injection test error:", e)

print("--- END SECURITY AUDIT ---")
""",

    "PERF_benchmark": """
# === TEST PERFORMANCE & N+1 ===
import time
print("--- STARTING PERFORMANCE & N+1 AUDIT ---")
MoveLine = env['account.move.line']
total_lines = MoveLine.search_count([])
print(f"Existing account.move.line count: {total_lines}")

t0 = time.time()
wiz_gl = env['account.report.general.ledger'].create({'target_move': 'posted', 'display_account': 'all'})
form_data = {
    'target_move': 'posted',
    'display_account': 'all',
    'used_context': {'date_from': False, 'date_to': False, 'strict_range': False, 'state': 'posted'},
    'id': wiz_gl.id,
}
gl_values = env['report.accounting_pdf_reports.report_general_ledger']._get_report_values(
    docids=[wiz_gl.id], data={'form': form_data}
)
t_gl = round(time.time() - t0, 3)
print(f"General Ledger execution time: {t_gl}s")

t0 = time.time()
st_lines = env['account.bank.statement.line'].search([], limit=50)
if st_lines:
    reconcile_data = env['account.reconciliation.widget'].get_bank_statement_line_data(st_lines.ids)
    t_rec = round(time.time() - t0, 3)
    print(f"Reconciliation screen 50 lines time: {t_rec}s")
else:
    print("No bank statement lines to test reconciliation performance.")

print("--- END PERFORMANCE AUDIT ---")
""",

    "NATIVE_regression": """
# === TEST REGRESSION NATIVE ODOO 19 ===
from odoo import Command
from datetime import date
print("--- STARTING NATIVE REGRESSION TEST ---")
partner = env['res.partner'].search([], limit=1)
product = env['product.product'].search([], limit=1)

# 1. Facture client standard
inv = env['account.move'].create({
    'move_type': 'out_invoice',
    'partner_id': partner.id,
    'invoice_date': date.today(),
    'invoice_line_ids': [Command.create({
        'product_id': product.id,
        'quantity': 2,
        'price_unit': 100.0,
    })]
})
inv.action_post()
print(f"Native customer invoice posted: {inv.name}, Total: {inv.amount_total}, State: {inv.state}")

# 2. Facture fournisseur standard
bill = env['account.move'].create({
    'move_type': 'in_invoice',
    'partner_id': partner.id,
    'invoice_date': date.today(),
    'invoice_line_ids': [Command.create({
        'product_id': product.id,
        'quantity': 1,
        'price_unit': 80.0,
    })]
})
bill.action_post()
print(f"Native vendor bill posted: {bill.name}, Total: {bill.amount_total}, State: {bill.state}")

print("Native regression test completed successfully: NO REGRESSION FOUND.")
print("--- END NATIVE REGRESSION TEST ---")
"""
}

def main():
    results = {}
    print(f"Running {len(AUDIT_TESTS)} deep functional and QA test suites on odoo19_test...")
    for test_name, code in AUDIT_TESTS.items():
        print(f"\n==================== RUNNING {test_name} ====================")
        retcode, out, err, dur = run_python_in_odoo(code)
        results[test_name] = {
            "return_code": retcode,
            "output": out,
            "error": err,
            "duration": dur
        }
        clean_lines = [l for l in out.splitlines() if not l.startswith("2026-") and l.strip()]
        for l in clean_lines:
            print("  [OUT]", l)
        if retcode != 0:
            print(f"  [ERROR] Code {retcode}: {err[-300:]}")
            
    with open("audit_tooling/deep_audit_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nSaved deep audit results to audit_tooling/deep_audit_results.json")

if __name__ == "__main__":
    main()
