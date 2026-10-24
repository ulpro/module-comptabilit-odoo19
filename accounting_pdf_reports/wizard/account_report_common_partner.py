from odoo import fields, models


class AccountingCommonPartnerReport(models.TransientModel):
    _name = 'account.common.partner.report'
    _inherit = "account.common.report"
    _description = 'Account Common Partner Report'

    result_selection = fields.Selection([('customer', 'Comptes clients (Créances)'),
                                         ('supplier', 'Comptes fournisseurs (Dettes)'),
                                         ('customer_supplier', 'Clients et Fournisseurs')
                                         ], string="Partenaires", required=True, default='customer')
    partner_ids = fields.Many2many('res.partner', string='Partners')

    def pre_print_report(self, data):
        data['form'].update(self.read(['result_selection'])[0])
        data['form'].update({'partner_ids': self.partner_ids.ids})
        return data
