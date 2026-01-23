# Changelog

All notable changes to the Advanced Accounting module will be documented in this file.

## [18.0.1.0.0] - 2026-01-22

### Added
- **Budget Management**
  - Multi-level budget creation and management
  - Budget vs Actual tracking with real-time updates
  - Budget approval workflow (Draft → Confirmed → Approved → Done)
  - Budget line management with analytic account integration
  - Theoretical amount calculation for budget monitoring
  - Budget alerts and warnings

- **Asset Management**
  - Fixed asset tracking and lifecycle management
  - Automated depreciation calculation
  - Support for Linear and Degressive depreciation methods
  - Depreciation board with automatic journal entry generation
  - Prorata temporis calculation for partial year depreciation
  - Asset disposal and closing functionality
  - Integration with purchase invoices

- **Cost Center Management**
  - Hierarchical cost center structure
  - Cost tracking by department/division
  - Revenue and expense monitoring per cost center
  - Budget allocation and tracking per cost center
  - Manager assignment and responsibility tracking
  - Integration with analytic accounting

- **Payment Follow-up**
  - Multi-level automated payment reminder system
  - Configurable follow-up levels with customizable delays
  - Email template customization for each level
  - Follow-up history tracking
  - Partner follow-up status dashboard
  - Manual action tracking and notes
  - Integration with overdue invoices

- **Enhanced Analytic Accounting**
  - Extended analytic account features
  - Budget integration with analytic accounts
  - Cost center linkage
  - Enhanced reporting capabilities
  - Budget remaining calculation

- **Security & Permissions**
  - Budget User and Manager groups
  - Asset User and Manager groups
  - Accounting Approver group
  - Row-level security on sensitive data

- **User Interface**
  - Modern, intuitive forms and views
  - Tree views with color coding
  - Advanced search and filtering
  - Dashboard widgets (placeholder)
  - Wizard-based operations

- **Documentation**
  - Comprehensive README
  - Installation guide
  - User guide with examples
  - Technical documentation
  - Module description page

### Technical Details
- Compatible with Odoo 18.0
- Python 3.10+ support
- PostgreSQL database support
- Full ORM integration
- Mail integration (chatter)
- Activity management support

### Dependencies
- base
- account
- account_accountant
- analytic

### Known Limitations
- Dashboard views are placeholder (to be implemented)
- Advanced financial reports need customization
- Multi-currency support is basic (uses company currency)

### Future Enhancements
- Interactive dashboard with charts
- Advanced financial report builder
- Multi-currency asset management
- Budget templates and copying
- Asset group management
- Integration with inventory for asset tracking
- Mobile app support
- REST API endpoints

---

## Version Numbering

Version format: `MAJOR.MINOR.PATCH.BUILD`

- **MAJOR**: Odoo version (18)
- **MINOR**: Feature release (0)
- **PATCH**: Bug fixes and minor improvements (1)
- **BUILD**: Build number (0)

---

## Support

For bug reports, feature requests, or questions:
- Check GitHub Issues
- Contact module developer
- Consult Odoo community forums

---

## License

This module is licensed under LGPL-3.0
