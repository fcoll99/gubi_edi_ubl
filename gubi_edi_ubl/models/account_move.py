# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

import logging

from lxml import etree

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round

logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "base.ubl"]

    def _get_account_move_gubi_ubl_backend(self):
        partner = self.partner_id.commercial_partner_id
        backend_type = "gubi_ubl"
        exchange_code = "invoice_out"
        backend = self.env["edi.backend"].search(
            [
                ("backend_type_id.code", "=", backend_type),
                "|",
                ("partner_id", "=", partner.id),
                ("partner_id", "=", False),
            ],
        )
        # It is necessary to set an EDI Backend in the Invoice Exchange Type
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
        return product.item_number

    def _ubl_get_customer_product_code(self, product, customer):
        """Overwrite the method and return the one needed"""
        customer_code = False
        if customer:
            customers = product._select_customerinfo(
                partner=customer.commercial_partner_id,
            )
            if customers:
                customer_code = customers[0].product_code
        return customer_code

    def _ubl_get_invoice_type_code(self):
        # TODO: establish when it is DR and when it is CR
        return "DR"

    def _ubl_get_order_reference(self):
        sale_order = self.invoice_line_ids.sale_line_ids.mapped("order_id")
        client_ref = sale_order.client_order_ref
        return client_ref

    def _ubl_get_customer_assigned_id(self, partner):
        return self.partner_id.commercial_partner_id.sps_customer_vendor_code

    def _ubl_add_order_reference(self, parent_node, ns, version="2.1"):
        # This is OVERWRITING the original method
        super(AccountMove, self)._ubl_add_order_reference(parent_node, ns, version)
        # START OF CHANGES
        order_ref = parent_node.find(ns["cac"] + "OrderReference")
        sale_order = self.invoice_line_ids.sale_line_ids.mapped("order_id")

        if sale_order.sps_order_create_date:
            order_date = etree.SubElement(order_ref, ns["cbc"] + "IssueDate")
            order_date.text = sale_order.sps_order_create_date.strftime("%Y-%m-%d")
        if sale_order.sps_client_order_ref:
            customer_order_number = etree.SubElement(
                order_ref, ns["cbc"] + "CustomerReference"
            )
            customer_order_number.text = sale_order.sps_client_order_ref
        # END OF CHANGES

    def _ubl_add_invoice_line(self, parent_node, iline, line_number, ns, version="2.1"):
        # This is OVERWRITING the original method in base_ubl
        self.ensure_one()
        cur_name = self.currency_id.name
        line_root = etree.SubElement(parent_node, ns["cac"] + "InvoiceLine")
        dpo = self.env["decimal.precision"]
        qty_precision = dpo.precision_get("Product Unit of Measure")
        price_precision = dpo.precision_get("Product Price")
        account_precision = self.currency_id.decimal_places
        line_id = etree.SubElement(line_root, ns["cbc"] + "ID")
        line_id.text = str(line_number)
        uom_unece_code = False
        # START OF CHANGES
        sale_line = iline.sale_line_ids
        sequence_id = etree.SubElement(line_root, ns["cbc"] + "UUID")
        sequence_id.text = str(sale_line.sps_sequence)
        # END OF CHANGES
        # product_uom_id is not a required field on account.move.line
        if iline.product_uom_id.unece_code:
            uom_unece_code = iline.product_uom_id.unece_code
            quantity = etree.SubElement(
                line_root, ns["cbc"] + "InvoicedQuantity", unitCode=uom_unece_code
            )
        else:
            quantity = etree.SubElement(line_root, ns["cbc"] + "InvoicedQuantity")
        qty = iline.quantity
        quantity.text = "%0.*f" % (qty_precision, qty)
        line_amount = etree.SubElement(
            line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_amount.text = "%0.*f" % (account_precision, iline.price_subtotal)
        self._ubl_add_invoice_line_tax_total(iline, line_root, ns, version=version)
        self._ubl_add_item(
            iline.name,
            iline.product_id,
            line_root,
            ns,
            type_="sale",
            customer=self.partner_id,
            version=version,
        )
        price_node = etree.SubElement(line_root, ns["cac"] + "Price")
        price_amount = etree.SubElement(
            price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
        )
        price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        if not float_is_zero(qty, precision_digits=qty_precision):
            price_unit = float_round(
                iline.price_subtotal / float(qty), precision_digits=price_precision
            )
        price_amount.text = "%0.*f" % (price_precision, price_unit)
        if uom_unece_code:
            base_qty = etree.SubElement(
                price_node, ns["cbc"] + "BaseQuantity", unitCode=uom_unece_code
            )
        else:
            base_qty = etree.SubElement(price_node, ns["cbc"] + "BaseQuantity")
        base_qty.text = "%0.*f" % (qty_precision, qty)
        # START OF CHANGES
        price_extension = etree.SubElement(line_root, ns["cac"] + "ItemPriceExtension")

        prec = self.currency_id.decimal_places
        price = iline.price_unit * (1 - (iline.discount or 0.0) / 100.0)

        res_taxes = iline.tax_ids.compute_all(
            price,
            quantity=iline.quantity,
            product=iline.product_id,
            partner=self.partner_id,
        )
        tax_total = float_round(
            res_taxes["total_included"] - res_taxes["total_excluded"],
            precision_digits=prec,
        )
        line_total = iline.price_subtotal + tax_total
        line_total_str = "%0.*f" % (prec, line_total)
        line_total_node = etree.SubElement(
            price_extension, ns["cbc"] + "Amount", currencyID=cur_name
        )
        line_total_node.text = str(line_total_str)
        # END OF CHANGES

    # TODO: use partner_id instead of the commercial_id in parties to set the address

    def _ubl_add_item(
        self,
        name,
        product,
        parent_node,
        ns,
        type_="purchase",
        seller=False,
        customer=False,
        version="2.1",
    ):
        # This method is OVERWRITING the original base_ubl method
        """Beware that product may be False (in particular on invoices)"""
        assert type_ in ("sale", "purchase"), "Wrong type param"
        assert name, "name is a required arg"
        item = etree.SubElement(parent_node, ns["cac"] + "Item")
        product_name = False
        seller_code = False
        if product:
            if type_ == "purchase":
                if seller:
                    sellers = product._select_seller(
                        partner_id=seller, quantity=0.0, date=None, uom_id=False
                    )
                    if sellers:
                        product_name = sellers[0].product_name
                        seller_code = sellers[0].product_code
            if not seller_code:
                seller_code = self._ubl_get_seller_code_from_product(product)
            if not product_name:
                variant = ", ".join(product.attribute_line_ids.mapped("value_ids.name"))
                product_name = (
                    variant and "{} ({})".format(product.name, variant) or product.name
                )
        description = etree.SubElement(item, ns["cbc"] + "Description")
        description.text = name
        name_node = etree.SubElement(item, ns["cbc"] + "Name")
        name_node.text = product_name or name.split("\n")[0]

        customer_code = self._ubl_get_customer_product_code(product, customer)
        if customer_code:
            buyer_identification = etree.SubElement(
                item, ns["cac"] + "BuyersItemIdentification"
            )
            buyer_identification_id = etree.SubElement(
                buyer_identification, ns["cbc"] + "ID"
            )
            buyer_identification_id.text = customer_code
        if seller_code:
            seller_identification = etree.SubElement(
                item, ns["cac"] + "SellersItemIdentification"
            )
            seller_identification_id = etree.SubElement(
                seller_identification, ns["cbc"] + "ID"
            )
            seller_identification_id.text = seller_code
        if product:
            if product.barcode:
                std_identification = etree.SubElement(
                    item, ns["cac"] + "StandardItemIdentification"
                )
                std_identification_id = etree.SubElement(
                    std_identification,
                    ns["cbc"] + "ID",
                    schemeAgencyID="6",
                    schemeID="GTIN",
                )
                std_identification_id.text = product.barcode
            # I'm not 100% sure, but it seems that ClassifiedTaxCategory
            # contains the taxes of the product without taking into
            # account the fiscal position
            if type_ == "sale":
                taxes = product.taxes_id
            else:
                taxes = product.supplier_taxes_id
            if taxes:
                for tax in taxes:
                    self._ubl_add_tax_category(
                        tax,
                        item,
                        ns,
                        node_name="ClassifiedTaxCategory",
                        version=version,
                    )
            # START OF CHANGES
            for attribute_value in product.product_template_attribute_value_ids:
                item_property = etree.SubElement(
                    item, ns["cac"] + "AdditionalItemProperty"
                )
                property_name = etree.SubElement(item_property, ns["cbc"] + "Name")
                property_name.text = attribute_value.attribute_id.name
                property_value = etree.SubElement(item_property, ns["cbc"] + "Value")
                property_value.text = attribute_value.name
            # END OF CHANGES

    def _ubl_add_supplier_party(
        self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        # This is OVERWRITING the original method
        supplier_party_node = super(AccountMove, self)._ubl_add_supplier_party(
            partner, company, node_name, parent_node, ns, version
        )
        additional_ref = self.partner_id.commercial_partner_id.sps_transaction_code
        if additional_ref:
            customer_id_node = supplier_party_node.find(
                ns["cbc"] + "CustomerAssignedAccountID"
            )
            additional_ref_node = etree.Element(ns["cbc"] + "AdditionalAccountID")
            additional_ref_node.text = additional_ref
            customer_id_node.addnext(additional_ref_node)

    def _ubl_add_party(
        self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        """This is overwriting the original base_ubl method"""
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        if partner.website:
            website = etree.SubElement(party, ns["cbc"] + "WebsiteURI")
            website.text = partner.website
        self._ubl_add_party_identification(partner, party, ns, version=version)
        party_name = etree.SubElement(party, ns["cac"] + "PartyName")
        name = etree.SubElement(party_name, ns["cbc"] + "Name")
        name.text = partner.name
        if partner.lang:
            self._ubl_add_language(partner.lang, party, ns, version=version)
        self._ubl_add_address(partner, "PostalAddress", party, ns, version=version)
        self._ubl_add_party_tax_scheme(partner, party, ns, version=version)
        if company:
            self._ubl_add_party_legal_entity(partner, party, ns, version="2.1")
        self._ubl_add_contact(partner, party, ns, version=version)

    def _ubl_add_delivery(self, delivery_partner, parent_node, ns, version="2.1"):
        "This is overwriting the original base_ubl method"
        delivery = etree.SubElement(parent_node, ns["cac"] + "Delivery")
        delivery_location = etree.SubElement(delivery, ns["cac"] + "DeliveryLocation")
        is_delivery = True
        # START OF THE CHANGES
        self._ubl_add_address(
            delivery_partner,
            "Address",
            delivery_location,
            ns,
            is_delivery,
            version=version,
        )
        # END OF THE CHANGES
        self._ubl_add_party(
            delivery_partner, False, "DeliveryParty", delivery, ns, version=version
        )

    def _ubl_add_address(
        self, partner, node_name, parent_node, ns, is_delivery=False, version="2.1"
    ):
        """This is overwriting the original base_ubl method"""
        address = etree.SubElement(parent_node, ns["cac"] + node_name)
        # START OF THE CHANGES
        if is_delivery:
            postbox_node = etree.SubElement(address, ns["cbc"] + "Postbox")
            postbox_node.text = "01"
        # END OF THE CHANGES
        if partner.street:
            streetname = etree.SubElement(address, ns["cbc"] + "StreetName")
            streetname.text = partner.street
        if partner.street2:
            addstreetname = etree.SubElement(
                address, ns["cbc"] + "AdditionalStreetName"
            )
            addstreetname.text = partner.street2
        if hasattr(partner, "street3") and partner.street3:
            blockname = etree.SubElement(address, ns["cbc"] + "BlockName")
            blockname.text = partner.street3
        if partner.city:
            city = etree.SubElement(address, ns["cbc"] + "CityName")
            city.text = partner.city
        if partner.zip:
            zip_code = etree.SubElement(address, ns["cbc"] + "PostalZone")
            zip_code.text = partner.zip
        if partner.state_id:
            state = etree.SubElement(address, ns["cbc"] + "CountrySubentity")
            state.text = partner.state_id.name
            state_code = etree.SubElement(address, ns["cbc"] + "CountrySubentityCode")
            state_code.text = partner.state_id.code
        if partner.country_id:
            self._ubl_add_country(partner.country_id, address, ns, version=version)
        else:
            logger.warning("UBL: missing country on partner %s", partner.name)

    def generate_invoice_ubl_xml_etree(self, version="2.1"):
        """This is overwriting the original account_invoice_ubl method"""
        self.ensure_one()
        nsmap, ns = self._ubl_get_nsmap_namespace("Invoice-2", version=version)
        xml_root = etree.Element("Invoice", nsmap=nsmap)
        self._ubl_add_header(xml_root, ns, version=version)
        self._ubl_add_order_reference(xml_root, ns, version=version)
        self._ubl_add_contract_document_reference(xml_root, ns, version=version)
        self._ubl_add_attachments(xml_root, ns, version=version)
        self._ubl_add_supplier_party(
            False,
            self.company_id,
            "AccountingSupplierParty",
            xml_root,
            ns,
            version=version,
        )
        self._ubl_add_customer_party(
            self.partner_id,
            False,
            "AccountingCustomerParty",
            xml_root,
            ns,
            version=version,
        )
        # START OF THE CHANGES
        self._ubl_add_party(
            self.partner_id, False, "PayeeParty", xml_root, ns, version=version,
        )
        # END OF THE CHANGES
        # the field 'partner_shipping_id' is defined in the 'sale' module
        if hasattr(self, "partner_shipping_id") and self.partner_shipping_id:
            self._ubl_add_delivery(self.partner_shipping_id, xml_root, ns)
        # Put paymentmeans block even when invoice is paid ?
        payment_identifier = self.get_payment_identifier()
        self._ubl_add_payment_means(
            self.invoice_partner_bank_id,
            self.payment_mode_id,
            self.invoice_date_due,
            xml_root,
            ns,
            payment_identifier=payment_identifier,
            version=version,
        )
        if self.invoice_payment_term_id:
            self._ubl_add_payment_terms(
                self.invoice_payment_term_id, xml_root, ns, version=version
            )
        self._ubl_add_tax_total(xml_root, ns, version=version)
        self._ubl_add_legal_monetary_total(xml_root, ns, version=version)

        line_number = 0
        for iline in self.invoice_line_ids:
            line_number += 1
            self._ubl_add_invoice_line(
                xml_root, iline, line_number, ns, version=version
            )
        return xml_root
