from odoo import models, fields, api

from datetime import timedelta
from odoo.exceptions import ValidationError


class RentalTrainingLesson(models.Model):
    _name = "rental_vehicles.training.lesson"
    _description = "Moto Training Lesson"
    _inherit = ['rental_vehicles.office.mixin']

    name = fields.Char(
        string="Subject",
        required=True,
        store=True,
        default="Training Lesson"
    )

    instructor_id = fields.Many2one(
        "res.users",
        string="Instructor",
        default=lambda self: self.env.user.id
    )
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(
        compute="_compute_end_datetime",
        store=True,
    )
    duration_hours = fields.Float(
        string="Duration",
        default=1.0,
    )
    price_per_hour = fields.Monetary(default=60)
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

    @api.depends("start_datetime", "duration_hours")
    def _compute_end_datetime(self):
        for rec in self:
            if rec.start_datetime and rec.duration_hours:
                rec.end_datetime = rec.start_datetime + timedelta(hours=rec.duration_hours)
            else:
                rec.end_datetime = False

    @api.depends('duration_hours', 'price_per_hour')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.duration_hours * rec.price_per_hour

    @api.constrains("start_datetime", "end_datetime")
    def _check_lesson_dates(self):
        for rec in self:
            if (
                rec.start_datetime
                and rec.end_datetime
                and rec.end_datetime <= rec.start_datetime
            ):
                raise ValidationError("End time must be later than start time.")

    @api.model
    def _round_to_next_hour(self, dt):
        dt = fields.Datetime.to_datetime(dt) if dt else fields.Datetime.now()
        dt = dt.replace(minute=0, second=0, microsecond=0)

        return dt

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)

        start_dt = vals.get("start_datetime")
        start_dt = self._round_to_next_hour(start_dt)
        vals["start_datetime"] = start_dt
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("start_datetime"):
                start_dt = self._round_to_next_hour(vals["start_datetime"])
                vals["start_datetime"] = start_dt

        return super().create(vals_list)

    def action_plan(self):
        self.write({"state": "planned"})

    def action_done(self):
        self.write({"state": "done"})

    def action_no_show(self):
        self.write({"state": "no_show"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    @api.depends("name", "state")
    def _compute_display_name(self):
        state_map = {
            "draft": "Draft",
            "planned": "Planned",
            "done": "Done",
            "cancelled": "Cancelled",
            "no_show": "No Show",
        }

        for rec in self:
            state_label = state_map.get(rec.state, rec.state or "")
            rec.display_name = f"{rec.name} · {state_label}" if state_label else rec.name
