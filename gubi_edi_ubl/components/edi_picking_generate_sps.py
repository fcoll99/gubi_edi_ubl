from odoo.addons.component.core import Component


class EdiPickingGenerate(Component):
    _name = "edi.output.generate.picking.sps"
    _inherit = "edi.component.output.mixin"
    _description = "Generates stock picking in edi format"
    _usage = "output.generate"
    _backend_type = "sps_ubl"
    _exchange_type = "picking_out"

    def generate(self):
        return self.generate_picking_data()

    def generate_picking_data(self):
        picking_bytes = self.exchange_record.record.generate_picking_ubl_xml_string()
        return picking_bytes
