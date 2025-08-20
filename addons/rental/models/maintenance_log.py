from odoo import models, fields


class MaintenanceLog(models.Model):
    _name = "rental.maintenance.log"
    _description = "Maintenance Log"

    vehicle_id = fields.Many2one("rental.vehicle", required=True)
    service_type = fields.Selection([
        ("oil", "Oil Change"),
        ("brake_pads", "Brake Pads Replacement"),
        ("belt", "Drive Belt Replacement"),
        ("custom", "Custom Service"),
    ], required=True)
    service_date = fields.Date(required=True)
    mileage = fields.Integer(required=True)
    cost = fields.Float(string="Cost", default=0.0)
    notes = fields.Text()
