#!/bin/bash
set -e

echo "================================================================================"
echo "      LANCEMENT DE LA SUITE COMPTABILITÉ ODOO 19 POUR PRÉSENTATION"
echo "================================================================================"

echo "[1/3] Démarrage des conteneurs Docker (Odoo 19 + PostgreSQL 16)..."
docker compose up -d

echo ""
echo "[2/3] Initialisation et vérification des données de présentation..."
docker exec odoo19_accounting_web python3 /mnt/extra-addons/audit_tooling/restore_presentation_data.py

echo ""
echo "[3/3] Prêt ! Accédez à : http://localhost:8069"
which xdg-open > /dev/null && xdg-open http://localhost:8069 || which open > /dev/null && open http://localhost:8069 || echo "Ouvrez http://localhost:8069 dans votre navigateur."
