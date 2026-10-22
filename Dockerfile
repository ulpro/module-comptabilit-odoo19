FROM odoo:19.0

USER root

# Copie et installation des dépendances Python identifiées durant l'audit
COPY requirements.txt /etc/odoo/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /etc/odoo/requirements.txt 2>/dev/null || \
    pip3 install --no-cache-dir -r /etc/odoo/requirements.txt

USER odoo
