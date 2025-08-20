from odoo import models, fields, api


class Tarif(models.Model):
    _name = "rental.tarif"
    _description = "Tarif"

    office_id = fields.Many2one(
        "rental.office",
        string="Office",
        required=True
    )

    vehicle_type_id = fields.Many2one(
        "rental.vehicle.type",
        string="Vehicle Type",
        required=True
    )
    
    price = fields.Monetary(
        string="Price",
        currency_field="currency_id",
        required=True
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True
    )

    @api.onchange("office_id")
    def _onchange_office_id_set_currency(self):
        """Автоматически ставим валюту из офиса"""
        if self.office_id and self.office_id.currency_id:
            self.currency_id = self.office_id.currency_id
