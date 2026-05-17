# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ─── Policy Constants ────────────────────────────────────────────────────────
IDR_ROUNDING = 0.01      # 2 decimal places  → e.g. 1500.25
DEFAULT_ROUNDING = 0.001  # 3 decimal places → e.g. 1.234
# ─────────────────────────────────────────────────────────────────────────────


class ResCurrencyFixed(models.Model):
    """
    Inherit res.currency to enforce mandatory decimal precision rules:
      - IDR  : 2 decimal digits (rounding = 0.01)
      - Other: 3 decimal digits (rounding = 0.001)

    The `rounding` field is set to readonly in the UI via the view override,
    and any programmatic write attempt that violates the policy is corrected
    silently (or raised if in strict mode).
    """

    _inherit = 'res.currency'

    # ── Override rounding field: hidden from UI modifications ────────────────
    rounding = fields.Float(
        string='Rounding Factor',
        digits=(12, 6),
        default=DEFAULT_ROUNDING,
        help='Mandatory rounding set by currency_decimal_fix module. '
             'IDR = 0.01 (2 decimals), all others = 0.001 (3 decimals).',
    )

    # ─── Internal helper ─────────────────────────────────────────────────────

    @api.model
    def _get_mandatory_rounding(self, currency_name):
        """Return the mandatory rounding value for a given currency name."""
        if currency_name and currency_name.upper() == 'IDR':
            return IDR_ROUNDING
        return DEFAULT_ROUNDING

    def _enforce_rounding(self, vals):
        """
        Inject the correct mandatory rounding into a vals dict.
        Called from create() and write() to guarantee policy compliance.
        """
        # Determine currency name from vals or from existing record
        name = vals.get('name') or (self[:1].name if self else None)
        if name:
            vals['rounding'] = self._get_mandatory_rounding(name)
        return vals

    # ─── ORM Overrides ───────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """Enforce rounding policy on every new currency record."""
        for vals in vals_list:
            self._enforce_rounding(vals)
            _logger.debug(
                '[currency_decimal_fix] create: %s -> rounding=%s',
                vals.get('name', '?'), vals.get('rounding')
            )
        return super().create(vals_list)

    def write(self, vals):
        """
        Enforce rounding policy on every write.

        Strategy:
        - If the caller is trying to change `rounding` to a non-compliant value,
          silently correct it.
        - If `name` changes, re-evaluate the required rounding.
        """
        # Evaluate per-record because names may differ across recordset
        if len(self) == 1:
            self._enforce_rounding_on_write(vals)
        else:
            # For multi-record writes we call individually to handle name changes
            for record in self:
                record_vals = dict(vals)
                record._enforce_rounding_on_write(record_vals)
            # After individual corrections, unify vals for records that share the same name
            # (or just let the loop above handle them separately)
            return self._write_individually(vals)

        return super().write(vals)

    def _enforce_rounding_on_write(self, vals):
        """Mutate vals in-place to enforce the rounding policy for a single record."""
        # Determine the effective name after the write
        name = vals.get('name', self.name)
        required_rounding = self._get_mandatory_rounding(name)

        if 'rounding' in vals:
            if abs(vals['rounding'] - required_rounding) > 1e-10:
                _logger.warning(
                    '[currency_decimal_fix] Blocked rounding change on %s: '
                    'tried %s, enforcing %s',
                    name, vals['rounding'], required_rounding
                )
        # Always set the mandatory rounding
        vals['rounding'] = required_rounding

    def _write_individually(self, vals):
        """
        Write records individually when the recordset contains currencies
        with potentially different rounding rules (mixed name changes).
        """
        result = True
        for record in self:
            record_vals = dict(vals)
            record._enforce_rounding_on_write(record_vals)
            result = super(ResCurrencyFixed, record).write(record_vals) and result
        return result

    # ─── Compute / onchange helpers ──────────────────────────────────────────

    @api.onchange('name')
    def _onchange_name_fix_rounding(self):
        """Update rounding immediately when the currency name changes in the form."""
        if self.name:
            self.rounding = self._get_mandatory_rounding(self.name)

    @api.model
    def _enforce_all_rounding(self):
        """
        Re-enforce mandatory rounding on ALL currency records.
        Called by the daily cron job (no import statements allowed in cron code).
        Also called by post_init_hook via hooks.py.
        """
        _logger.info('[currency_decimal_fix] _enforce_all_rounding: start')
        all_currencies = self.with_context(active_test=False).search([])
        updated = 0
        for currency in all_currencies:
            required = self._get_mandatory_rounding(currency.name)
            if abs(currency.rounding - required) > 1e-10:
                self.env.cr.execute(
                    "UPDATE res_currency SET rounding = %s WHERE id = %s",
                    (required, currency.id),
                )
                updated += 1
                _logger.info(
                    '[currency_decimal_fix] %s rounding corrected -> %s',
                    currency.name, required,
                )
        self.env['res.currency'].invalidate_model(['rounding'])
        # Also re-enforce decimal.precision rows
        self.env['decimal.precision']._enforce_currency_precision_all()
        _logger.info('[currency_decimal_fix] _enforce_all_rounding: %d currencies updated', updated)

    # ─── Override round() to always use enforced rounding ────────────────────

    def round(self, amount):
        """
        Override the base round() to guarantee we use the enforced rounding,
        even if the in-memory object somehow has a different value.
        """
        enforced = self._get_mandatory_rounding(self.name)
        # Temporarily use enforced rounding without writing to DB
        from odoo.tools import float_round
        return float_round(amount, precision_rounding=enforced)
