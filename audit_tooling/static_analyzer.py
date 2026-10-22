import os
import ast
import re
import csv
import glob

MODULES = [
    "accounting_pdf_reports",
    "om_account_accountant",
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
    "om_spreadsheet_account_followup"
]

def analyze_manifests():
    print("=== 1. MANIFESTS ANALYSIS ===")
    results = {}
    for mod in MODULES:
        mf_path = os.path.join(mod, "__manifest__.py")
        if not os.path.exists(mf_path):
            results[mod] = {"error": "Manifest not found"}
            continue
        with open(mf_path, "r", encoding="utf-8") as f:
            try:
                data = ast.literal_eval(f.read())
            except Exception as e:
                data = {"error": str(e)}
        results[mod] = {
            "name": data.get("name"),
            "version": data.get("version"),
            "license": data.get("license"),
            "depends": data.get("depends", []),
            "external_dependencies": data.get("external_dependencies", {}),
            "installable": data.get("installable", True),
            "application": data.get("application", False),
        }
        print(f"[{mod}] Version: {results[mod]['version']} | License: {results[mod]['license']} | External: {results[mod]['external_dependencies']}")
    return results

def analyze_code():
    print("\n=== 2. STATIC CODE SCAN (SQL, SUDO, EVAL, TIMEOUTS, FILES/NET) ===")
    findings = []
    
    # regex patterns
    re_cr_execute = re.compile(r'(self\._?cr\.execute|env\.cr\.execute|cr\.execute)\s*\((.*?)\)', re.DOTALL)
    re_sudo = re.compile(r'\.sudo\s*\(')
    re_eval_exec = re.compile(r'\b(eval|exec)\s*\((.*?)\)')
    re_requests = re.compile(r'\brequests\.(get|post|put|delete|request)\s*\((.*?)\)', re.DOTALL)
    re_xmlrpc = re.compile(r'\bServerProxy\s*\((.*?)\)', re.DOTALL)
    
    for mod in MODULES:
        for root, dirs, files in os.walk(mod):
            # Skip test folders for sudo checking if required, but keep track
            is_test_dir = "tests" in root.replace("\\", "/").split("/")
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    full_content = "".join(lines)
                
                # Check line by line
                for idx, line in enumerate(lines, 1):
                    # Check eval / exec
                    if "safe_eval" not in line:
                        for m in re.finditer(r'\b(eval|exec)\s*\(', line):
                            # make sure it's not safe_eval or expression evaluation in xml
                            findings.append({
                                "module": mod,
                                "file": rel_path,
                                "line": idx,
                                "category": "EVAL_EXEC",
                                "detail": line.strip()
                            })
                    
                    # Check sudo outside tests
                    if not is_test_dir and ".sudo(" in line:
                        findings.append({
                            "module": mod,
                            "file": rel_path,
                            "line": idx,
                            "category": "SUDO_OUTSIDE_TESTS",
                            "detail": line.strip()
                        })
                        
                    # Check open() / os / network
                    if re.search(r'\bopen\s*\(', line) and not "open(" in line.replace("safe_eval", ""):
                        # check if writing or unvalidated reading
                        findings.append({
                            "module": mod,
                            "file": rel_path,
                            "line": idx,
                            "category": "FILE_ACCESS",
                            "detail": line.strip()
                        })

                # Ast based or regex based cr.execute
                for m in re_cr_execute.finditer(full_content):
                    call_str = m.group(0)
                    start_pos = m.start()
                    line_num = full_content.count('\n', 0, start_pos) + 1
                    # Check if SQL() is used (Odoo 17/18/19 requirement: from odoo.tools import SQL)
                    has_sql = "SQL(" in call_str or "tools.SQL" in call_str
                    has_fstring = "f\"" in call_str or "f\'" in call_str
                    has_percent = "%" in call_str and "SQL(" not in call_str and not re.search(r'LIKE\s+[\'"]%|%[\'"]', call_str)
                    has_format = ".format(" in call_str
                    
                    category = "RAW_CR_EXECUTE"
                    if has_fstring:
                        category = "SQL_INJECTION_FSTRING"
                    elif has_format:
                        category = "SQL_INJECTION_FORMAT"
                    elif not has_sql:
                        category = "CR_EXECUTE_WITHOUT_SQL"
                        
                    findings.append({
                        "module": mod,
                        "file": rel_path,
                        "line": line_num,
                        "category": category,
                        "detail": call_str.replace('\n', ' ')[:140]
                    })
                    
                # Check requests without timeout
                for m in re_requests.finditer(full_content):
                    call_str = m.group(0)
                    line_num = full_content.count('\n', 0, m.start()) + 1
                    if "timeout=" not in call_str and "timeout =" not in call_str:
                        findings.append({
                            "module": mod,
                            "file": rel_path,
                            "line": line_num,
                            "category": "REQUESTS_WITHOUT_TIMEOUT",
                            "detail": call_str.replace('\n', ' ')[:140]
                        })

    print(f"Total findings: {len(findings)}")
    for f in findings:
        print(f"[{f['category']}] {f['file']}:{f['line']} -> {f['detail']}")
    return findings

