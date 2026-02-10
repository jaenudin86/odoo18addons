# Quick Start Guide

Panduan cepat menggunakan modul **POS & Warehouse User Access Control** untuk Odoo 18.

## 🚀 Instalasi Cepat

### 1. Upload Module

```bash
# Extract ZIP file
unzip pos_warehouse_access.zip -d /path/to/odoo/addons/

# Restart Odoo
sudo systemctl restart odoo
```

### 2. Install di Odoo

1. Login sebagai **Administrator**
2. Pergi ke **Apps**
3. Update Apps List (jika perlu)
4. Cari **"POS & Warehouse User Access Control"**
5. Klik **Activate/Install**
6. Tunggu instalasi selesai

## 📝 Penggunaan 5 Menit

### Skenario: Setup Kasir untuk Toko Cabang

**Goal:** User "Andi" hanya bisa pakai POS Toko A dan lihat stok Gudang Jakarta

#### Step 1: Buat/Pilih User

1. **Settings → Users & Companies → Users**
2. Create new user atau pilih existing user
3. Name: `Andi Kasir`
4. Login: `andi@tokoa.com`
5. Password: buat password
6. Access Rights: pilih **Point of Sale / User**

#### Step 2: Assign POS

1. Masih di form user "Andi"
2. Klik tab **"POS Access"**
3. Di field "POS Access", pilih **POS Toko A**
4. List di bawah akan muncul detail POS Toko A

#### Step 3: Assign Gudang

1. Masih di form user "Andi"
2. Klik tab **"Warehouse Access"**
3. Di field "Warehouse Access", pilih **Gudang Jakarta**
4. List di bawah akan muncul detail Gudang Jakarta

#### Step 4: Save & Test

1. Klik **Save**
2. Logout dari Administrator
3. Login sebagai **andi@tokoa.com**
4. Buka Point of Sale
5. Cek: Andi hanya bisa lihat POS Toko A
6. Buka Inventory → Products → Update Stock
7. Cek: Andi hanya bisa lihat stok Gudang Jakarta ✅

## 🎯 Use Cases

### Use Case 1: Kasir Tunggal (1 POS, 1 Gudang)

```
User: Kasir Toko A
POS Access: [POS Toko A]
Warehouse Access: [Gudang Jakarta]
```

**Hasil:** Hanya bisa pakai POS Toko A, hanya lihat stok Gudang Jakarta

---

### Use Case 2: Supervisor Multi Cabang (3 POS, 2 Gudang)

```
User: Supervisor Region
POS Access: [POS Toko A, POS Toko B, POS Toko C]
Warehouse Access: [Gudang Jakarta, Gudang Bandung]
```

**Hasil:** Bisa pilih POS mana mau dipakai, bisa monitoring stok 2 gudang

---

### Use Case 3: Staff Gudang (No POS, Multiple Gudang)

```
User: Staff Inventory
POS Access: [] (kosong)
Warehouse Access: [Gudang Jakarta, Gudang Bandung, Gudang Surabaya]
```

**Hasil:** Tidak bisa akses POS, tapi bisa kelola stok 3 gudang

---

### Use Case 4: Manager (Full Access)

```
User: Manager
Groups: [POS Manager, Stock Manager]
POS Access: (tidak perlu setting, otomatis ALL)
Warehouse Access: (tidak perlu setting, otomatis ALL)
```

**Hasil:** Otomatis bisa akses SEMUA POS dan SEMUA gudang

## 🔍 Cek dari Sisi Lain

### Lihat User yang Akses POS Tertentu

1. **Point of Sale → Configuration → Point of Sale**
2. Pilih POS (misal: POS Toko A)
3. Klik tab **"User Access"**
4. Lihat daftar user yang bisa pakai POS ini
5. Bisa tambah/hapus user dari sini juga

### Lihat User yang Akses Gudang Tertentu

1. **Inventory → Configuration → Warehouses**
2. Pilih Gudang (misal: Gudang Jakarta)
3. Klik tab **"User Access"**
4. Lihat daftar user yang bisa lihat gudang ini
5. Bisa tambah/hapus user dari sini juga

## 🔧 Tips & Tricks

### Tip 1: Smart Buttons

Di form User, ada smart buttons:
- **POS Access (angka)** → Klik untuk lihat list POS yang user akses
- **Warehouse Access (angka)** → Klik untuk lihat list gudang yang user akses

