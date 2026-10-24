from odoo import api, fields, models


class AccountCommonAccountReport(models.TransientModel):
    _name = 'account.common.account.report'
    _inherit = "account.common.report"
    _description = 'Account Common Account Report'

    display_account = fields.Selection([('all', 'Tout'), 
                                        ('movement', 'Avec des mouvements'),
                                        ('not_zero', 'Avec un solde non nul'), ],
                                       string='Afficher les comptes',
                                       required=True, default='movement')
    analytic_account_ids = fields.Many2many('account.analytic.account', 
                                            string='Analytic Accounts')
    account_ids = fields.Many2many('account.account', string='Accounts')
    partner_ids = fields.Many2many('res.partner', string='Partners')

    def pre_print_report(self, data):
        data['form'].update(self.read(['display_account'])[0])
        data['form'].update({
            'analytic_account_ids': self.analytic_account_ids.ids,
            'partner_ids': self.partner_ids.ids,
            'account_ids': self.account_ids.ids,
        })
        return data
