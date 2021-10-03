# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

{
    "name": "Gubi EDI UBL",
    "summary": "Gubi Specific EDI components for UBL standard",
    "category": "Accounting",
    "version": "13.0.1.0.0",
    "license": "OPL-1",
    "author": "ForgeFlow",
    "depends": [
        "edi_account",
        "sale",
        "account_invoice_ubl",
        "purchase_order_ubl",
        "sale_order_import_ubl",
        "gubi_sale",
        "niova_product_auto_item_number",
        "product_supplierinfo_for_customer_sale",
        "niova_stock_dropshipping",
        "niova_product_volume_weights",
        "product",
        "edi_backend_partner",
    ],
    "data": [
        "data/edi_backend_type_data.xml",
        "data/edi_backend_data.xml",
        "data/edi_exchange_type_data.xml",
        "views/sale_views.xml",
        "views/purchase_order_views.xml",
        "views/res_partner_views.xml",
        "views/edi_product_catalogue_views.xml",
        "security/ir.model.access.csv",
    ],
    "demo": [],
}
