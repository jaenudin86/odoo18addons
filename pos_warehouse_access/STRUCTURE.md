# Module Structure

```
pos_warehouse_access/
├── __init__.py                          # Module initializer
├── __manifest__.py                       # Module manifest/descriptor
├── LICENSE                              # LGPL-3 License
├── README.md                            # Main documentation
├── INSTALL.md                           # Installation guide
├── CHANGELOG.md                         # Version history
│
├── models/                              # Python models
│   ├── __init__.py                      # Models initializer
│   ├── res_users.py                     # Extend res.users with POS & warehouse access
│   ├── pos_config.py                    # Extend pos.config with user access
│   ├── stock_warehouse.py               # Extend stock.warehouse with user access
│   └── stock_quant.py                   # Override stock.quant for filtering
│
├── views/                               # XML views
│   ├── res_users_views.xml              # User form/tree views with access tabs
│   ├── pos_config_views.xml             # POS form/tree views with user access
│   └── stock_warehouse_views.xml        # Warehouse form/tree views with user access
│
├── security/                            # Security & access rights
│   ├── ir.model.access.csv              # Model access rights
│   └── security.xml                     # Record rules for filtering
│
├── demo/                                # Demo/test data
│   └── demo_data.xml                    # Sample users, POS, warehouses with access
│
└── static/                              # Static files
    └── description/
        └── index.html                   # Module description page
```

## File Descriptions

### Root Files

**__init__.py**
- Module entry point
- Imports models package

**__manifest__.py**
- Module metadata (name, version, author)
- Dependencies declaration
- Data files loading order
- License and category info

**README.md**
- Main documentation
- Features overview
- Usage examples
- Troubleshooting guide

**INSTALL.md**
- Step-by-step installation guide
- Docker installation
- Troubleshooting installation issues

**CHANGELOG.md**
- Version history
- New features per version
- Bug fixes tracking

**LICENSE**
- LGPL-3 license text

### Models Package

**models/__init__.py**
- Import all model files

**models/res_users.py**
- Extend `res.users` model
- Add fields: `pos_access_ids`, `warehouse_access_ids`
- Computed fields: `pos_access_count`, `warehouse_access_count`
- Methods: `action_view_pos_access()`, `action_view_warehouse_access()`

**models/pos_config.py**
- Extend `pos.config` model
- Add field: `user_access_ids`
- Computed field: `user_access_count`
- Override `search_read()` for auto-filtering
- Method: `action_view_user_access()`

**models/stock_warehouse.py**
- Extend `stock.warehouse` model
- Add field: `user_access_ids`
- Computed field: `user_access_count`
- Method: `action_view_user_access()`

**models/stock_quant.py**
- Extend `stock.quant` model
- Override `search_read()` for stock filtering
- Filter based on warehouse access

### Views Package

**views/res_users_views.xml**
- Add tabs "POS Access" and "Warehouse Access" to user form
- Add smart buttons for access counts
- Add columns in user tree view
- Info alerts with usage instructions

**views/pos_config_views.xml**
- Add tab "User Access" to POS form
- Add smart button for user count
- Add column in POS tree view
- Info alerts with usage instructions

**views/stock_warehouse_views.xml**
- Add tab "User Access" to warehouse form
- Add smart button for user count
- Add column in warehouse tree view
- Info alerts with usage instructions

### Security Package

**security/ir.model.access.csv**
- Define model access rights
- Different rights for users vs managers
- Format: id, name, model_id, group_id, perm_read, perm_write, perm_create, perm_unlink

**security/security.xml**
- Record rules for `pos.config` (user access filtering)
- Record rules for `stock.warehouse` (user access filtering)
- Record rules for `stock.quant` (stock filtering based on warehouse)
- Separate rules for regular users vs managers
- Domain force for automatic filtering

### Demo Package

**demo/demo_data.xml**
- Demo users: Kasir, Supervisor, Warehouse Staff
- Demo warehouses: Jakarta, Bandung, Surabaya
- Demo POS: Toko A, B, C
- Pre-configured access mappings for testing

