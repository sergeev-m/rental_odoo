from odoo import models, fields, api


class RentalOffice(models.Model):
    _name = "rental_vehicles.office"
    _description = "Rental Office"

    name = fields.Char(compute="_compute_name", store=True)
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
        'rental_vehicles.vehicle',
        'office_id',
        string='Vehicles',
    )
    salary_fixed_usd = fields.Float("Fixed Salary (USD)", default=150)
    salary_percent = fields.Float("Percent from Revenue (%)", default=30)

    @api.depends('country_id', 'city')
    def _compute_name(self):
        for rec in self:
            name = '---'
            if all((rec.country_id, rec.city)):
                name = f'{rec.country_id.name} - {rec.city}'
            rec.name = name

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


class OfficeMixin(models.AbstractModel):
    _name = "rental_vehicles.office.mixin"
    _description = "Office Mixin"

    office_id = fields.Many2one(
        "rental_vehicles.office",
        index=True,
        required=True,
        default=lambda self: self.env.context.get("office_id"),
    )
