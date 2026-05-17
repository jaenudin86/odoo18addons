# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    After module installation, enforce decimal precision on all existing currencies.
    Delegates to res.currency._enforce_all_rounding() to avoid logic duplication.
    """
    _logger.info('[currency_decimal_fix] Running post_init_hook...')
    env['res.currency'].sudo()._enforce_all_rounding()
    _logger.info('[currency_decimal_fix] post_init_hook complete.')
