from odoo import models, fields, api


class Vehicle(models.Model):
    _name = "rental.vehicle"
    _description = "Vehicle"

    name = fields.Char(required=True)
    model_id = fields.Many2one("rental.vehicle.model", string="Model", required=True)
    plate_number = fields.Char()
    serial_number = fields.Char()
    mileage = fields.Integer(string="Current Mileage", default=0)
    office_id = fields.Many2one("rental.office", string="Office")
    status = fields.Selection([
        ("available", "Available"),
        ("rented", "Rented"),
        ("booked", "Booked"),
        ("maintenance", "Maintenance"),
        ("inactive", "Inactive"),
    ], default="available")

    maintenance_status_ids = fields.One2many("rental.maintenance.status", "vehicle_id", string="Maintenance Status")

    @api.model
    def create(self, vals):
        vehicle = super().create(vals)
        # Создать статусы обслуживания на основе плана модели
        for plan in vehicle.model_id.maintenance_plan_ids:
            self.env["rental.maintenance.status"].create({
                "vehicle_id": vehicle.id,
                "service_type": plan.service_type,
                "last_service_mileage": 0,
                "last_service_date": False,
            })
        return vehicle
