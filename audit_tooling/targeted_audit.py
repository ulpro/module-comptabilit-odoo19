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

# Check OM Reconcile API
data1 = st1_line.om_bank_rec_get_data()
print("TEST A.1: 1-pour-1 OM API data fetched. Trans id:", data1['transaction']['id'], "Remaining:", data1['transaction']['remaining'])

# Search candidates
candidates = st1_line.om_bank_rec_candidates()
print("TEST A.1: Candidates found for st line:", len(candidates))

# Preview proposal
proposal = {'matches': [{'aml_id': inv1_line.id}]}
prev = st1_line.om_bank_rec_preview(proposal)
print("TEST A.1: Preview is_complete:", prev['is_complete'], "Remaining:", prev['remaining'])

# Validate reconciliation
st1_line.om_bank_rec_validate(proposal)
print("TEST A.1: Validated. is_reconciled:", st1_line.is_reconciled, "Inv1 residual:", inv1.amount_residual)

# Undo reconciliation
st1_line.action_undo_reconciliation()
print("TEST A.1: Undo reconciliation. is_reconciled:", st1_line.is_reconciled, "Inv1 residual restored:", inv1.amount_residual)

print("--- END TEST A ---")
""",

    "B_bank_import": """
# === TEST B: IMPORT DE RELEVES (om_account_bank_statement_import) ===
from odoo.exceptions import UserError

print("--- STARTING TEST B: STATEMENT IMPORT ---")
wizard_model = env['account.statement.import']
bank = env['account.journal'].search([('type', '=', 'bank')], limit=1)

# B.1: Fichier vide
try:
    wiz = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'empty.ofx', 'raw': b''})], 'journal_id': bank.id})
    wiz.action_import()
    print("TEST B.1: Fichier vide -> Non bloque!")
except Exception as e:
    print("TEST B.1: Fichier vide bloque avec succes:", type(e).__name__, str(e)[:60])

# B.2: Mauvais encodage / binaire corrompu
try:
    wiz = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'corrupt.qif', 'raw': b'\\xff\\xfe\\x00\\x12\\x88\\x99'})], 'journal_id': bank.id})
    wiz.action_import()
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
    res = wiz.action_import()
    print("TEST B.3: QIF valide importe avec succes:", res.get('res_model'))
    
    # B.4: Reimport doublon
    wiz2 = wizard_model.create({'attachment_ids': [(0, 0, {'name': 'valid.qif', 'raw': qif_content})], 'journal_id': bank.id})
    try:
        wiz2.action_import()
        print("TEST B.4: Doublon non detecte !")
    except UserError as e:
        print("TEST B.4: Doublon bloque correctement avec UserError:", str(e)[:60])
except Exception as e:
    print("TEST B.3: Erreur import QIF:", type(e).__name__, str(e)[:70])

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
    res_ofx = wiz_ofx.action_import()
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
    asset_acc = env['account.account'].search([('account_type', 'not in', env['account.asset.category'].exclude_types)], limit=1)
    depr_acc = env['account.account'].search([('id', '!=', asset_acc.id), ('account_type', 'not in', env['account.asset.category'].exclude_types)], limit=1)
    exp_acc = env['account.account'].search([('id', 'not in', (asset_acc.id, depr_acc.id)), ('account_type', 'not in', env['account.asset.category'].exclude_types)], limit=1)
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

    "E_currencies": """
# === TEST E: DEVISES & REEVALUATION (om_currency_revaluation, rate_update) ===
from datetime import date
from odoo.exceptions import UserError

print("--- STARTING TEST E: CURRENCIES & REVALUATION ---")
# E.1: Test Revaluation Wizard
journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
acc_gain = env['account.account'].search([('account_type', '=', 'income')], limit=1)
acc_loss = env['account.account'].search([('account_type', '=', 'expense')], limit=1)

wizard = env['currency.revaluation'].create({
    'date': '2026-03-31',
    'journal_id': journal.id,
    'gain_account_id': acc_gain.id,
    'loss_account_id': acc_loss.id,
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
form_data = wiz_gl.read()[0]
form_data['used_context'] = {'date_from': False, 'date_to': False, 'strict_range': False, 'state': 'posted'}
gl_report = env['report.accounting_pdf_reports.report_general_ledger'].with_context(
    active_model='account.report.general.ledger', active_ids=[wiz_gl.id]
)
gl_values = gl_report._get_report_values(docids=[wiz_gl.id], data={'form': form_data})
print("TEST G.1: General Ledger report data generated. Accounts count:", len(gl_values.get('Accounts', [])))

# 3. Trial Balance Wizard
wiz_tb = env['account.balance.report'].create({
    'target_move': 'posted',
    'display_account': 'all',
})
form_tb = wiz_tb.read()[0]
form_tb['used_context'] = {'date_from': False, 'date_to': False, 'strict_range': False, 'state': 'posted'}
tb_report = env['report.accounting_pdf_reports.report_trialbalance'].with_context(
    active_model='account.balance.report', active_ids=[wiz_tb.id]
)
tb_values = tb_report._get_report_values(docids=[wiz_tb.id], data={'form': form_tb})
print("TEST G.2: Trial Balance report data generated. Accounts count:", len(tb_values.get('Accounts', [])))

print("--- END TEST G ---")
"""
}

def main():
    results = {}
    print(f"Running targeted functional verification test suites on odoo19_test...")
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
            
    with open("audit_tooling/targeted_audit_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nSaved targeted audit results to audit_tooling/targeted_audit_results.json")

if __name__ == "__main__":
    main()
