# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    sps_customer_vendor_code = fields.Char()
    sps_transaction_code = fields.Char()

    edi_catalogue_ids = fields.One2many(
        comodel_name="edi.product.catalogue", inverse_name="partner_id"
    )
    edi_catalogue_count = fields.Integer(compute="_compute_edi_catalogue_count")

    def _compute_edi_catalogue_count(self):
        for rec in self:
            rec.edi_catalogue_count = len(rec.edi_catalogue_ids)

    def action_get_edi_catalogue(self):
        action = self.env.ref("gubi_edi_ubl.product_catalogue_action")
        result = action.read()[0]
        catalogues = self.mapped("edi_catalogue_ids")
        if len(catalogues) > 1:
            result["domain"] = [("id", "in", catalogues.ids)]
        else:
            res = self.env.ref("gubi_edi_ubl.product_catalogues_form", False)
            result["views"] = [(res and res.id or False, "form")]
            result["res_id"] = catalogues.id
        return result
