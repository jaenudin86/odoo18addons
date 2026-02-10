# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2025-02-11

### Fixed
- Fixed duplicate field declaration in user, POS, and warehouse views
- Removed invalid `color_field` widget option
- Fixed many2many field display issues in Odoo 18
- Added proper widget attributes for editable lists

### Added
- Added Settings page extension (res.config.settings view)
- Added link to User Access configuration from Settings
- Added editable mode to list views for easier inline editing
- Added optional field visibility controls
- Added BUGFIX.md documentation

### Changed
- Restructured view layouts to avoid duplicate field declarations
- Improved user experience with better field organization
- Enhanced list view with editable="bottom" attribute

## [1.0.0] - 2025-02-11

### Added
- Initial release untuk Odoo 18.0
- Fitur assign POS ke user (many-to-many)
- Fitur assign Gudang ke user (many-to-many)
- Tab "POS Access" di user form
- Tab "Warehouse Access" di user form
- Tab "User Access" di POS config form
- Tab "User Access" di warehouse form
- Smart buttons untuk count akses
- Auto-filtering POS berdasarkan user access
- Auto-filtering stock berdasarkan warehouse access
- Record rules untuk security
- Support untuk POS Manager role (bypass filter)
- Support untuk Stock Manager role (bypass filter)
- Support untuk Administrator role (full access)
- Documentation lengkap (README, INSTALL, CHANGELOG)
- Module description HTML untuk Apps page

### Security
- Record rule untuk pos.config user access
- Record rule untuk stock.warehouse user access
- Record rule untuk stock.quant warehouse filtering
- Access rights untuk regular users vs managers

### Technical
- Model extend: res.users
- Model extend: pos.config
- Model extend: stock.warehouse
- Model extend: stock.quant
- Junction table: pos_user_access_rel
- Junction table: warehouse_user_access_rel
- Override search_read di pos.config untuk filtering
- Override search_read di stock.quant untuk filtering

### Views
- User form view dengan tabs akses
- User tree view dengan access count
- POS config form view dengan tab user access
- POS config tree view dengan user count
- Warehouse form view dengan tab user access
- Warehouse tree view dengan user count

## [Planned for Future Versions]

### [1.1.0] - Planned
- [ ] Report akses user (siapa akses apa)
- [ ] Bulk assign user ke multiple POS/Warehouse
- [ ] Import/Export user access mapping
- [ ] Email notification saat akses berubah
- [ ] Access log/audit trail

### [1.2.0] - Planned
- [ ] Time-based access (temporary access)
- [ ] Territory-based access
- [ ] Custom access levels (read-only vs full access)
- [ ] Access request workflow (user request, manager approve)

### [2.0.0] - Planned
- [ ] Support untuk Sales Team access
- [ ] Integration dengan HR module (access based on job position)
- [ ] Mobile app support
- [ ] API endpoint untuk external access management

## Version Numbering

Format: MAJOR.MINOR.PATCH

- MAJOR: Incompatible API changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

## Support

Version 1.0.0 compatible with:
- Odoo Community Edition 18.0
- Odoo Enterprise Edition 18.0

Minimum Odoo version: 18.0
Tested up to: 18.0

---

**Note:** This is the first stable release. Please report any bugs or issues to support@yourcompany.com
