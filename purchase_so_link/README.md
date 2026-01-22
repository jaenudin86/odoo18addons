# Purchase Order SO Link Module for Odoo 18

Module untuk menghubungkan Purchase Order dengan Sales Order, dengan validasi budget dan reporting lengkap.

## Fitur Utama

### 1. Link Purchase Order ke Sales Order
- **Field SO Wajib**: Setiap Purchase Order harus dikaitkan dengan Sales Order
- **Auto-fill Vendor**: Partner otomatis terisi dari Sales Order
- **Tracking**: Semua perubahan SO di PO akan tercatat

### 2. Validasi Budget
- **Validasi Otomatis**: Sistem akan mencegah konfirmasi PO jika total melebihi SO
- **Perhitungan Real-time**: 
  - Total PO yang sudah dikonfirmasi untuk SO
  - Sisa budget yang tersedia
  - Warning jika mendekati limit
- **Pesan Error Lengkap**: Menampilkan detail perhitungan saat validasi gagal

### 3. Informasi di Purchase Order
- **SO Amount**: Total nilai Sales Order
- **Total PO for SO**: Total semua PO yang sudah dikonfirmasi untuk SO ini
- **Remaining SO Amount**: Sisa budget yang tersedia (dengan indikator warna)

### 4. Informasi di Sales Order
- **Purchase Order Count**: Jumlah PO yang terkait
- **Total Purchase Amount**: Total nilai semua PO terkonfirmasi
- **Remaining Budget**: Sisa budget (dengan indikator warna)
- **Smart Button**: Akses cepat ke semua PO terkait

### 5. Reporting

#### A. Purchase by SO Report (Menu: Purchase > Reporting > Purchase by SO)
Laporan analisa pembelian per Sales Order dengan fitur:
- **Tree View**: Daftar lengkap PO per SO
- **Pivot View**: Analisa dinamis dengan drag & drop
- **Graph View**: Visualisasi bar chart
- **Filter & Group By**:
  - Per SO, Customer, Vendor, Salesperson
  - Per periode (This Month, This Year)
  - Per status PO
- **Aggregation**: Total SO Amount dan PO Amount

#### B. Purchase SO Accounting (Menu: Accounting > Reporting > Purchase SO Accounting)
Laporan untuk departemen accounting dengan fitur:
- **Pivot Analysis**: Analisa keuangan multi-dimensi
- **Line Graph**: Trend pembelian vs penjualan per bulan
- **Filtering**: Berdasarkan periode, customer, status
- **Group By Customer**: Analisa per pelanggan
- **Monthly Breakdown**: Perbandingan SO vs PO per bulan

#### C. PDF Report (Print dari Sales Order)
Report PDF yang bisa dicetak dari Sales Order menampilkan:
- Detail Sales Order
- Daftar semua PO terkait
- Summary budget (SO Amount, Total Purchases, Remaining)
- Status setiap PO

## Instalasi

1. Copy folder `purchase_so_link` ke folder addons Odoo
2. Restart Odoo server
3. Update Apps List
4. Install module "Purchase Order SO Link"

## Konfigurasi

Tidak ada konfigurasi khusus yang diperlukan. Module langsung aktif setelah instalasi.

## Cara Penggunaan

### Membuat Purchase Order Baru

1. Buka **Purchase > Orders > Requests for Quotation**
2. Klik **Create**
3. **Pilih Sales Order** (Field wajib diisi)
4. Sistem akan menampilkan:
   - SO Total Amount
   - Total PO yang sudah dibuat untuk SO ini
   - Remaining budget
5. Isi detail PO seperti biasa
6. Saat **Confirm Order**, sistem akan validasi:
   - ✅ **Berhasil** jika total PO ≤ SO Amount
   - ❌ **Error** jika total PO > SO Amount

### Contoh Validasi

**Scenario:**
- SO Amount: Rp 100.000.000
- PO1 (confirmed): Rp 60.000.000
- PO2 (new): Rp 50.000.000

**Result:**
```
Error: Total Purchase Order amount (Rp 110.000.000) exceeds Sales Order amount (Rp 100.000.000)!

Sales Order: SO001
SO Amount: Rp 100.000.000
Previous PO Total: Rp 60.000.000
Current PO: Rp 50.000.000
Total PO: Rp 110.000.000
Exceeded by: Rp 10.000.000
```

### Melihat Report

#### 1. Purchase by SO Report
- Menu: **Purchase > Reporting > Purchase by SO**
- Gunakan **Pivot View** untuk analisa:
  - Drag field ke Row/Column untuk pivot table
  - Klik angka untuk drill-down detail
- Gunakan **Graph View** untuk visualisasi
- Filter berdasarkan periode, customer, atau status

#### 2. Accounting Report
- Menu: **Accounting > Reporting > Purchase SO Accounting**
- Default view: Pivot dengan group by customer
- Switch ke Graph untuk melihat trend bulanan
- Export ke Excel untuk analisa lebih lanjut

#### 3. Print PDF Report
- Buka Sales Order
- Klik **Print > Purchase by SO Report**
- PDF akan menampilkan detail SO dan semua PO terkait

### Tips Penggunaan

1. **Monitoring Budget**: 
   - Cek field "Remaining SO Amount" di PO sebelum konfirmasi
   - Warna merah = budget habis/exceeded
   - Warna hijau = budget masih tersedia

2. **Smart Button di SO**:
   - Klik badge "X Purchase Orders" untuk melihat semua PO
   - Akses cepat ke semua pembelian untuk SO tersebut

3. **Filtering di Report**:
   - Gunakan filter "This Month" untuk monitoring bulanan
   - Group by "Salesperson" untuk tracking performance
   - Group by "Vendor" untuk analisa supplier

4. **Pivot Analysis**:
   - Drag "Customer" ke Row, "Month" ke Column
   - Lihat pola pembelian per customer per bulan
   - Export ke Excel untuk presentasi

## Field Reference

### Purchase Order
- `sale_order_id`: Many2one ke sale.order (Required)
- `sale_order_amount`: Monetary (Related/Computed)
- `total_po_for_so`: Monetary (Computed)
- `remaining_so_amount`: Monetary (Computed)

### Sale Order
- `purchase_order_ids`: One2many dari purchase.order
- `purchase_order_count`: Integer (Computed)
- `total_purchase_amount`: Monetary (Computed)
- `remaining_purchase_budget`: Monetary (Computed)

## Security

Module menggunakan grup security standar:
- Purchase User: Read, Write, Create
- Purchase Manager: Full access termasuk Delete

## Troubleshooting

**Q: Error saat confirm PO walaupun budget masih cukup**
A: Pastikan semua PO sebelumnya dalam state 'purchase' atau 'done'. PO draft tidak dihitung.

**Q: Tidak bisa pilih SO di PO**
A: Hanya SO dengan status 'Sales Order' atau 'Done' yang bisa dipilih. Quotation tidak bisa dipilih.

**Q: Report kosong**
A: Pastikan ada PO yang sudah terkonfirmasi dan linked ke SO. Filter juga bisa mempengaruhi hasil.

**Q: Angka di report tidak match**
A: Report hanya menghitung PO dengan status 'Purchase Order' dan 'Done'. Draft PO tidak dihitung.

## Support

Untuk bantuan lebih lanjut, hubungi tim IT internal atau dokumentasi Odoo resmi di https://www.odoo.com/documentation/18.0/

## Changelog

### Version 1.0.0
- Initial release
- Purchase Order SO linking
- Budget validation
- Purchase by SO Report
- Accounting Report
- PDF Report
