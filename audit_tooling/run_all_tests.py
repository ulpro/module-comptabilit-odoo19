import subprocess
import json
import re
import time
import sys

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
    "om_account_accountant",
]

def run_module_test(module_name, db_name="odoo19_test"):
    cmd = [
        "docker", "exec", "odoo19_accounting_web",
        "odoo", "-d", db_name,
        "--test-enable", f"--test-tags=/{module_name}",
        "-p", "8079", "--stop-after-init",
        "--log-level=test"
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
        output = proc.stdout
        duration = round(time.time() - t0, 2)
        retcode = proc.returncode
    except subprocess.TimeoutExpired as e:
        output = e.stdout if e.stdout else "TIMEOUT EXPIRED (300s)"
        duration = 300.0
        retcode = -1

    # Analysis of output
    # Patterns
    # "0 failed, 0 error(s) of X tests"
    # "X failed, Y error(s) of Z tests"
    # "stats: <module>: X tests Y.YYs Z queries"
    res_match = re.search(r'(\d+)\s+failed,\s+(\d+)\s+error\(s\)\s+of\s+(\d+)\s+tests', output)
    stats_match = re.search(rf'{re.escape(module_name)}:\s+(\d+)\s+tests\s+([\d\.]+)s\s+(\d+)\s+queries', output)
    
    total_tests = 0
    failed_tests = 0
    error_tests = 0
    queries = 0
    module_time = duration

    if stats_match:
        total_tests = int(stats_match.group(1))
        module_time = float(stats_match.group(2))
        queries = int(stats_match.group(3))
    elif res_match:
        failed_tests = int(res_match.group(1))
        error_tests = int(res_match.group(2))
        total_tests = int(res_match.group(3))
        
    if res_match:
        failed_tests = int(res_match.group(1))
        error_tests = int(res_match.group(2))

    passed_tests = total_tests - (failed_tests + error_tests)
    if passed_tests < 0:
        passed_tests = 0

    # Extract errors/failures traceback
    failures = []
    if failed_tests > 0 or error_tests > 0 or retcode != 0:
        lines = output.splitlines()
        for idx, line in enumerate(lines):
            if " ERROR " in line or " FAIL: " in line or "Traceback (most recent call last):" in line:
                chunk = "\n".join(lines[max(0, idx-1):min(len(lines), idx+15)])
                failures.append(chunk)

    return {
        "module": module_name,
        "return_code": retcode,
        "duration": duration,
        "module_time": module_time,
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "errors": error_tests,
        "queries": queries,
        "failures_details": failures[:5],
        "output_tail": "\n".join(output.splitlines()[-20:])
    }

def main():
    results = {}
    print(f"Starting test execution across all {len(MODULES)} modules on odoo19_test...")
    for mod in MODULES:
        print(f"\n--- Testing module: {mod} ---")
        res = run_module_test(mod)
        results[mod] = res
        print(f"[{mod}] Total: {res['total_tests']} | Passed: {res['passed']} | Failed: {res['failed']} | Errors: {res['errors']} | Time: {res['duration']}s")
        if res['failed'] > 0 or res['errors'] > 0 or res['return_code'] != 0:
            print(f"FAILED DETAILS for {mod}:")
            for f in res['failures_details']:
                print(f)

    with open("audit_tooling/test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nAll results saved to audit_tooling/test_results.json")

if __name__ == "__main__":
    main()
