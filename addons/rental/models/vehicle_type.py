from odoo import models, fields


class VehicleType(models.Model):
    _name = "rental.vehicle.type"
    _description = "Vehicle Type"

    name = fields.Char(string="Type Name", required=True)
