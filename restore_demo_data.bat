@echo off
chcp 65001 >nul
echo ================================================================================
echo       RÉINITIALISATION DU JEU DE DONNÉES DE PRÉSENTATION ODOO 19
echo ================================================================================
echo Cette opération va restaurer la base 'odoo19_cemac' à son état d'origine.
echo.
docker exec odoo19_accounting_web python3 /mnt/extra-addons/audit_tooling/restore_presentation_data.py --force
echo.
pause
