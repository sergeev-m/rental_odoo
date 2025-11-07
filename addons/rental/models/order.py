from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError


class RentalOrder(models.Model):
    _name = "rental.order"
    _description = "Rental Order"
    _order = "start_date desc"

    office_id = fields.Many2one('rental.office')
    vehicle_id = fields.Many2one(
        "rental.vehicle",
        required=True,
        domain="[('office_id', '=', office_id), ('status', '=', 'available')]"
    )
    customer_name = fields.Char()
    renter_id = fields.Many2one('rental.renter')
    rental_days = fields.Integer(required=True, default=1)
    rental_hours = fields.Integer()
    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(string="End Date", compute="_compute_end_date", store=True)
    extra_expenses = fields.Float(string="Extra Expenses", default=0.0)


    start_mileage = fields.Integer()
    end_mileage = fields.Integer()
    currency_id = fields.Many2one(related='tarif_id.currency_id')
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

    tarif_id = fields.Many2one(
        "rental.tarif",
        string="Tarif",
        required=True,
        domain="[('office_id', '=', office_id), ('vehicle_model_id', '=', vehicle_model_id)]",
    )
    tarif_price = fields.Monetary(
        string="Tariff Price",
        currency_field="currency_id",
        # readonly=True
    )

    @api.onchange('tarif_id')
    def _onchange_tarif_id(self):
        if self.tarif_id:
            self.tarif_price = self.tarif_id.price_per_unit

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

        self.tarif_id = False
        tarif = self.env['rental.tarif'].search([
            ('vehicle_model_id', '=', self.vehicle_model_id.id),
            ('period_type', '=', 'hour'),
        ], limit=1)
        self.tarif_id = tarif.id if tarif else False


    @api.onchange('rental_days', 'vehicle_id')
    def _onchange_rental_days(self):
        self.tarif_id = False

        if not (self.vehicle_id and self.rental_days):
            return

        tarif = self.env['rental.tarif'].search([
            ('vehicle_model_id', '=', self.vehicle_model_id.id),
            ('period_type', '=', 'day'),
            ('min_period', '<=', self.rental_days),
        ], order='min_period desc', limit=1)

        self.tarif_id = tarif.id if tarif else False

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
        
    @api.depends('rental_days', 'rental_hours', 'tarif_price', 'extra_expenses')
    def _compute_amount_total(self):
        for rec in self:
            total = 0

            if rec.tarif_price and rec.rental_days:
                total = rec.rental_days * rec.tarif_price

            if rec.rental_hours:
                tarif_hour = rec.env['rental.tarif'].search([
                    ('vehicle_model_id', '=', rec.vehicle_id.model_id.id),
                    ('period_type', '=', 'hour'),
                ], limit=1)
                if tarif_hour:
                    total += rec.rental_hours * tarif_hour.price_per_unit
            
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
            "res_model": "rental.renter.photo.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }