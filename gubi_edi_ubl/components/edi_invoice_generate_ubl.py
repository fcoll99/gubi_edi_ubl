# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from odoo.addons.component.core import Component


class EdiInvoiceGenerate(Component):
    _name = "edi.output.generate.invoice.ubl"
    _inherit = "edi.component.output.mixin"
    _description = "Generates UBL Invoice (ISO 810)"
    _usage = "output.generate"
    _backend_type = "gubi_ubl"
    _exchange_type = "invoice_out"

    def generate(self):
        return self.generate_invoice_data()

    def generate_invoice_data(self):
        invoice_file_bytes = self.exchange_record.record.generate_ubl_xml_string()
        return invoice_file_bytes
