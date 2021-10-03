# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from lxml import etree

from odoo.addons.component.core import Component


class EdiOrderProcess(Component):
    _name = "edi.input.process.order.ubl"
    _inherit = "edi.component.input.mixin"
    _description = "Processes UBL Order (ISO 850)"
    _usage = "input.process"
    _backend_type = "gubi_ubl"
    _exchange_type = "order_in"

    def process(self):
        file_content = self.exchange_record._get_file_content()
        xml_root = etree.fromstring(file_content)
        so = self._parse_xml_file(xml_root)
        self.exchange_record.write({"model": "sale.order", "res_id": so.id})

    def _parse_xml_file(self, xml_root):
        return self.env["sale.order.import"].parse_ubl_sale_order(xml_root)
