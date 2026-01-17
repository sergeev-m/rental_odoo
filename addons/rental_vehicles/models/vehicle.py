from odoo import models, fields, api
from odoo.tools import format_date


class Vehicle(models.Model):
    _name = "rental_vehicles.vehicle"
    _description = "Vehicle"
    _order="sequence"

    name = fields.Char(compute='_compute_name', store="True")
    sequence = fields.Integer(string="Sequence")
    model_id = fields.Many2one("rental_vehicles.vehicle.model", string="Model", required=True)
    plate_number = fields.Char(required=True)
    year = fields.Char()
    purchase_price = fields.Integer()
    mileage = fields.Integer(string="Current Mileage", default=0)
    office_id = fields.Many2one("rental_vehicles.office", string="Office", required=True)
    vehicle_type_id = fields.Many2one(related='model_id.vehicle_type_id')
    status = fields.Selection([
        ("available", "Available"),
        ("rented", "Rented"),
        ("booked", "Booked"),
        ("maintenance", "Maintenance"),
        ("inactive", "Inactive"),
    ], default="available")

    maintenance_due_ids = fields.One2many(
        "rental_vehicles.maintenance.due",
        "vehicle_id",
        string="Upcoming Maintenance",
        readonly=True
    )
    maintenance_ids = fields.One2many("rental_vehicles.maintenance", "vehicle_id", string="Maintenance")
    order_ids = fields.One2many("rental_vehicles.order", "vehicle_id", string="Заказы")

    maintenance_due_summary = fields.Json(
        string="Upcoming Maintenance Summary",
        compute="_compute_maintenance_due_summary",
        store=False,
    )

    image_ids = fields.One2many(
        "rental_vehicles.vehicle.image",
        "vehicle_id",
        string="Images",
    )

    @api.depends('maintenance_due_ids', 
                 'maintenance_due_ids.service_type_id',
                 'maintenance_due_ids.next_service_mileage',
                 'maintenance_due_ids.next_service_date',
                 'maintenance_due_ids.km_to_due',
                 'maintenance_due_ids.days_to_due',
                 'maintenance_due_ids.is_due',
                 'maintenance_due_ids.overdue')
    def _compute_maintenance_due_summary(self):
        for vehicle in self:
            lines = []
            for line in vehicle.maintenance_due_ids:
                next_service_date_str = ''
                if line.next_service_date:
                    next_service_date_str = format_date(
                        line.env,
                        line.next_service_date,
                        date_format='MMM yy'
                    )
                lines.append({
                    "service": line.service_type_id.display_name,
                    "next_service": line.next_service_mileage or next_service_date_str,
                    "remaining": line.km_to_due or f'{line.days_to_due} days',
                    'is_due': line.is_due,
                    "overdue": line.overdue,
                })
            vehicle.maintenance_due_summary = lines

    @api.depends('model_id.manufacturer_id.name', 'model_id.name', 'plate_number')
    def _compute_name(self):
        for rec in self:
            values = (
                rec.model_id.manufacturer_id.name,
                rec.model_id.name,
                rec.plate_number
            )
            placeholder = ' '.join(['%s'] * len(values))
            rec.name = placeholder % values if values else False

    def write(self, vals):
        res = super().write(vals)
        if 'mileage' in vals:
            self.flush_recordset()
        return res

    def action_view_orders(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Заказы",
            "res_model": self['order_ids']._name,  # noqa
            "view_mode": "list,form",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {
                'default_vehicle_id': self.id,
                'default_office_id': self.office_id.id,
            },
        }
