# Installation Guide - Advanced Accounting Module

## Prerequisites

Sebelum menginstall module ini, pastikan Anda memiliki:

1. Odoo 18.0 (Community atau Enterprise Edition)
2. Python 3.10 atau lebih tinggi
3. Module dependencies:
   - base (included in Odoo)
   - account (included in Odoo)
   - account_accountant
   - analytic

## Installation Steps

### Step 1: Download Module

Download atau clone module `advanced_accounting` ke komputer Anda.

### Step 2: Copy to Addons Directory

Copy folder `advanced_accounting` ke dalam direktori addons Odoo Anda:

```bash
# Untuk Linux/Mac
cp -r advanced_accounting /path/to/odoo/addons/

# Atau tambahkan path custom addons di config file
# addons_path = /path/to/odoo/addons,/path/to/custom/addons
```

### Step 3: Update Apps List

1. Login ke Odoo sebagai Administrator
2. Aktifkan Developer Mode:
   - Settings > Activate Developer Mode
3. Update Apps List:
   - Apps > Update Apps List
   - Klik tombol "Update"

### Step 4: Install Module

1. Buka menu Apps
2. Hapus filter "Apps" di search bar
3. Cari "Advanced Accounting"
4. Klik tombol "Install"

### Step 5: Verify Installation

Setelah instalasi selesai, Anda akan melihat menu baru:
- Advanced Accounting di main menu

## Post-Installation Configuration

### 1. Setup Chart of Accounts

Pastikan chart of accounts Anda sudah dikonfigurasi dengan accounts untuk:
- Fixed Assets (Account Type: Fixed Assets)
- Accumulated Depreciation (Account Type: Fixed Assets)
- Depreciation Expense (Account Type: Expenses)

### 2. Configure Journals

Buat journal khusus untuk:
- Depreciation Journal (Type: General)
- Asset Journal (Type: General)

### 3. Setup Payment Follow-up

Data default sudah ter-install, tapi Anda bisa customize:
1. Go to: Advanced Accounting > Payment Follow-up > Follow-up Levels
2. Edit levels sesuai kebutuhan perusahaan
3. Customize email templates

### 4. Create Cost Centers (Optional)

Jika menggunakan cost center:
1. Go to: Advanced Accounting > Cost Centers
2. Create hierarchical structure
3. Link to analytic accounts

### 5. User Permissions

Assign appropriate groups to users:
- Budget User/Manager
- Asset User/Manager
- Accounting Approver

## Troubleshooting

### Module tidak muncul di Apps List

- Pastikan folder ada di direktori addons
- Restart Odoo service
- Update apps list lagi

### Error saat Install

- Check log file: `/var/log/odoo/odoo-server.log`
- Pastikan semua dependencies ter-install
- Check database access rights

### Missing Menu Items

- Refresh browser (Ctrl+F5)
- Clear browser cache
- Check user permissions

## Upgrade from Previous Version

Jika Anda upgrade dari versi sebelumnya:

```bash
# Backup database terlebih dahulu
pg_dump odoo_db > backup.sql

# Update module
odoo-bin -u advanced_accounting -d odoo_db
```

## Uninstall

Untuk uninstall module:

1. Go to Apps
2. Cari "Advanced Accounting"
3. Klik "Uninstall"
4. Confirm uninstallation

**Warning**: Uninstall akan menghapus semua data yang terkait dengan module ini.

## Support

Jika mengalami masalah saat instalasi:
1. Check Odoo logs
2. Verify Python version
3. Check module dependencies
4. Contact module developer

## Additional Resources

- [Odoo Official Documentation](https://www.odoo.com/documentation/18.0/)
- Module README.md
- Module source code comments
