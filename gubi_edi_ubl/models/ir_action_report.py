# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def is_ubl_xml_to_embed_in_invoice(self):
        res = super().is_ubl_xml_to_embed_in_invoice()
        # WARNING: this overrides method in `account_invoice_ubl` module.
        # The purpose is to disable the auto-embedding of ubl in pdf reports.
        # It is not desired by default, as Gubi UBL messages will be shared
        # using EDI app.
        return res and False
