from odoo import models, fields, api
from odoo.exceptions import UserError
import base64, requests
import logging


_logger = logging.Logger(__name__)


class RenterPhotoWizard(models.TransientModel):
    _name = "rental.renter.photo.wizard"
    _description = "Renter Photo Upload Wizard"

    image = fields.Binary("Image", required=True)
    image_filename = fields.Char()
    renter_id = fields.Many2one("rental.renter", string="Detected Renter", readonly=True)
    name = fields.Char("Name")
    passport_number = fields.Char("Passport Number")
    driver_license = fields.Char("Driver License")
    phone = fields.Char("Phone")
    country = fields.Char("Country")
    order_id = fields.Many2one("rental.order", string="Order")

    def action_extract_data(self):
        """Отправляем фото в OCR-сервис"""
        if not self.image:
            raise UserError("Please upload a image before extracting data.")

        try:
            response = requests.post(
                "http://rental_ocr:8000/ocr/extract",
                files={"file": ("photo.jpg", base64.b64decode(self.image))}
            )
            response.raise_for_status()
            data = response.json()
            _logger.info(data)
        except Exception as e:
            raise UserError(f"OCR service error: {str(e)}")

        # Заполняем распознанные данные
        self.name = data.get("name")
        self.passport_number = data.get("passport_number")
        self.driver_license = data.get("driver_license")
        self.country = data.get("country")

        # Ищем существующего арендатора
        renter = self.env["rental.renter"].search([
            "|",
            ("passport_number", "=", self.passport_number),
            ("driver_license", "=", self.driver_license)
        ], limit=1)

        if renter:
            self.renter_id = renter.id

        return {
            "type": "ir.actions.act_window",
            "res_model": "rental.renter.photo.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def action_confirm(self):
        """Создать или выбрать арендатора и присвоить заказу"""
        if not self.order_id:
            raise UserError("Order not found.")

        if not self.renter_id:
            renter = self.env["rental.renter"].create({
                "name": self.name or "Unknown",
                "passport_number": self.passport_number,
                "driver_license": self.driver_license,
                # "country": self.country,
                "phone": self.phone,
                "image": self.image,
            })
        else:
            renter = self.renter_id

        self.order_id.renter_id = renter.id
        return {"type": "ir.actions.act_window_close"}