### Tip 2: Many2Many Tags

Field akses menggunakan widget tags yang mudah:
- Klik field → dropdown muncul
- Pilih multiple items dengan klik
- Remove dengan klik "X" di tag

### Tip 3: Empty Access = No Access

Jika:
- POS Access kosong → User TIDAK bisa akses POS apapun
- Warehouse Access kosong → User TIDAK bisa lihat stok apapun
- Kecuali user adalah Manager/Admin

### Tip 4: Manager Bypass

User dengan role berikut bypass semua filter:
- **POS Manager** → Lihat semua POS
- **Stock Manager** → Lihat semua gudang
- **Administrator** → Full access everything

## ⚠️ Common Mistakes

### ❌ Mistake 1: Lupa Assign Access

**Problem:** User sudah dibuat tapi tidak bisa lihat apapun

**Solution:** 
- Check tab "POS Access" → pastikan ada POS yang dipilih
- Check tab "Warehouse Access" → pastikan ada gudang yang dipilih

### ❌ Mistake 2: User Punya Role Manager

**Problem:** Filter tidak bekerja meskipun sudah assign

**Solution:**
- Check Access Rights user
- Jika user punya role "POS Manager" atau "Stock Manager", filter tidak berlaku
- Remove role tersebut jika ingin filter bekerja

### ❌ Mistake 3: Gudang Tidak Ada Stock Location

**Problem:** User sudah assign gudang tapi tetap tidak bisa lihat stok

**Solution:**
- Pastikan gudang punya stock location yang benar
- Check di Inventory → Configuration → Locations
- Pastikan location linked ke warehouse

## 📊 Demo Data

Module ini include demo data untuk testing:

**Demo Users:**
- Login: `kasir.a@demo.com` / Password: `demo123`
  - Access: POS Toko A, Gudang Jakarta
  
- Login: `supervisor@demo.com` / Password: `demo123`
  - Access: POS Toko A/B/C, Gudang Jakarta/Bandung
  
- Login: `warehouse@demo.com` / Password: `demo123`
  - Access: No POS, Gudang Jakarta/Bandung/Surabaya

**Demo POS:**
- POS Toko A (Warehouse: Jakarta)
- POS Toko B (Warehouse: Bandung)
- POS Toko C (Warehouse: Surabaya)

**Demo Warehouses:**
- Gudang Jakarta (Code: JKT)
- Gudang Bandung (Code: BDG)
- Gudang Surabaya (Code: SBY)

**Note:** Demo data hanya load jika install dengan demo data enabled

## 🆘 Need Help?

### Module Tidak Terinstall?

1. Check Odoo log: `tail -f /var/log/odoo/odoo-server.log`
2. Pastikan dependencies terinstall (point_of_sale, stock)
3. Check file permissions
4. Lihat INSTALL.md untuk troubleshooting lengkap

### Filter Tidak Bekerja?

1. Clear browser cache
2. Logout dan login ulang
3. Check user tidak punya role Manager
4. Update module: Apps → Upgrade

### Smart Button Tidak Muncul?

1. Update module
2. Hard refresh browser (Ctrl+Shift+R)
3. Check developer mode enabled

### Contact Support

- Email: support@yourcompany.com
- Documentation: Baca README.md dan INSTALL.md
- Report bugs: Include log file dan screenshot

## ✅ Checklist Implementasi

Sebelum go-live, pastikan:

- [ ] Module terinstall dengan benar
- [ ] Semua POS sudah ada di system
- [ ] Semua gudang sudah ada di system
- [ ] User sudah dibuat dengan role yang benar
- [ ] Setiap user sudah di-assign POS dan gudang
- [ ] Test login sebagai user biasa (bukan admin)
- [ ] Verify user hanya lihat POS/gudang yang di-assign
- [ ] Test dengan multiple users
- [ ] Backup database sebelum production
- [ ] Train user cara pakai system

## 🎓 Best Practices

1. **Principle of Least Privilege**: Berikan access minimal yang dibutuhkan
2. **Regular Audit**: Review access setiap bulan
3. **Document Access**: Catat siapa akses apa dan kenapa
4. **Test First**: Test di development/staging dulu
5. **Backup Always**: Backup sebelum major changes
6. **User Training**: Train user sebelum rollout
7. **Monitor Usage**: Pantau siapa akses apa

---

**Happy POS-ing! 🎉**
