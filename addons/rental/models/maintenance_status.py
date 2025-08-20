from odoo import models, fields, api
from datetime import timedelta


class MaintenanceStatus(models.Model):
    _name = "rental.maintenance.status"
    _description = "Maintenance Status for Vehicle"

    vehicle_id = fields.Many2one("rental.vehicle", required=True, ondelete='cascade')
    service_type = fields.Selection([
        ("oil", "Oil Change"),
        ("brake_pads", "Brake Pads Replacement"),
        ("belt", "Drive Belt Replacement"),
        ("custom", "Custom Service"),
    ], required=True)
    last_service_mileage = fields.Integer()
    last_service_date = fields.Date()
    next_service_mileage = fields.Integer(compute="_compute_next_service", store=True)
    next_service_date = fields.Date(compute="_compute_next_service", store=True)

    @api.depends("last_service_mileage", "last_service_date", "service_type", "vehicle_id.model_id")
    def _compute_next_service(self):
        for rec in self:
            plan = rec.vehicle_id.model_id.maintenance_plan_ids.filtered(lambda p: p.service_type == rec.service_type)
            if plan:
                rec.next_service_mileage = rec.last_service_mileage + plan.interval_km if plan.interval_km else False
                rec.next_service_date = rec.last_service_date + timedelta(days=plan.interval_days) if plan.interval_days and rec.last_service_date else False
            else:
                rec.next_service_mileage = False
                rec.next_service_date = False
