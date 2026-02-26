
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account.models.account_move import BYPASS_LOCK_CHECK

_logger = logging.getLogger(__name__)


UNINSTALL_CONTEXT_FLAGS = {
    '_force_unlink': True,
    'force_unlink': True,
    'tracking_disable': True,
    'mail_notrack': True,
    'module_uninstall': True,
    'prefetch_fields': False,
    'dynamic_unlink': True,
    'bypass_lock_check': BYPASS_LOCK_CHECK
}


class ClearDataTransactionWizard(models.TransientModel):
    _name = "clear.data.transaction.wizard"
    _description = "Clear Data Transaction Wizard"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        domain="[('transient', '=', False)]",
        help="Choose the model whose records should be deleted.",
    )
    model_name = fields.Char(
        related='model_id.model', 
        string='Model Name', 
        readonly=True, 
        store=True
    )
    domain = fields.Char(
        string="Filter", 
        help="Optional domain filter in Python list syntax. Example: [('state', '=', 'cancelled')].",
    )
    use_sudo = fields.Boolean(
        string="Superuser Mode",
        default=True,
        help="Delete records with superuser rights to avoid access right issues.",
    )
    reset_sequences = fields.Boolean(
        string="Reset Sequences",
        help="Reset the selected sequences after data removal.",
    )
    sequence_ids = fields.Many2many(
        'ir.sequence',
        string="Guess Sequences",
        domain=['|', ('active', '=', True), ('active', '=', False)],
        help="Sequences whose numbering should restart after the cleanup.",
    )

    @api.onchange('model_id', 'reset_sequences')
    def _onchange_model_id(self):
        sequences = [fields.Command.clear()]
        if self.reset_sequences and self.model_id:
            guessed = self._guess_sequences(self.model_id)
            if guessed:
                sequences = [fields.Command.set(guessed.ids)]
                
        self.sequence_ids = sequences             

    def _guess_sequences(self, model):
        if not model:
            return False
        
        name_parts = [model.model, model.name, model.model.replace('.', '_')]
        domain = []
        for part in name_parts:
            clause = ['|', ('code', 'ilike', part), ('name', 'ilike', part)]
            domain = clause if not domain else expression.OR([domain, clause])
            
        return self.env['ir.sequence'].with_context(active_test=False).search(domain, limit=20)

    def _parse_domain(self):
        self.ensure_one()
        if not self.domain:
            return []
        try:
            parsed_domain = safe_eval(self.domain, locals_dict={})
        except Exception as exc:  # pylint: disable=broad-except
            raise UserError(_("Invalid domain expression: %s", exc)) from exc
        
        if not isinstance(parsed_domain, (list, tuple)):
            raise UserError(_("The domain must evaluate to a list or tuple."))
        return list(parsed_domain)

    def _notify(self, title, message, sticky=False, level="info"):
        self.domain = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "sticky": sticky,
                "type": level,
            },
        }

    @api.model
    def _batched(self, records, batch_size=1000):
        length = len(records)
        for start in range(0, length, batch_size):
            yield records[start : start + batch_size]

    def _cleanup_external_ids(self, model_name, record_ids):
        if not record_ids:
            return 0
        imd = self.env['ir.model.data'].with_context(UNINSTALL_CONTEXT_FLAGS).sudo()
        records = imd.search([
            ('model', '=', model_name),
            ('res_id', 'in', list(record_ids)),
        ])
        count = len(records)
        if count:
            _logger.debug("Removing %s ir.model.data reference(s) for %s", count, model_name)
            records.unlink()
        return count

    def _reset_sequences(self, sequences):
        reset_count = 0
        for sequence in sequences:
            try:
                sequence.write({'number_next': 1, 'number_next_actual': 1})
                if sequence.use_date_range:
                    sequence.date_range_ids.write({'number_next': 1})
                reset_count += 1
            except Exception as err:  # pylint: disable=broad-except
                _logger.exception("Failed to reset sequence %s: %s", sequence, err)
        return reset_count

    def _maybe_cancel(self, recs):
        if not recs:
            return
        for attr in ('action_cancel', 'button_cancel', '_action_cancel'):
            try:
                method = getattr(recs, attr)
            except AttributeError:
                continue
            try:
                method()
                break
            except Exception:
                continue
                
    def _maybe_draft(self, recs):
        if not recs:
            return
        for attr in ('action_draft', 'button_draft', '_action_draft'):
            try:
                method = getattr(recs, attr)
            except AttributeError:
                continue
            try:
                method()
                break
            except Exception:
                continue

    def action_clear(self):
        self.ensure_one()
        model_name = self.model_id.model
        if not model_name:
            raise UserError(_("The selected model is invalid."))

        domain = self._parse_domain()
        env = self.env[model_name]
        if self.use_sudo:
            env = env.sudo()
        env = env.with_context(active_test=False, **UNINSTALL_CONTEXT_FLAGS)
        records = env.search(domain)
        total = len(records)
        if not total:
            return self._notify(_("Clear Data"), _("No records matched the provided domain."))

        _logger.info(
            "Clear Data Transaction: deleting %s records from model %s with uninstall semantics",
            total,
            model_name,
        )

        external_removed = self._cleanup_external_ids(model_name, records.ids)

        deleted = 0
        failed = 0
        failures = []
        for batch in self._batched(records, batch_size=500):
            batch_count = len(batch)
            success = False

            # Attempt 1: direct unlink
            try:
                with self.env.cr.savepoint():
                    batch.unlink()
                success = True
            except Exception as err_unlink:  # pylint: disable=broad-except
                _logger.warning(
                    "Clear data unlink failed for %s (direct unlink): %s",
                    batch,
                    err_unlink,
                )

            # Attempt 2: cancel then unlink
            if not success:
                try:
                    with self.env.cr.savepoint():
                        self._maybe_cancel(batch)
                        batch.unlink()
                    success = True
                except Exception as err_cancel:  # pylint: disable=broad-except
                    _logger.warning(
                        "Clear data unlink failed for %s (cancel+unlink): %s",
                        batch,
                        err_cancel,
                    )

            # Attempt 3: draft then unlink
            if not success:
                try:
                    with self.env.cr.savepoint():
                        self._maybe_draft(batch)
                        batch.unlink()
                    success = True
                except Exception as err_draft:  # pylint: disable=broad-except
                    _logger.exception(
                        "Clear data unlink failed for %s (draft+unlink). skipping batch.",
                        batch,
                    )
                    failures.append(str(err_draft))
                    failed += batch_count

            if success:
                deleted += batch_count

        level = "success"
        messages = []
        if deleted:
            messages.append(_("Deleted %(count)s record(s) from %(model)s.", count=deleted, model=self.model_id.display_name))
        if external_removed:
            messages.append(_("Removed %(count)s external id(s).", count=external_removed))
        if failed:
            level = "warning"
            messages.append(_("Failed to delete %(count)s record(s).", count=failed))
            if failures:
                messages.append("; ".join(failures[:3]))

        sequence_reset_msg = None
        sequences = self.sequence_ids
        if self.reset_sequences and sequences:
            total_sequences = len(sequences)
            reset_count = self._reset_sequences(sequences)
            if reset_count:
                sequence_reset_msg = _("Reset %(count)s sequence(s).", count=reset_count)
                if reset_count < total_sequences:
                    level = "warning"
                    sequence_reset_msg += " " + _(
                        "Some sequences could not be reset. Check the logs for details."
                    )
            elif total_sequences:
                level = "warning"
                sequence_reset_msg = _("Failed to reset the selected sequences. Check the logs for details.")
            else:
                sequence_reset_msg = _("No sequences were selected to reset.")
        if sequence_reset_msg:
            messages.append(sequence_reset_msg)

        if not messages:
            messages.append(_("No changes were performed."))

        return self._notify(_("Clear Data"), "\n".join(messages), sticky=True, level=level)