### Static Package

**static/description/index.html**
- HTML page shown in Apps menu
- Feature highlights
- Usage guide
- Screenshots area (can add images)

## Data Loading Order

1. `security/ir.model.access.csv` - Access rights first
2. `security/security.xml` - Record rules
3. `views/res_users_views.xml` - User interface
4. `views/pos_config_views.xml` - POS interface
5. `views/stock_warehouse_views.xml` - Warehouse interface
6. `demo/demo_data.xml` - Demo data (optional, only if demo=True in manifest)

## Database Tables

### New Junction Tables

**pos_user_access_rel**
- user_id (FK to res_users)
- pos_id (FK to pos_config)

**warehouse_user_access_rel**
- user_id (FK to res_users)
- warehouse_id (FK to stock_warehouse)

### Extended Tables

**res_users**
- pos_access_ids (many2many)
- warehouse_access_ids (many2many)
- pos_access_count (computed)
- warehouse_access_count (computed)

**pos_config**
- user_access_ids (many2many)
- user_access_count (computed)

**stock_warehouse**
- user_access_ids (many2many)
- user_access_count (computed)

## Security Implementation

### Record Rules

1. **pos_config_user_access_rule**
   - Apply to: base.group_user
   - Domain: User can only see POS where they are in user_access_ids OR user_access_ids is empty
   - Permission: Read only

2. **pos_config_manager_access_rule**
   - Apply to: point_of_sale.group_pos_manager
   - Domain: All POS (1=1)
   - Permission: Full CRUD

3. **stock_warehouse_user_access_rule**
   - Apply to: base.group_user
   - Domain: User can only see warehouses where they are in user_access_ids OR user_access_ids is empty
   - Permission: Read only

4. **stock_warehouse_manager_access_rule**
   - Apply to: stock.group_stock_manager
   - Domain: All warehouses (1=1)
   - Permission: Full CRUD

5. **stock_quant_user_warehouse_rule**
   - Apply to: base.group_user
   - Domain: Stock quant filtered by warehouse access
   - Permission: Read only

6. **stock_quant_manager_access_rule**
   - Apply to: stock.group_stock_manager
   - Domain: All stock (1=1)
   - Permission: Full CRUD

## Workflow

### User Access Setup

1. Admin creates user
2. Admin goes to user form
3. Admin opens "POS Access" tab
4. Admin selects which POS user can access
5. Admin opens "Warehouse Access" tab
6. Admin selects which warehouses user can see
7. User logs in and sees only assigned POS and stock

### POS Access Management

1. Admin goes to POS configuration
2. Admin opens "User Access" tab
3. Admin sees which users can access this POS
4. Admin can add/remove users
5. Changes take effect immediately

### Warehouse Access Management

1. Admin goes to Warehouse configuration
2. Admin opens "User Access" tab
3. Admin sees which users can see this warehouse
4. Admin can add/remove users
5. Stock visibility changes immediately

## Extension Points

This module can be extended by:

1. **Adding time-based access**: Add date_from and date_to fields
2. **Adding access levels**: Add access_type field (read_only, full_access)
3. **Adding approval workflow**: Require manager approval for access
4. **Adding logging**: Log all access changes
5. **Adding reports**: Generate access audit reports
6. **Integrating with HR**: Auto-assign based on job position
7. **Adding API**: REST API for external access management

## Performance Considerations

- Junction tables are indexed for fast lookup
- Record rules use efficient domain filters
- Computed fields are cached
- search_read override minimal overhead
- No expensive joins in filtering logic

## Testing Checklist

- [ ] Install module without errors
- [ ] Assign POS to user
- [ ] User can only see assigned POS
- [ ] Assign warehouse to user
- [ ] User can only see stock from assigned warehouse
- [ ] Manager can see all POS/warehouses
- [ ] Admin has full access
- [ ] Smart buttons work correctly
- [ ] Access counts are accurate
- [ ] Demo data loads correctly
- [ ] Uninstall works without errors
