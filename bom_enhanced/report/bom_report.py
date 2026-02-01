# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)

class ReportBomStructure(models.AbstractModel):
    _name = 'report.bom_enhanced.report_bom_with_price_document'
    _description = 'BOM Report With Price'

    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        
        all_data = []
        for bom in boms:
            try:
                # Try to use standard Odoo report method
                report_model = self.env['report.mrp.report_bom_structure']
                bom_data = report_model._get_report_data(
                    bom_id=bom.id,
                    searchQty=bom.product_qty,
                    searchVariant=bom.product_id.id if bom.product_id else False
                )
                # Add bom object for logo/address
                bom_data['bom_obj'] = bom
                all_data.append(bom_data)
                
            except Exception as e:
                _logger.warning(f"Standard report method failed: {e}. Building data manually.")
                
                # Build data structure manually (fallback)
                bom_data = {
                    'bom_obj': bom,
                    'name': bom.product_tmpl_id.display_name,
                    'bom_code': bom.code or '',
                    'quantity': bom.product_qty,
                    'uom_name': bom.product_uom_id.name,
                    'currency': bom.company_id.currency_id,
                    'show_costs': True,
                    'show_availabilities': False,
                    'show_lead_times': False,
                    'lines': [],
                    'bom_cost': 0.0,
                    'prod_cost': 0.0,
                }
                
                # Add BOM lines
                for line in bom.bom_line_ids:
                    line_data = {
                        'name': line.product_id.display_name,
                        'quantity': line.product_qty,
                        'uom_name': line.product_uom_id.name,
                        'prod_cost': line.product_id.standard_price * line.product_qty,
                        'bom_cost': line.product_id.standard_price * line.product_qty,
                    }
                    bom_data['lines'].append(line_data)
                    bom_data['bom_cost'] += line_data['bom_cost']
                    bom_data['prod_cost'] += line_data['prod_cost']
                
                all_data.append(bom_data)
        
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.bom',
            'docs': all_data,
        }


class ReportBomStructureNoPrice(models.AbstractModel):
    _name = 'report.bom_enhanced.report_bom_no_price_document'
    _description = 'BOM Report No Price'

    def _get_report_values(self, docids, data=None):
        # Reuse the same data from with_price report
        return self.env['report.bom_enhanced.report_bom_with_price_document']._get_report_values(docids, data)
