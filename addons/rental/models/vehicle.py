from odoo import models, fields


class Vehicle(models.Model):
    _name = "rental.vehicle"
    _description = "Vehicle"

    model_id = fields.Many2one("rental.vehicle.model", string="Model", required=True)
    plate_number = fields.Char(required=True)
    year = fields.Char()
    purchase_price = fields.Integer()
    mileage = fields.Integer(string="Current Mileage", default=0)
    office_id = fields.Many2one("rental.office", string="Office", required=True)
    vehicle_type_id = fields.Many2one(related='model_id.vehicle_type_id')
    status = fields.Selection([
        ("available", "Available"),
        ("rented", "Rented"),
        ("booked", "Booked"),
        ("maintenance", "Maintenance"),
        ("inactive", "Inactive"),
    ], default="available")

    maintenance_due_ids = fields.One2many(
        "rental.maintenance.due",
        "vehicle_id",
        string="Upcoming Maintenance",
        readonly=True
    )
    maintenance_log_ids = fields.One2many("rental.maintenance.log", "vehicle_id", string="Maintenance Logs")
    order_ids = fields.One2many("rental.order", "vehicle_id", string="Заказы")

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

    def _compute_display_name(self):
        for rec in self:
            values = (rec.model_id.name, rec.plate_number)
            placeholder = ' '.join(['%s'] * len(values))
            rec.display_name = placeholder % values if values else False
