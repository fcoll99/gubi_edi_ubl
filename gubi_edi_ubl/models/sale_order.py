# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sps_order_create_date = fields.Date(help="SPSCommerce PO date")
    sps_client_order_ref = fields.Char(help="SPSCommerce additional order reference")
    sps_transport_method_code = fields.Selection(
        [
            ("A", "A: Air"),
            ("E", "E: Expedited Truck"),
            ("H", "H: Customer Pickup"),
            ("N", "N: Private Vessel (Direct to client - Ocean)"),
            ("O", "O: Containerized Ocean"),
            ("P", "P: Private Carrier (Direct to client - Air)"),
        ],
        help="Transport method for SPSCommerce",
    )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sps_sequence = fields.Integer(help="SPSCommerce required line reference")
