from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RentalTrainingLesson(models.Model):
    _name = "rental_vehicles.training.lesson"
    _description = "Moto Training Lesson"
    _inherit = ['rental_vehicles.office.mixin']

    # name = fields.Char(compute="_compute_name", store=True)

    partner_id = fields.Many2one("res.partner", string="Student")
    instructor_id = fields.Many2one("res.users", string="Instructor")
    # vehicle_id = fields.Many2one("rental.vehicle", string="Vehicle")

    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(required=True)
    duration_hours = fields.Float(compute="_compute_duration_hours", store=True)

    price_per_hour = fields.Monetary()
    amount_total = fields.Monetary(compute="_compute_amount_total", store=True)
    currency_id = fields.Many2one(related='office_id.currency_id')

    state = fields.Selection([
        ("draft", "Draft"),
        ("planned", "Planned"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ], default="draft", tracking=True)

    notes = fields.Text()

    @api.depends('duration_hours', 'price_per_hour')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.duration_hours * rec.price_per_hour

    @api.depends("start_datetime", "end_datetime")
    def _compute_duration_hours(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.duration_hours = max(delta.total_seconds() / 3600.0, 0.0)
            else:
                rec.duration_hours = 0.0

    @api.constrains("start_datetime", "end_datetime")
    def _check_lesson_dates(self):
        for rec in self:
            if (
                rec.start_datetime
                and rec.end_datetime
                and rec.end_datetime <= rec.start_datetime
            ):
                raise ValidationError("End time must be later than start time.")
