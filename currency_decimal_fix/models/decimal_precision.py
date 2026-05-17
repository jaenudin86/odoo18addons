# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Precision names in Odoo that correspond to monetary/currency display
CURRENCY_PRECISION_NAMES = frozenset([
    'Account',
    'Payment Terms',
    'Currency',
    'Product Price',
])

MANDATORY_DIGITS = 3  # Our standard for all currency-related decimal precisions


class DecimalPrecisionFixed(models.Model):
    """
    Override decimal.precision to prevent UI changes to currency-related
    precision records. Any attempt to reduce digits below MANDATORY_DIGITS
    for the listed precision names is blocked/corrected.
    """

    _inherit = 'decimal.precision'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._enforce_currency_precision(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'digits' in vals or 'name' in vals:
            for record in self:
                record_vals = dict(vals)
                effective_name = record_vals.get('name', record.name)
                if effective_name in CURRENCY_PRECISION_NAMES:
                    if 'digits' in record_vals and record_vals['digits'] < MANDATORY_DIGITS:
                        _logger.warning(
                            '[currency_decimal_fix] Blocked decimal.precision change on "%s": '
                            'tried %d digits, enforcing minimum %d',
                            effective_name, record_vals['digits'], MANDATORY_DIGITS
                        )
                        record_vals['digits'] = MANDATORY_DIGITS
                    super(DecimalPrecisionFixed, record).write(record_vals)
            return True
        return super().write(vals)

    @api.model
    def _enforce_currency_precision(self, vals):
        """Ensure currency-related decimal precisions meet minimum digits."""
        name = vals.get('name', '')
        if name in CURRENCY_PRECISION_NAMES:
            if vals.get('digits', 0) < MANDATORY_DIGITS:
                vals['digits'] = MANDATORY_DIGITS
        return vals

    @api.model
    def _enforce_currency_precision_all(self):
        """
        Safe SQL UPDATE for all known currency-related decimal.precision rows.
        Called from data/decimal_precision_data.xml via <function> tag.

        Uses UPDATE (not INSERT) so it only affects rows that already exist —
        rows from modules not yet installed are silently skipped.
        When those modules are installed later, the ORM overrides (create/write)
        and the daily cron will enforce the correct digits.
        """
        targets = {
            'Account': 3,
            'Currency': 3,
            'Payment Terms': 3,
            'Product Price': 3,
            'Product Unit of Measure': 3,
            'Discount': 3,
        }
        for name, digits in targets.items():
            self.env.cr.execute(
                "UPDATE decimal_precision SET digits = %s WHERE name = %s AND digits < %s",
                (digits, name, digits),
            )
            if self.env.cr.rowcount:
                _logger.info(
                    '[currency_decimal_fix] decimal.precision "%s" -> %d digits', name, digits
                )
        self.env['decimal.precision'].invalidate_model(['digits'])

    @api.model
    def precision_get(self, application):
        """
        Override precision_get to enforce our minimum for currency-related
        applications at the point of use (affects formatLang, float_repr, etc.).
        """
        digits = super().precision_get(application)
        if application in CURRENCY_PRECISION_NAMES:
            return max(digits, MANDATORY_DIGITS)
        return digits
