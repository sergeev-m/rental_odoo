from odoo import models, fields


class Accessory(models.Model):
    _name = "rental_vehicles.accessory"
    _description = "Accessory"
    _order = "id desc, name"

    name = fields.Char(required=True)
    office_id = fields.Many2one('rental_vehicles.office', required=True)
    default_price = fields.Monetary(string="Default Price", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        related='office_id.currency_id'
    )
    active = fields.Boolean(default=True)
    affects_salary = fields.Boolean(default=False)
