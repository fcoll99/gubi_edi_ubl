# Copyright 2021 ForgeFlow, S.L.
# License OPL-1
from lxml import etree

from odoo import _, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "base.ubl", "edi.exchange.consumer.mixin"]


    def generate_purchase_order_button(self):
        self._event("on_generate_purchase_order").notify(self)

    def _get_purchase_order_gubi_ubl_backend(self):
        partner = self.partner_id.commercial_partner_id
        backend_type = "gubi_ubl"
        exchange_code = "order_out"
        backend = self.env["edi.backend"].search(
            [
                ("backend_type_id.code", "=", backend_type),
                "|",
                ("partner_id", "=", partner.id),
                ("partner_id", "=", False),
            ],
        )
        # It is necessary to set an EDI Backend in the Purchase Exchange Type
        if len(backend) != 1:
            backend_list = backend
            for backend_rec in backend_list:
                exchange_type = self.env["edi.exchange.type"].search(
                    [
                        ("backend_type_id.code", "=", backend_type),
                        ("direction", "=", "output"),
                        ("code", "=", exchange_code),
                        ("backend_id", "=", backend_rec.id),
                    ]
                )
                if exchange_type:
                    backend = backend_rec
            if len(backend) != 1:
                raise UserError(
                    _(
                        "Multiple or no backends detected. "
                        "Check out the EDI configuration"
                    )
                )
        return backend

    def _ubl_get_seller_code_from_product(self, product):
        seller_code = False
        seller = self.partner_id
        if seller:
            sellers = product._select_seller(partner_id=seller,)
            if sellers:
                seller_code = sellers[0].product_code
        return seller_code

    def _ubl_get_customer_product_code(self, product, customer):
        return product.item_number
