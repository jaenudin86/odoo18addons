# Advanced Accounting Module for Odoo 18

Module akuntansi lanjutan yang menyediakan fitur-fitur enterprise untuk Odoo 18.

## Fitur Utama

### 1. Budget Management
- Pembuatan dan pengelolaan budget
- Budget lines dengan analytic accounts
- Tracking budget vs actual
- Multi-level approval workflow
- Budget analysis dan reporting

### 2. Asset Management
- Manajemen aset tetap
- Depresiasi otomatis (Linear & Degressive)
- Asset disposal
- Asset transfer
- Depreciation board
- Integration dengan journal entries

### 3. Analytic Accounting Enhancement
- Cost center management
- Enhanced analytic accounts dengan budget tracking
- Analytic distribution
- Multi-dimensional analysis

### 4. Payment Follow-up
- Automated payment reminders
- Multi-level follow-up system
- Email templates
- Follow-up history tracking
- Partner follow-up status

### 5. Cost Center Management
- Hierarchical cost centers
- Cost tracking per department
- Budget allocation per cost center
- Performance analysis

### 6. Financial Reports
- Custom financial report builder
- Flexible report structure
- Multiple display formats
- Comparison capabilities

## Instalasi

1. Copy folder `advanced_accounting` ke dalam addons directory Odoo Anda
2. Update apps list di Odoo
3. Install module "Advanced Accounting"

## Konfigurasi

### Budget Setup
1. Buka Menu: Advanced Accounting > Budgets
2. Buat budget baru dengan periode yang diinginkan
3. Tambahkan budget lines dengan analytic accounts
4. Confirm dan approve budget

### Asset Setup
1. Konfigurasi asset accounts di Chart of Accounts
2. Setup depreciation journals
3. Buat asset baru dari menu Assets
4. Validate asset untuk mulai depresiasi

### Cost Center Setup
1. Buka Menu: Advanced Accounting > Cost Centers
2. Buat cost center hierarchy
3. Assign cost centers ke analytic accounts
4. Link ke budget dan tracking

### Payment Follow-up Setup
1. Konfigurasi follow-up levels di Configuration
2. Customize email templates
3. Set delay periods untuk setiap level
4. Jalankan follow-up wizard secara berkala

## Permissions

Module ini menggunakan beberapa security groups:

- **Budget User**: Dapat melihat dan membuat budget
- **Budget Manager**: Full access ke budget management
- **Asset User**: Dapat melihat dan membuat assets
- **Asset Manager**: Full access ke asset management
- **Accounting Approver**: Dapat approve journal entries

## Dependencies

- base
- account
- account_accountant
- analytic

## Compatibility

- Odoo 18.0 Community dan Enterprise
- Python 3.10+

## Technical Notes

### Models
- `account.budget`: Budget headers
- `account.budget.line`: Budget details
- `account.asset`: Fixed assets
- `account.asset.depreciation.line`: Depreciation schedules
- `account.cost.center`: Cost centers
- `account.payment.followup`: Follow-up levels
- `account.payment.followup.line`: Follow-up history

### Views
Semua models dilengkapi dengan:
- Tree views (list)
- Form views (detail)
- Search views dengan filters
- Kanban views (untuk beberapa models)

### Wizards
- Budget generation wizard
- Report printing wizard
- Batch operations wizards

## Support

Untuk support dan pertanyaan, silakan hubungi developer.

## License

LGPL-3

## Changelog

### Version 18.0.1.0.0
- Initial release
- Budget Management
- Asset Management
- Cost Center Management
- Payment Follow-up
- Enhanced Analytic Accounting
