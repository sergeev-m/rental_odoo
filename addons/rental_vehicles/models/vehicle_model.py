from odoo import models, fields, api
from odoo.exceptions import ValidationError


class VehicleModel(models.Model):
    _name = "rental_vehicles.vehicle.model"
    _description = "Vehicle Model"

    _name_manufacturer_id_unique = models.Constraint(
        'UNIQUE(name,manufacturer_id)',
        'Vehicle model name must be unique per manufacturer!'
    )

    name = fields.Char(required=True)
    manufacturer_id = fields.Many2one('rental_vehicles.manufacturer', required=True)
    vehicle_type_id = fields.Many2one("rental_vehicles.vehicle.type", string="Vehicle Type", required=True)
    maintenance_plan_ids = fields.One2many("rental_vehicles.maintenance.plan", "model_id", string="Maintenance Plan")

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
    tariff_ids = fields.Many2one('rental_vehicles.tariff')

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

    def action_view_tariffs(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Tarifs",
            "res_model": self['tariff_ids']._name,  # noqa
            "view_mode": "list,form",
            "domain": [("vehicle_model_id", "=", self.id)],
            "context": {
                'default_vehicle_model_id': self.id,
            },
        }


class Manufacturer(models.Model):
    _name = "rental_vehicles.manufacturer"
    _description = "Manufacturer"

    name = fields.Char(
        string='Name',
    )

    _name_unique = models.Constraint(
        'UNIQUE(name)', 'Manufacturer name must be unique!'
    )

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
