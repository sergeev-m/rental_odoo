from odoo import models, fields, api


class RentalOffice(models.Model):
    _name = "rental.office"
    _description = "Rental Office"

    name = fields.Char(compute="_compute_name")
    city = fields.Char(required=True)
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        required=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True
    )
    vehicle_ids = fields.One2many(
        'rental.vehicle',
        'office_id',
        string='Vehicles',
    )

    def _compute_name(self):
        for rec in self:
            rec.name = '---'
            if all((rec.country_id, rec.city)):
                rec.name = f'{rec.country_id.name} - {rec.city}'

    @api.onchange("country_id")
    def _onchange_country_id(self):
        if self.country_id:
            self.currency_id = self.country_id.currency_id

    @api.model
    def create(self, vals):
        office = super().create(vals)
        
        if not office.currency_id.active:
            office.currency_id.active = True
        
        return office


    # def write(self, values):
    #     res = super().write(values)
    #     if values.get('role_ids'):
    #         self.onchange_role_ids()
    #     return res

