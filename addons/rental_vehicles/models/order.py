from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError


class RentalOrder(models.Model):
    _name = "rental_vehicles.order"
    _description = "Rental Order"
    _order = "start_date desc"

    office_id = fields.Many2one('rental_vehicles.office')
    vehicle_id = fields.Many2one(
        "rental_vehicles.vehicle",
        required=True,
        domain="[('office_id', '=', office_id), ('status', '=', 'available')]"
    )
    renter_id = fields.Many2one('rental_vehicles.renter')
    rental_days = fields.Integer(required=True, default=1)
    rental_hours = fields.Integer()
    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(string="End Date", compute="_compute_end_date", store=True)
    extra_expenses = fields.Float(string="Extra Expenses", default=0.0)
    start_mileage = fields.Integer()
    end_mileage = fields.Integer()
    currency_id = fields.Many2one(related='tariff_id.currency_id')
    amount_total = fields.Monetary(currency_field="currency_id", compute="_compute_amount_total", store=True)
    deposit_amount = fields.Float()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        index=True
    )
    vehicle_type_id = fields.Many2one(
        related="vehicle_id.vehicle_type_id",
        store=True,
        readonly=True,
    )
    vehicle_model_id = fields.Many2one(
        related="vehicle_id.model_id",
        store=True,
        readonly=True,
    )
    tariff_id = fields.Many2one(
        "rental_vehicles.tariff",
        string="Tariff",
        required=True,
        domain="[('office_id', '=', office_id), ('vehicle_model_id', '=', vehicle_model_id)]",
    )
    tariff_price = fields.Monetary(
        string="Tariff Price",
        currency_field="currency_id",
        # readonly=True
    )

    @api.onchange('tariff_id')
    def _onchange_tarif_id(self):
        if self.state =='done':
            return

        if self.tariff_id:
            self.tariff_price = self.tariff_id.price_per_unit

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        self.start_mileage = False
        if self.vehicle_id:
            self.start_mileage = self.vehicle_id.mileage
    
    @api.onchange('rental_hours')
    def _onchange_rental_hours(self):
        if self.rental_days:
            return

        if not (self.vehicle_id and self.rental_hours):
            return

        self.tariff_id = False
        tariff = self.env['rental_vehicles.tariff'].search([
            ('vehicle_model_id', '=', self.vehicle_model_id.id),
            ('period_type', '=', 'hour'),
        ], limit=1)
        self.tariff_id = tariff.id if tariff else False


    @api.onchange('rental_days', 'vehicle_id')
    def _onchange_rental_days(self):
        self.tariff_id = False

        if not (self.vehicle_id and self.rental_days):
            return

        tariff = self.env['rental_vehicles.tariff'].search([
            ('vehicle_model_id', '=', self.vehicle_model_id.id),
            ('period_type', '=', 'day'),
            ('min_period', '<=', self.rental_days),
        ], order='min_period desc', limit=1)

        self.tariff_id = tariff.id if tariff else False

    @api.depends("start_date", "rental_days")
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date:
                end_dt = rec.start_date + timedelta(days=rec.rental_days)

                if end_dt.minute and end_dt.minute >= 5:
                    end_dt = end_dt + timedelta(hours=1)
                
                end_dt = end_dt.replace(minute=0, second=0, microsecond=0)
                rec.end_date = end_dt
            else:
                rec.end_date = False
        
    @api.depends('rental_days', 'rental_hours', 'tariff_price', 'extra_expenses')
    def _compute_amount_total(self):
        for rec in self:
            total = 0

            if rec.tariff_price and rec.rental_days:
                total = rec.rental_days * rec.tariff_price

            if rec.rental_hours:
                tariff_hour = rec.env['rental_vehicles.tariff'].search([
                    ('vehicle_model_id', '=', rec.vehicle_id.model_id.id),
                    ('period_type', '=', 'hour'),
                ], limit=1)
                if tariff_hour:
                    total += rec.rental_hours * tariff_hour.price_per_unit
            
            if rec.extra_expenses:
                total += rec.extra_expenses

            rec.amount_total = total

    def action_start_rental(self):
        for rec in self:
            if rec.state != "draft":
                raise ValidationError("должен быть статус draft")
        self.state = "active"
        self.vehicle_id.status = "rented"

    def action_end_rental(self):
        for rec in self:
            if rec.state != "active":
                raise ValidationError("Завершить можно только активную аренду.")
        self.state = "done"
        self.vehicle_id.mileage = max(self.vehicle_id.mileage, self.end_mileage)
        self.vehicle_id.status = "available"

    def action_cancel(self):
        for rec in self:
            if rec.state not in ("draft", "active"):
                raise ValidationError("Отменить можно только черновик или активную аренду.")
            if rec.state == "active":
                rec.vehicle_id.status = "available"
            rec.state = "cancelled"

    def action_open_photo_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Recognize Renter from Photo",
            "res_model": "rental_vehicles.renter.photo.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }


    def _compute_display_name(self):
        for rec in self:
            values = (
                rec.id,
                rec.vehicle_id.name,
            )
            placeholder = ' '.join(['%s'] * len(values))
            rec.display_name = placeholder % tuple(values) if values else False
