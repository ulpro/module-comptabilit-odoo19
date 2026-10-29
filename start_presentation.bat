@echo off
chcp 65001 >nul
echo ================================================================================
echo       LANCEMENT DE LA SUITE COMPTABILITÉ ODOO 19 POUR PRÉSENTATION
echo ================================================================================

echo [1/3] Démarrage des conteneurs Docker (Odoo 19 + PostgreSQL 16)...
docker compose up -d

echo.
echo [2/3] Initialisation et vérification des données de présentation...
docker exec odoo19_accounting_web python3 /mnt/extra-addons/audit_tooling/restore_presentation_data.py

echo.
echo [3/3] Ouverture de l'application dans votre navigateur...
start http://localhost:8069

echo.
echo ================================================================================
echo L'environnement est prêt pour votre démonstration !
echo Appuyez sur une touche pour quitter cette fenêtre.
echo ================================================================================
pause
