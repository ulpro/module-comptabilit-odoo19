from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountReportGeneralLedger(models.TransientModel):
    _name = "account.report.general.ledger"
    _inherit = "account.common.account.report"
    _description = "General Ledger Report"

    initial_balance = fields.Boolean(
        string='Inclure les soldes initiaux',
        help='Si vous sélectionnez une date, ce champ vous permet d\'ajouter une ligne '
             'pour afficher le montant débit/crédit/solde qui précède '
             'le filtre que vous avez défini.'
    )
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partenaire')],
        string='Trier par', required=True, default='sort_date'
    )
    journal_ids = fields.Many2many(
        'account.journal', 'account_report_general_ledger_journal_rel',
        'account_id', 'journal_id', string='Journals', required=True
    )

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        return records, data

    def _print_report(self, data):
        records, data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(landscape=True).report_action(records, data=data)
