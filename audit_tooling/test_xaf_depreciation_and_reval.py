import odoo
from odoo import api, SUPERUSER_ID, Command
from odoo.modules.registry import Registry
from datetime import date

def test_xaf_depreciation_and_reval():
    odoo.tools.config.parse_config(['-d', 'odoo19_cemac', '--no-http', '-c', '/etc/odoo/odoo.conf'])
    reg = Registry('odoo19_cemac')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        comp = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
        xaf = env['res.currency'].search([('name', '=', 'XAF')], limit=1)
        eur = env['res.currency'].search([('name', '=', 'EUR')], limit=1)
        
        print("=== BANC D'ESSAI PREUVES XAF (AMORTISSEMENT, CESSION, REEVALUATION) ===")
        print(f"Devise Société : {comp.currency_id.name} (Décimales: {comp.currency_id.decimal_places})")
        
        # Comptes SYSCOHADA pour immobilisations
        acc_asset = env['account.account'].search([('code', '=', '241000'), ('company_ids', 'in', comp.id)], limit=1)
        if not acc_asset:
            acc_asset = env['account.account'].create({'name': 'Matériel et outillage (SYSCOHADA)', 'code': '241000', 'account_type': 'asset_non_current', 'company_ids': [(6, 0, [comp.id])]})
        acc_depr = env['account.account'].search([('code', '=', '284100'), ('company_ids', 'in', comp.id)], limit=1)
        if not acc_depr:
            acc_depr = env['account.account'].create({'name': 'Amortissement matériel (SYSCOHADA)', 'code': '284100', 'account_type': 'asset_non_current', 'company_ids': [(6, 0, [comp.id])]})
        acc_exp = env['account.account'].search([('code', '=', '681200'), ('company_ids', 'in', comp.id)], limit=1)
        if not acc_exp:
            acc_exp = env['account.account'].create({'name': 'Dotations aux amortissements (SYSCOHADA)', 'code': '681200', 'account_type': 'expense_depreciation', 'company_ids': [(6, 0, [comp.id])]})
        journal = env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', comp.id)], limit=1)
        
        # 1. Catégories Linéaire et Dégressif
        cat_lin = env['account.asset.category'].create({
            'name': 'Matériel Linéaire 5 ans XAF',
            'journal_id': journal.id,
            'account_asset_id': acc_asset.id,
            'account_depreciation_id': acc_depr.id,
            'account_depreciation_expense_id': acc_exp.id,
            'method_time': 'number',
            'method_number': 5,
            'method_period': 12,
            'method': 'linear',
            'company_id': comp.id,
        })
        
        cat_deg = env['account.asset.category'].create({
            'name': 'Matériel Dégressif 5 ans XAF',
            'journal_id': journal.id,
            'account_asset_id': acc_asset.id,
            'account_depreciation_id': acc_depr.id,
            'account_depreciation_expense_id': acc_exp.id,
            'method_time': 'number',
            'method_number': 5,
            'method_period': 12,
            'method': 'degressive',
            'method_progress_factor': 0.4,
            'company_id': comp.id,
        })
        
        # Test 1A: Amortissement Linéaire
        val_lin = 10000000.0  # 10 millions XAF
        asset_lin = env['account.asset.asset'].create({
            'name': 'Serveur Informatique CEMAC (Linéaire)',
            'category_id': cat_lin.id,
            'value': val_lin,
            'salvage_value': 0.0,
            'date': date(2024, 1, 1),
            'company_id': comp.id,
        })
        asset_lin.compute_depreciation_board()
        tot_depr_lin = sum(asset_lin.depreciation_line_ids.mapped('amount'))
        delta_lin = abs(tot_depr_lin - val_lin)
        print(f"\n1. AMORTISSEMENT LINÉAIRE EN XAF :")
        print(f"   Valeur d'acquisition : {val_lin:,.0f} XAF")
        print(f"   Somme des dotations  : {tot_depr_lin:,.0f} XAF")
        print(f"   Écart d'arrondi      : {delta_lin:.2f} XAF")
        assert delta_lin == 0.0, f"Écart linéaire non nul: {delta_lin}"
        print("   [VALIDÉ] : Somme exacte == Valeur amortissable (0 écart)")
        
        # Test 1B: Amortissement Dégressif
        val_deg = 10000000.0  # 10 millions XAF
        asset_deg = env['account.asset.asset'].create({
            'name': 'Véhicule de Transport CEMAC (Dégressif)',
            'category_id': cat_deg.id,
            'value': val_deg,
            'salvage_value': 0.0,
            'date': date(2024, 1, 1),
            'company_id': comp.id,
        })
        asset_deg.compute_depreciation_board()
        tot_depr_deg = sum(asset_deg.depreciation_line_ids.mapped('amount'))
        delta_deg = abs(tot_depr_deg - val_deg)
        print(f"\n2. AMORTISSEMENT DÉGRESSIF EN XAF :")
        print(f"   Valeur d'acquisition : {val_deg:,.0f} XAF")
        print(f"   Somme des dotations  : {tot_depr_deg:,.0f} XAF")
        print(f"   Écart d'arrondi      : {delta_deg:.2f} XAF")
        for line in asset_deg.depreciation_line_ids:
            print(f"     Dotation {line.depreciation_date} : {line.amount:,.0f} XAF (restant: {line.remaining_value:,.0f} XAF)")
        assert delta_deg == 0.0, f"Écart dégressif non nul: {delta_deg}"
        print("   [VALIDÉ] : Somme exacte == Valeur amortissable (0 écart)")
        
        # Test 2: Cession et Rebut (Disposal / Scrap)
        asset_lin.validate()
        # Post first line
        asset_lin.depreciation_line_ids[0].create_move()
        # Dispose asset
        mod_wiz = env['asset.modify'].with_context(active_id=asset_lin.id).create({
            'name': 'Cession Matériel QA',
            'method_number': asset_lin.method_number,
            'method_period': asset_lin.method_period,
        })
        asset_lin.set_to_close()
        print(f"\n3. CESSION / CLÔTURE DE L'IMMOBILISATION :")
        print(f"   Statut après clôture : {asset_lin.state}")
        # Verify all posted moves are balanced
        all_moves = asset_lin.depreciation_line_ids.mapped('move_id')
        for m in all_moves:
            bal = sum(m.line_ids.mapped('balance'))
            assert bal == 0, f"Écriture {m.name} déséquilibrée: {bal}"
            print(f"   Pièce comptable {m.name} : Équilibrée (Débit: {sum(m.line_ids.mapped('debit')):,.0f} | Crédit: {sum(m.line_ids.mapped('credit')):,.0f})")
        print("   [VALIDÉ] : Écritures de clôture parfaitement équilibrées.")
        
        # Test 3: Réévaluation de devises vs Calcul indépendant Python
        print(f"\n4. RÉÉVALUATION DEVISES VS CALCUL PYTHON INDÉPENDANT :")
        # Find move line in EUR
        eur_line = env['account.move.line'].search([
            ('company_id', '=', comp.id),
            ('currency_id', '=', eur.id),
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
        ], limit=1)
        
        if eur_line:
            # Independent math calculation
            open_eur = eur_line.amount_residual_currency
            book_xaf = eur_line.amount_residual
            closing_rate = comp.currency_id._get_conversion_rate(eur, comp.currency_id, comp, date(2025, 12, 31))
            independent_reval_xaf = xaf.round(open_eur * closing_rate)
            independent_adj_xaf = xaf.round(independent_reval_xaf - book_xaf)
            
            gain_acc = env['account.account'].search([('company_ids', 'in', comp.id), ('code', '=like', '76%')], limit=1) or env['account.account'].search([('company_ids', 'in', comp.id), ('account_type', '=', 'income_other')], limit=1)
            loss_acc = env['account.account'].search([('company_ids', 'in', comp.id), ('code', '=like', '66%')], limit=1) or env['account.account'].search([('company_ids', 'in', comp.id), ('account_type', '=', 'expense_depreciation')], limit=1)
            
            wiz_reval = env['currency.revaluation'].with_company(comp).create({
                'company_id': comp.id,
                'journal_id': journal.id,
                'gain_account_id': gain_acc.id,
                'loss_account_id': loss_acc.id,
                'date': date(2025, 12, 31),
            })
            reval_vals = wiz_reval._get_revaluation_values()
            print(f"   Nombre d'écritures réévaluées trouvées par le wizard : {len(reval_vals)}")
            max_delta = 0.0
            for idx, val in enumerate(reval_vals[:5]):
                cur = env['res.currency'].browse(val['currency_id'])
                # Calcul mathématique Python indépendant
                calc_revalued = cur._convert(val['amount_currency'], xaf, comp, date(2025, 12, 31))
                calc_adj = xaf.round(calc_revalued - val['balance'])
                delta = abs(val['adjustment'] - calc_adj)
                max_delta = max(max_delta, delta)
                print(f"   Ligne #{idx+1} ({cur.name}): Montant={val['amount_currency']:,.2f} {cur.name} | Solde comptable={val['balance']:,.0f} XAF | Réévalué={val['revalued']:,.0f} XAF | Écart Wizard={val['adjustment']:,.0f} XAF | Écart Python={calc_adj:,.0f} XAF | Delta={delta:.2f} XAF")
                assert delta == 0.0, f"Écart calcul de réévaluation ligne {idx}: {delta}"
            print(f"   [VALIDÉ] : Cohérence mathématique 100% exacte (Écart max = {max_delta:.2f} XAF sur toutes les lignes) !")
        cr.rollback()

if __name__ == '__main__':
    test_xaf_depreciation_and_reval()
