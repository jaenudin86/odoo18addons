# BOM Enhanced Reports Module for Odoo 18

## Deskripsi
Module ini menambahkan fitur-fitur berikut pada Bill of Materials (BOM) di Odoo 18:

### Fitur Utama:
1. **Serial Number Otomatis** - Setiap BOM mendapatkan nomor serial unik otomatis (format: BOM/00001)
2. **Referensi Sales Order** - Field optional untuk menghubungkan BOM dengan Sales Order
3. **2 Jenis Report Profesional:**
   - Report dengan Harga (Cost Analysis) - Menampilkan unit price dan total cost
   - Report tanpa Harga (Technical Specification) - Menampilkan spesifikasi teknis saja
4. **Tampilan Modern** - Design profesional dengan logo perusahaan dan alamat
5. **Layout Responsive** - Optimized untuk cetak dan PDF

## Instalasi

### 1. Copy Module
```bash
cp -r bom_enhanced /path/to/odoo/addons/
```

### 2. Update Apps List
- Login ke Odoo sebagai Administrator
- Aktifkan Developer Mode (Settings > Developer Tools > Activate Developer Mode)
- Pergi ke Apps menu
- Klik "Update Apps List"
- Cari "BOM Enhanced Reports"
- Klik Install

## Penggunaan

### Membuat BOM Baru
1. Pergi ke Manufacturing > Products > Bills of Materials
2. Klik Create
3. Serial Number akan terisi otomatis
4. Isi field:
   - Product: Pilih produk
   - Sales Order: (Optional) Pilih SO jika ada
   - Components: Tambahkan komponen-komponen
5. Save

### Mencetak Report

#### Dari Form View:
1. Buka BOM yang ingin dicetak
2. Klik tombol:
   - **"Print with Price"** - Untuk report dengan harga
   - **"Print without Price"** - Untuk report tanpa harga

#### Dari Tree View:
1. Pilih satu atau beberapa BOM (checkbox)
2. Klik Action > Print
3. Pilih:
   - "BOM Report (With Price)" atau
   - "BOM Report (No Price)"

### Fitur Report

#### Report With Price (Cost Analysis):
- Menampilkan semua komponen dengan:
  - Product Code
  - Product Name
  - Quantity
  - Unit Price
  - Subtotal
- Total Cost di bagian bawah
- Signature section (Prepared by & Approved by)

#### Report No Price (Technical Specification):
- Menampilkan komponen tanpa harga:
  - Product Code
  - Product Name
  - Quantity
  - UoM
- Manufacturing instructions
- 3 Signature sections (Prepared, Reviewed, Approved)

## Struktur Module

```
bom_enhanced/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── mrp_bom.py
├── views/
│   └── mrp_bom_views.xml
├── reports/
│   ├── bom_reports.xml
│   ├── bom_report_with_price.xml
│   └── bom_report_no_price.xml
├── data/
│   └── sequence_data.xml
├── security/
│   └── ir.model.access.csv
└── static/
    └── src/
        └── css/
            └── report_style.css
```

## Konfigurasi

### Mengubah Format Serial Number:
Edit file `data/sequence_data.xml`:
```xml
<field name="prefix">BOM/</field>
<field name="padding">5</field>
```

### Customisasi Tampilan Report:
Edit file `static/src/css/report_style.css` untuk mengubah warna, font, atau layout.

### Mengubah Logo & Alamat Perusahaan:
1. Pergi ke Settings > Companies > Update Info
2. Upload logo perusahaan
3. Isi alamat lengkap
4. Logo dan alamat akan otomatis muncul di report

## Dependencies
- mrp (Manufacturing)
- sale_management (Sales)
- stock (Inventory)

## Versi
- Odoo Version: 18.0
- Module Version: 1.0.0

## Support
Untuk pertanyaan atau issues, silakan hubungi tim development.

## Lisensi
LGPL-3

---

## Changelog

### Version 1.0.0 (2025-01-26)
- Initial release
- Serial number untuk BOM
- Sales Order reference field
- 2 jenis report (with/without price)
- Professional layout dengan CSS styling