def analyze_models_and_security():
    print("\n=== 3. MODELS & SECURITY (ir.model.access.csv, ir.rule) ===")
    re_model = re.compile(r'class\s+([A-Za-z0-9_]+)\s*\((.*?)\):')
    re_name = re.compile(r'_name\s*=\s*[\'"]([a-zA-Z0-9_\.]+)[\'"]')
    re_inherit = re.compile(r'_inherit\s*=\s*([\[\'"][^\]\n]+[\]\'"])')
    
    summary = {}
    
    for mod in MODULES:
        models_defined = set()
        models_inherited_only = set()
        
        # Scan python files
        for root, dirs, files in os.walk(mod):
            for file in files:
                if not file.endswith(".py"):
                    continue
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                names = re_name.findall(content)
                inherits = re_inherit.findall(content)
                
                # Simple heuristic: if _name exists, it creates or explicitly inherits a table/model
                for n in names:
                    models_defined.add(n)
        
        # Read ir.model.access.csv
        access_csv_path = os.path.join(mod, "security", "ir.model.access.csv")
        csv_models = set()
        if os.path.exists(access_csv_path):
            with open(access_csv_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) > 2 and row[2]:
                        model_id = row[2].strip()
                        # model_xxx_yyy -> xxx.yyy
                        if model_id.startswith("model_"):
                            csv_models.add(model_id[6:].replace("_", "."))
                        else:
                            csv_models.add(model_id.replace("_", "."))
                            
        # Read ir.rule in security xml files
        security_rules = []
        for root, dirs, files in os.walk(mod):
            for file in files:
                if file.endswith(".xml"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        xml_content = f.read()
                    if 'model="ir.rule"' in xml_content:
                        # find all records with model="ir.rule"
                        records = re.findall(r'<record[^>]*model="ir\.rule"[^>]*>(.*?)</record>', xml_content, re.DOTALL)
                        for r in records:
                            m_match = re.search(r'model_([a-zA-Z0-9_]+)', r)
                            has_multicompany = "company_id" in r or "company_ids" in r
                            rule_id = re.search(r'id=[\'"]([a-zA-Z0-9_]+)[\'"]', r)
                            security_rules.append({
                                "rule": rule_id.group(1) if rule_id else "unknown",
                                "target_model": m_match.group(1).replace("_", ".") if m_match else "unknown",
                                "multicompany": has_multicompany,
                                "file": os.path.relpath(path)
                            })
                            
        summary[mod] = {
            "models_defined": sorted(list(models_defined)),
            "csv_models": sorted(list(csv_models)),
            "rules": security_rules
        }
        
        # Models defined but not in ir.model.access.csv
        missing_acl = []
        for m in models_defined:
            # check direct or normalized match
            m_norm = m.replace(".", "_")
            csv_norms = [c.replace(".", "_") for c in csv_models]
            if m_norm not in csv_norms and m not in csv_models:
                # check if transient/abstract? (we will refine)
                missing_acl.append(m)
                
        print(f"[{mod}] Models defined: {len(models_defined)} | ACL defined: {len(csv_models)} | Missing ACL candidates: {missing_acl}")
        print(f"[{mod}] ir.rules: {len(security_rules)} rules (Multi-company: {sum(1 for r in security_rules if r['multicompany'])})")

if __name__ == "__main__":
    analyze_manifests()
    analyze_code()
    analyze_models_and_security()
