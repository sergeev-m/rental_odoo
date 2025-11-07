import requests
import base64

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class Renter(models.Model):
    _name = 'rental.renter'
    _description = 'Renter'

    name = fields.Char("Full Name", required=True)
    country_id = fields.Many2one("res.country", string="Country")
    phone = fields.Char("Phone Number")
    passport_number = fields.Char("Passport Number")
    driver_license = fields.Char("Driver License Number")

    passport_image = fields.Binary("Passport Image")
    license_image = fields.Binary("Driver License Image")
    image = fields.Binary("Image")

    order_ids = fields.One2many("rental.order", "renter_id", string="Rentals")
    total_rentals = fields.Integer("Total Rentals", compute="_compute_total_rentals", store=True)
    total_spent = fields.Monetary("Total Spent", compute="_compute_total_spent", store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    active = fields.Boolean(default=True)
    note = fields.Text("Notes")

    @api.depends("order_ids.state")
    def _compute_total_rentals(self):
        for rec in self:
            rec.total_rentals = len(rec.order_ids.filtered(lambda r: r.state == "done"))

    @api.depends("order_ids.amount_total", "order_ids.state")
    def _compute_total_spent(self):
        for rec in self:
            rec.total_spent = sum(
                rec.order_ids
                .filtered(lambda r: r.state == "done")
                .mapped('amount_total')
            )
