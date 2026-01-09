@api.depends('picking_id', 'move_type')
    def _compute_available_sn_ids(self):
        """Get available serial numbers - filter by status and tracking"""
        for wizard in self:
            if not wizard.picking_id:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # Get products that have SN tracking
            products = wizard.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.tracking == 'serial' and m.product_id.product_tmpl_id.sn_product_type
            ).mapped('product_id')
            
            if not products:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # Build domain
            domain = [
                ('product_id', 'in', products.ids),
                ('sn_type', '!=', False)  # Only custom SNs
            ]
            
            # Filter by move type and status
            if wizard.move_type == 'in':
                # For incoming: show all status (bisa re-use SN yang used untuk return)
                # Tapi exclude yang sudah used di location lain
                domain.append(('sn_status', 'in', ['available', 'reserved']))
            elif wizard.move_type == 'out':
                # For outgoing: ONLY available
                domain.append(('sn_status', '=', 'available'))
            elif wizard.move_type == 'internal':
                # For internal: available or reserved
                domain.append(('sn_status', 'in', ['available', 'reserved']))
            
            # Exclude already scanned in this picking
            already_scanned = wizard.picking_id.sn_move_ids.mapped('serial_number_id.id')
            if already_scanned:
                domain.append(('id', 'not in', already_scanned))
            
            available_sns = self.env['stock.lot'].search(domain, order='name')
            wizard.available_sn_ids = [(6, 0, available_sns.ids)]