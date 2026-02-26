# -*- coding: utf-8 -*-
from odoo import models
import logging
_logger = logging.getLogger(__name__)


class ReportBomWithPrice(models.AbstractModel):
    _name = 'report.bom_enhanced.report_bom_with_price_document'
    _description = 'BOM Report With Price'

    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        report_model = self.env['report.mrp.report_bom_structure']
        docs = []

        for bom in boms:
            try:
                # Call native Odoo BOM report data builder
                bom_data = report_model._get_report_data(
                    bom_id=bom.id,
                    searchQty=bom.product_qty,
                    searchVariant=bom.product_id.id if bom.product_id else False,
                )
                docs.append({
                    'bom_obj': bom,
                    'data': bom_data['lines'][0],  # top-level BOM dict
                })
            except Exception as e:
                _logger.warning("Native BOM report data failed for bom %s: %s", bom.id, e)
                # Minimal fallback so the report still renders
                docs.append({
                    'bom_obj': bom,
                    'data': {
                        'name': bom.product_tmpl_id.display_name,
                        'bom_code': bom.code or '',
                        'quantity': bom.product_qty,
                        'uom_name': bom.product_uom_id.name,
                        'currency': bom.company_id.currency_id,
                        'show_costs': True,
                        'show_availabilities': False,
                        'show_lead_times': False,
                        'lines': [],
                        'byproducts': [],
                        'bom_cost': sum(
                            l.product_id.standard_price * l.product_qty
                            for l in bom.bom_line_ids
                        ),
                        'prod_cost': bom.product_tmpl_id.standard_price * bom.product_qty,
                        'route_name': '',
                        'route_detail': '',
                        'route_alert': False,
                        'lead_time': False,
                        'producible_qty': 0,
                        'quantity_available': 0,
                        'quantity_on_hand': 0,
                        'components_available': None,
                        'availability_state': '',
                        'availability_display': '',
                    },
                })

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.bom',
            'docs': docs,
        }