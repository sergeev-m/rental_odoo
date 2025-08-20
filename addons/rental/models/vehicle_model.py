from odoo import models, fields


class VehicleModel(models.Model):
    _name = "rental.vehicle.model"
    _description = "Vehicle Model"

    name = fields.Char(required=True)
    manufacturer = fields.Many2one('rental.manufacturer', required=True)
    vehicle_type_id = fields.Many2one("rental.vehicle.type", string="Vehicle Type", required=True)
    maintenance_plan_ids = fields.One2many("rental.vehicle.model.maintenance", "model_id", string="Maintenance Plan")
    year = fields.Char()

    displacement = fields.Float()
    max_power = fields.Float()
    top_speed = fields.Integer()
    transmission = fields.Selection([
        ("automatic", "Automatic"),
        ("manual", "Manual"),
    ])
    transmission_type = fields.Selection([
        ('cvt', 'CVT'),
    ])
    weight = fields.Float()
    image = fields.Binary(
        string='Image',
        attachment=True,
    )


class VehicleModelMaintenance(models.Model):
    _name = "rental.vehicle.model.maintenance"
    _description = "Vehicle Model Maintenance Plan"

    model_id = fields.Many2one("rental.vehicle.model", required=True, ondelete='cascade')
    service_type = fields.Selection([
        ("oil", "Oil Change"),
        ("brake_pads", "Brake Pads Replacement"),
        ("belt", "Drive Belt Replacement"),
        ("custom", "Custom Service"),
    ], required=True)
    interval_km = fields.Integer("Interval (km)")
    interval_days = fields.Integer("Interval (days)")


class Manufacturer(models.Model):
    _name = "rental.manufacturer"
    _description = "Manufacturer"

    name = fields.Char(
        string='Name',
    )
