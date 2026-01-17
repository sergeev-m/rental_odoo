from odoo import models, fields


class VehicleImage(models.Model):
    _name = "rental_vehicles.vehicle.image"
    _description = "Vehicle image"
    _order = 'sequence, id asc'

    vehicle_model_id = fields.Many2one(
        "rental_vehicles.vehicle.model",
        required=True,
        ondelete="cascade",
    )

    image_1920 = fields.Image(
        string="Image",
        required=True,
    )
    sequence = fields.Integer(default=10)
