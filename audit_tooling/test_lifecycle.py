import subprocess
import json
import time

MODULES = [
    "accounting_pdf_reports",
    "om_account_asset",
    "om_account_bank_statement_import",
    "om_account_budget",
    "om_account_cash_forecast",
    "om_account_check_printing",
    "om_account_daily_reports",
    "om_account_followup",
    "om_account_reconcile",
    "om_currency_rate_update",
    "om_currency_revaluation",
    "om_fiscal_year",
    "om_recurring_payments",
    "om_spreadsheet_account",
    "om_spreadsheet_account_asset",
    "om_spreadsheet_account_budget",
    "om_spreadsheet_account_followup",
    "om_account_accountant"
]

def recreate_db(db_name="test_lifecycle"):
    sql = f"""
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
    DROP DATABASE IF EXISTS {db_name};
    CREATE DATABASE {db_name} OWNER odoo;
    """
    subprocess.run(["docker", "exec", "odoo19_accounting_db", "psql", "-U", "odoo", "-d", "postgres", "-c", sql],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def run_lifecycle():
    recreate_db("test_lifecycle")
    
    # 1. Install each module individually
    results = {}
    print("=== TESTING INDIVIDUAL MODULE INSTALLATIONS & UNINSTALLATIONS ===")
    for mod in MODULES:
        print(f"\n--- Lifecycle test for {mod} ---")
        t0 = time.time()
        
        # We can test install on test_lifecycle or a sub-db
        # To make it clean and fast, let's install on test_lifecycle
        cmd_install = [
            "docker", "exec", "odoo19_accounting_web",
            "odoo", "-d", "test_lifecycle", "-i", mod,
            "-p", "8079", "--stop-after-init", "--no-http"
        ]
        p_inst = subprocess.run(cmd_install, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        inst_ok = p_inst.returncode == 0 and "ERROR" not in p_inst.stdout
        
        # Test uninstall via python script
        uninstall_script = f"""
mod = env['ir.module.module'].search([('name', '=', '{mod}')])
if mod and mod.state == 'installed':
    print('FOUND INSTALLED:', mod.name)
    mod.button_immediate_uninstall()
    print('UNINSTALLED SUCCESSFULLY')
else:
    print('MODULE NOT INSTALLED')
"""
        p_uninst = subprocess.run(
            ["docker", "exec", "-i", "odoo19_accounting_web", "odoo", "shell", "-d", "test_lifecycle", "-p", "8079", "--no-http"],
            input=uninstall_script, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120
        )
        uninst_ok = "UNINSTALLED SUCCESSFULLY" in p_uninst.stdout and "Traceback" not in p_uninst.stdout

        # Check orphan models/menus/views
        orphan_check_script = """
# Check if any ir.model exists without valid table
models = env['ir.model'].search([('transient', '=', False)])
orphans = []
for m in models:
    env.cr.execute("SELECT to_regclass(%s)", [m.model.replace('.', '_')])
    if not env.cr.fetchone()[0]:
        orphans.append(m.model)
print("ORPHAN_MODELS:", orphans)
"""
        p_orphans = subprocess.run(
            ["docker", "exec", "-i", "odoo19_accounting_web", "odoo", "shell", "-d", "test_lifecycle", "-p", "8079", "--no-http"],
            input=orphan_check_script, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60
        )
        
        duration = round(time.time() - t0, 2)
        results[mod] = {
            "install_ok": inst_ok,
            "uninstall_ok": uninst_ok,
            "duration": duration,
            "install_output": p_inst.stdout[-300:] if not inst_ok else "OK",
            "uninstall_output": p_uninst.stdout[-300:] if not uninst_ok else "OK",
            "orphan_info": p_orphans.stdout[-150:]
        }
        print(f"[{mod}] Install: {'OK' if inst_ok else 'FAIL'} | Uninstall: {'OK' if uninst_ok else 'FAIL'} ({duration}s)")
        
    with open("audit_tooling/lifecycle_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to audit_tooling/lifecycle_results.json")

if __name__ == "__main__":
    run_lifecycle()
