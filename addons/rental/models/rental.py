from odoo import models, fields, api
from datetime import datetime


class Rental(models.Model):
    _name = "rental.rental"
    _description = "Rental"

    vehicle_id = fields.Many2one("rental.vehicle", required=True)
    customer_name = fields.Char(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date()
    start_mileage = fields.Integer()
    end_mileage = fields.Integer()
    daily_rate = fields.Float()
    weekly_rate = fields.Float()
    total_amount = fields.Float(compute="_compute_total_amount", store=True)
    deposit_amount = fields.Float()

    state = fields.Selection([
        ("draft", "Draft"),
        ("active", "Active"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ], default="draft")

    @api.depends("start_date", "end_date", "daily_rate", "weekly_rate")
    def _compute_total_amount(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                days = (rec.end_date - rec.start_date).days + 1
                weeks = days // 7
                remaining_days = days % 7
                rec.total_amount = weeks * rec.weekly_rate + remaining_days * rec.daily_rate
            else:
                rec.total_amount = 0

    def action_start_rental(self):
        self.ensure_one()
        self.state = "active"
        self.start_mileage = self.vehicle_id.mileage
        self.vehicle_id.status = "rented"

    def action_end_rental(self):
        self.ensure_one()
        # self.end_mileage = end_mileage
        self.state = "done"
        self.vehicle_id.mileage = max(self.vehicle_id.mileage, self.end_mileage)
        self.vehicle_id.status = "available"

        # Обновить maintenance_status
        for status in self.vehicle_id.maintenance_status_ids:
            plan = self.vehicle_id.model_id.maintenance_plan_ids.filtered(lambda p: p.service_type == status.service_type)
            if not plan:
                continue
            # Проверяем, если пробег достиг интервала - обновляем last_service_mileage и last_service_date
            if status.next_service_mileage and self.vehicle_id.mileage >= status.next_service_mileage:
                status.last_service_mileage = self.vehicle_id.mileage
                status.last_service_date = fields.Date.today()
