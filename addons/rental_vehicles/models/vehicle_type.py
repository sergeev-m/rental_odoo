from odoo import models, fields, api
from odoo.exceptions import ValidationError


class VehicleType(models.Model):
    _name = "rental_vehicles.vehicle.type"
    _description = "Vehicle Type"

    name = fields.Char(string="Type Name", required=True)

    _vehicle_type_name_unique = models.Constraint(
        'UNIQUE(name)', 'Vehicle type name must be unique!'
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
                    f'The vehicle type "{rec.name}" already exists.'
                )
