import os
import sys
import subprocess
import json

def run_in_odoo(code_snippet, db="odoo19_test"):
    cmd = [
        "docker", "exec", "-i", "odoo19_accounting_web",
        "odoo", "shell", "-d", db, "--no-http", "-p", "8079"
    ]
    proc = subprocess.run(cmd, input=code_snippet, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
    return proc.returncode, proc.stdout, proc.stderr

if __name__ == "__main__":
    print("Test runner initialized.")
