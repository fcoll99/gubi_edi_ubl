# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from odoo.addons.component.core import Component


class EdiPurchaseGenerate(Component):
    _name = "edi.output.generate.order.ubl"
    _inherit = "edi.component.output.mixin"
    _description = "Generates UBL Purchase Orders"
    _usage = "output.generate"
    _backend_type = "gubi_ubl"
    _exchange_type = "order_out"

    def generate(self):
        return self.generate_order_data()

    def generate_order_data(self):
        state = self.exchange_record.record.state
        if state == "draft":
            order_bytes = self.exchange_record.record.generate_ubl_xml_string("rfq")
        if state == "purchase":
            order_bytes = self.exchange_record.record.generate_ubl_xml_string("order")
        return order_bytes
