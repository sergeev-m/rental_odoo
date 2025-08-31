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

    min_days = fields.Integer(string="Минимум дней", required=True)
    max_days = fields.Integer(string="Максимум дней", required=True)

    def _compute_display_name(self):
        for rec in self:
            values = (rec.price, rec.currency_id.symbol)
            placeholder = ' '.join(['%s'] * len(values))
            rec.display_name = placeholder % tuple(values) if values else False

    @api.onchange("office_id")
    def _onchange_office_id_set_currency(self):
        """Автоматически ставим валюту из офиса"""
        if self.office_id and self.office_id.currency_id:
            self.currency_id = self.office_id.currency_id
