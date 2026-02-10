# POS & Warehouse User Access Control

Modul Odoo 18 untuk mengatur akses user ke POS dan Gudang tertentu.

## Fitur

### 1. **Akses POS per User**
- Assign POS tertentu ke user tertentu (many-to-many relationship)
- User hanya bisa mengakses POS yang sudah di-assign
- Admin/POS Manager bisa mengakses semua POS

### 2. **Akses Gudang per User**
- Assign gudang tertentu ke user tertentu (many-to-many relationship)
- User hanya bisa melihat stok dari gudang yang sudah di-assign
- Admin/Stock Manager bisa melihat semua gudang

### 3. **Manajemen dari 2 Sisi**
- **Dari sisi User**: Lihat dan atur POS & Gudang apa saja yang user bisa akses
- **Dari sisi POS/Gudang**: Lihat dan atur user mana saja yang bisa akses

### 4. **Auto Filtering**
- Stok otomatis ter-filter berdasarkan akses gudang user
- POS otomatis ter-filter berdasarkan akses POS user
- Menggunakan Record Rules untuk keamanan

## Instalasi

1. Copy folder `pos_warehouse_access` ke direktori addons Odoo Anda
2. Restart Odoo server
3. Update Apps List: Settings > Apps > Update Apps List
4. Cari "POS & Warehouse User Access Control"
5. Klik Install

## Penggunaan

### A. Mengatur dari sisi User

1. **Buka Settings > Users & Companies > Users**
2. **Pilih user yang ingin diatur**
3. **Tab "POS Access"**:
   - Pilih POS yang bisa diakses user
   - User hanya akan bisa login ke POS yang dipilih
4. **Tab "Warehouse Access"**:
   - Pilih gudang yang bisa dilihat user
   - User hanya akan bisa lihat stok dari gudang yang dipilih

### B. Mengatur dari sisi POS

1. **Buka Point of Sale > Configuration > Point of Sale**
2. **Pilih POS yang ingin diatur**
3. **Tab "User Access"**:
   - Pilih user yang bisa mengakses POS ini
   - Lihat daftar user yang punya akses

### C. Mengatur dari sisi Gudang

1. **Buka Inventory > Configuration > Warehouses**
2. **Pilih gudang yang ingin diatur**
3. **Tab "User Access"**:
   - Pilih user yang bisa melihat gudang ini
   - Lihat daftar user yang punya akses

## Contoh Skenario

### Skenario 1: Kasir Cabang Tunggal

**User: Andi (Kasir Toko A)**
```
POS Access: 
  ✓ POS Toko A

Warehouse Access:
  ✓ Gudang Jakarta
```

**Hasil:**
- Andi hanya bisa login ke POS Toko A
- Andi hanya bisa lihat stok dari Gudang Jakarta
- Andi TIDAK bisa akses POS atau gudang lain

### Skenario 2: Supervisor Multi Cabang

**User: Budi (Supervisor)**
```
POS Access:
  ✓ POS Toko A
  ✓ POS Toko B
  ✓ POS Toko C

Warehouse Access:
  ✓ Gudang Jakarta
  ✓ Gudang Bandung
```

**Hasil:**
- Budi bisa pilih login ke POS A, B, atau C
- Budi bisa lihat stok gabungan dari Jakarta & Bandung
- Budi bisa monitoring 3 POS sekaligus

### Skenario 3: Staff Gudang (Tanpa Akses POS)

**User: Citra (Staff Inventory)**
```
POS Access:
  (kosong - tidak ada akses POS)

Warehouse Access:
  ✓ Gudang Jakarta
  ✓ Gudang Bandung
  ✓ Gudang Surabaya
```

**Hasil:**
- Citra TIDAK bisa akses POS sama sekali
- Citra bisa kelola stok dari 3 gudang
- Cocok untuk staff inventory/warehouse

### Skenario 4: Admin/Manager

**User: Dedi (Admin/Manager)**
```
Groups:
  ✓ POS Manager / Stock Manager / System Administrator
```

**Hasil:**
- Dedi otomatis bisa akses SEMUA POS
- Dedi otomatis bisa lihat SEMUA gudang
- Tidak perlu setting manual

## Role & Permission

### Regular User (Base User)
- Hanya bisa akses POS & Gudang yang di-assign
- Bisa READ data POS & Gudang
- Tidak bisa WRITE/CREATE/DELETE POS & Gudang

### POS Manager
- Bisa akses SEMUA POS
- Bisa CRUD (Create/Read/Update/Delete) POS
- Bisa mengatur user access ke POS

### Stock Manager
- Bisa lihat SEMUA gudang
- Bisa CRUD gudang
- Bisa mengatur user access ke gudang

### Administrator
- Full access ke semua fitur
- Bypass semua record rules

## Keamanan

Modul ini menggunakan **Record Rules** Odoo untuk memastikan:
- User tidak bisa bypass filter dengan direct URL
- User tidak bisa manipulasi domain filter
- Akses dikontrol di level database (bukan hanya UI)
- Compatible dengan multi-company setup

## Troubleshooting

### User tidak bisa lihat POS/Gudang apapun
**Solusi:**
1. Pastikan user sudah di-assign ke minimal 1 POS/Gudang
2. Atau berikan role POS Manager/Stock Manager
3. Clear browser cache dan refresh

### Admin tidak bisa edit user access
**Solusi:**
1. Pastikan user login sebagai Administrator
2. Atau berikan group Settings > Administration > Settings

### Filter tidak bekerja
**Solusi:**
1. Restart Odoo server setelah install
2. Update module: Apps > POS & Warehouse User Access Control > Upgrade
3. Check ir.rule di Settings > Technical > Security > Record Rules

## Technical Information

### Dependencies
- `base`
- `point_of_sale`
- `stock`

### Models Extended
- `res.users`
- `pos.config`
- `stock.warehouse`
- `stock.quant`

### New Fields
**res.users:**
- `pos_access_ids` (Many2many to pos.config)
- `warehouse_access_ids` (Many2many to stock.warehouse)

**pos.config:**
- `user_access_ids` (Many2many to res.users)

**stock.warehouse:**
- `user_access_ids` (Many2many to res.users)

### Junction Tables
- `pos_user_access_rel`
- `warehouse_user_access_rel`

## Support

Untuk bug report atau feature request, silakan hubungi:
- Email: support@yourcompany.com
- Phone: +62-xxx-xxxx-xxxx

## License

LGPL-3

## Author

Your Company Name
