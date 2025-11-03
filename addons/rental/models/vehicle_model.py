from odoo import models, fields, api
from odoo.exceptions import ValidationError


class VehicleModel(models.Model):
    _name = "rental.vehicle.model"
    _description = "Vehicle Model"

    _sql_constraints = [
        (
            'unique_vehicle_model_name_manufacturer',
            'UNIQUE (name, manufacturer_id)',
            'Vehicle model name must be unique per manufacturer!'
        ),
    ]

    name = fields.Char(required=True)
    manufacturer_id = fields.Many2one('rental.manufacturer', required=True)
    vehicle_type_id = fields.Many2one("rental.vehicle.type", string="Vehicle Type", required=True)
    maintenance_plan_ids = fields.One2many("rental.vehicle.model.maintenance", "model_id", string="Maintenance Plan")

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

    def _compute_display_name(self):
        for rec in self:
            values = (
                rec.manufacturer_id.name,
                rec.name,
            )
            placeholder = ' '.join(['%s'] * len(values))
            rec.display_name = placeholder % values if values else False


    @api.constrains('name', 'manufacturer_id')
    def _check_unique_name_manufacturer(self):
        for rec in self:
            if not rec.name:
                continue

            domain = [
                ('id', '!=', rec.id),
                ('manufacturer_id', '=', rec.manufacturer_id.id),
                ('name', '=ilike', rec.name.strip()),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    f'The vehicle model "{rec.name}" already exists for this manufacturer.'
                )


class VehicleModelMaintenance(models.Model):
    _name = "rental.vehicle.model.maintenance"
    _description = "Vehicle Model Maintenance Plan"

    model_id = fields.Many2one("rental.vehicle.model", required=True, ondelete='cascade')
    service_type_id = fields.Many2one("rental.service.type", string="Service Type", required=True)
    interval_km = fields.Integer("Interval (km)")
    interval_days = fields.Integer("Interval (days)")

    # 🔔 поля напоминаний
    remind_before_km = fields.Integer(
        "Remind Before (km)",
        default=100,
        help="За сколько км до наступления интервала подсвечивать"
    )
    remind_before_days = fields.Integer(
        "Remind Before (days)",
        default=7,
        help="За сколько дней до наступления интервала подсвечивать"
    )


class Manufacturer(models.Model):
    _name = "rental.manufacturer"
    _description = "Manufacturer"

    name = fields.Char(
        string='Name',
    )

    _sql_constraints = [
        ('unique_manufacturer_name', 'unique(name)', 'Manufacturer name must be unique!')
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if not rec.name:
                continue

            domain = [
                ('id', '!=', rec.id),
                ('name', '=ilike', rec.name.strip()),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    f'The manufacturer "{rec.name}" already exists.'
                )
