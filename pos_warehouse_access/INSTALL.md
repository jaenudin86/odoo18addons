# Installation Guide

## Instalasi Manual

### 1. Download Module

Download atau clone repository ini ke komputer Anda.

### 2. Copy ke Addons Directory

Copy folder `pos_warehouse_access` ke direktori addons Odoo Anda. Biasanya lokasi default:

```bash
# Linux
/opt/odoo/addons/
# atau
/usr/lib/python3/dist-packages/odoo/addons/

# Windows
C:\Program Files\Odoo 18.0\server\odoo\addons\

# Development
~/odoo/addons/
```

Atau jika menggunakan custom addons path:

```bash
# Copy ke custom addons
cp -r pos_warehouse_access /path/to/your/custom/addons/
```

### 3. Update Addons Path (Opsional)

Jika belum mengatur custom addons path, tambahkan di `odoo.conf`:

```ini
[options]
addons_path = /opt/odoo/addons,/path/to/custom/addons
```

### 4. Restart Odoo Server

```bash
# Service
sudo systemctl restart odoo

# Manual
./odoo-bin -c /path/to/odoo.conf

# Docker
docker restart odoo
```

### 5. Update Apps List

1. Login sebagai Administrator
2. Aktifkan Developer Mode: Settings → Activate Developer Mode
3. Go to Apps → Update Apps List
4. Klik "Update" dan tunggu proses selesai

### 6. Install Module

1. Apps → Search "POS & Warehouse User Access Control"
2. Klik "Activate" atau "Install"
3. Tunggu instalasi selesai

## Instalasi via Docker

Jika menggunakan Docker, tambahkan volume mount:

```yaml
# docker-compose.yml
services:
  odoo:
    image: odoo:18.0
    volumes:
      - ./addons:/mnt/extra-addons
      - ./pos_warehouse_access:/mnt/extra-addons/pos_warehouse_access
```

Kemudian:

```bash
docker-compose restart
```

## Instalasi via Git

```bash
cd /path/to/addons
git clone https://github.com/yourcompany/pos_warehouse_access.git
sudo systemctl restart odoo
```

## Verifikasi Instalasi

### 1. Check Technical Menu

Settings → Technical → Database Structure → Models

Cari:
- `res.users` (harus ada field `pos_access_ids` dan `warehouse_access_ids`)
- `pos.config` (harus ada field `user_access_ids`)
- `stock.warehouse` (harus ada field `user_access_ids`)

### 2. Check Views

Settings → Technical → User Interface → Views

Cari views dengan nama:
- `res.users.form.pos.warehouse.access`
- `pos.config.form.user.access`
- `stock.warehouse.form.user.access`

### 3. Check Security

Settings → Technical → Security → Record Rules

Harus ada rules:
- `POS: User Access Only`
- `Warehouse: User Access Only`
- `Stock Quant: User Warehouse Access`

### 4. Test Functionality

1. Buka Settings → Users
2. Pilih user test
3. Pastikan ada tab "POS Access" dan "Warehouse Access"
4. Assign POS/Gudang ke user
5. Login sebagai user tersebut
6. Verifikasi hanya POS/Gudang yang di-assign yang terlihat

## Troubleshooting

### Module tidak muncul di Apps List

**Solusi:**
```bash
# Update apps list dari command line
./odoo-bin -c odoo.conf -u all -d database_name --stop-after-init
```

### Error saat install: "Module not found"

**Solusi:**
1. Pastikan folder `pos_warehouse_access` berada di addons path
2. Check permission folder (harus readable oleh user odoo)
   ```bash
   sudo chown -R odoo:odoo /path/to/addons/pos_warehouse_access
   sudo chmod -R 755 /path/to/addons/pos_warehouse_access
   ```

### Error: "Could not execute the ir.model.access CSV"

**Solusi:**
1. Pastikan file `security/ir.model.access.csv` ada dan valid
2. Check syntax CSV (no extra commas, proper headers)
3. Reinstall module dengan force:
   ```bash
   ./odoo-bin -c odoo.conf -u pos_warehouse_access -d database_name --stop-after-init
   ```

### Views tidak muncul

**Solusi:**
1. Clear browser cache
2. Update module: Apps → POS & Warehouse User Access Control → Upgrade
3. Check developer mode: Settings → Technical → Views

### Record Rules tidak bekerja

**Solusi:**
1. Check ir.rule: Settings → Technical → Security → Record Rules
2. Pastikan groups sudah benar
3. Test dengan user yang tidak punya group POS Manager/Stock Manager
4. Restart Odoo server

### Field tidak muncul di form

**Solusi:**
1. Update module
2. Clear cache
3. Check view inheritance di Technical → Views
4. Pastikan `inherit_id` benar

## Upgrade dari Odoo 17

Jika upgrade dari Odoo 17, perhatikan:

1. **View syntax berubah:** `<tree>` menjadi `<list>`
2. **Widget changes:** Beberapa widget deprecated
3. **Re-install module:** Uninstall versi lama, install versi 18

```bash
# Backup database dulu!
pg_dump database_name > backup.sql

# Upgrade Odoo
# Kemudian install module versi 18
```

## Dependencies

Pastikan module dependencies sudah terinstall:

```
✓ base (Built-in)
✓ point_of_sale (Apps → Search "Point of Sale" → Install)
✓ stock (Apps → Search "Inventory" → Install)
```

## Uninstall

Jika ingin uninstall module:

1. Apps → Search "POS & Warehouse User Access Control"
2. Klik "Uninstall"
3. Confirm uninstall

**Warning:** 
- Semua data relasi user-pos dan user-warehouse akan hilang
- Backup database dulu sebelum uninstall!

## Support

Jika masih ada masalah:

1. Check Odoo log file:
   ```bash
   tail -f /var/log/odoo/odoo-server.log
   ```

2. Enable debug mode dan lihat error detail

3. Contact support: support@yourcompany.com
