# Work Center Custom Code Module for Odoo 18

## Deskripsi
Module ini menambahkan field custom untuk Work Center di Odoo 18 dengan format pengkodean khusus yang mengikuti struktur divisi perusahaan.

## Format Kode Work Center
```
EQT.[DEPT].[CODE].00000
```

**Contoh:**
- Office: `EQT.OFF.SLS.00000` (Sales)
- Manufacturing: `EQT.MFR.FRD.00000` (Foundry)

## Fitur

### 1. Field Baru di Work Center
- **Tujuan**: Default "EQT" (Company code)
- **ID DIVISI**: Kode divisi 3 huruf (OFF, MFR, FN1, dll)
- **DIVISI**: Nomor divisi (1, 2, 12.1, dll)
- **Devisi**: Nama divisi (Sales, Marketing, Production)
- **Department Type**: Office atau Manufacturing
- **Short Code**: Kode 3 huruf untuk work center
- **Sequence Number**: Nomor urut 5 digit
- **Code**: Auto-generate berdasarkan field di atas

### 2. Auto-Generate Code
Code akan otomatis dibuat dengan format:
- Office Department: `EQT.OFF.[SHORT_CODE].00000`
- Manufacturing: `EQT.MFR.[SHORT_CODE].00000`

### 3. Validasi
- Short Code harus tepat 3 karakter
- Sequence Number harus tepat 5 digit angka
- Auto uppercase untuk Short Code

### 4. Demo Data
Module ini dilengkapi dengan contoh work center:

**Office Department:**
- EQT.OFF.SLS.00000 - Sales
- EQT.OFF.MRK.00000 - Marketing
- EQT.OFF.FN1.00000 - Keuangan 1
- EQT.OFF.DND.00000 - Design & Drawing
- EQT.OFF.RND.00000 - R&D

**Manufacturing:**
- EQT.MFR.FRD.00000 - Foundry
- EQT.MFR.MCH.00000 - Machining
- EQT.MFR.PNT.00000 - Painting
- EQT.MFR.ASY.00000 - Assembly
- EQT.MFR.TST.00000 - Testing
- EQT.MFR.PCK.00000 - Packing

## Instalasi

### 1. Copy Module ke Addons Directory
```bash
cp -r workcenter_custom_code /path/to/odoo/addons/
```

### 2. Update Apps List
```bash
# Restart Odoo service
sudo systemctl restart odoo

# Atau via command line
./odoo-bin -c /path/to/odoo.conf -u all
```

### 3. Install Module
1. Login sebagai Administrator
2. Buka **Apps**
3. Hapus filter "Apps" untuk melihat semua module
4. Search "Work Center Custom Code"
5. Klik **Install**

## Penggunaan

### Membuat Work Center Baru

1. **Buka Manufacturing > Configuration > Work Centers**
2. **Klik Create**
3. **Isi Field:**
   - Name: Nama work center
   - Division ID: Kode divisi (OFF/MFR/dll)
   - DIVISI: Nomor divisi
   - Devisi: Nama divisi
   - Department Type: Pilih Office atau Manufacturing
   - Short Code: 3 huruf kode (akan auto uppercase)
   - Sequence Number: 5 digit (default: 00000)
4. **Code akan otomatis dibuat**

### Filter & Group By

**Filter tersedia:**
- Office Department
- Manufacturing Department

**Group By:**
- Department Type
- Division ID

## Struktur File

```
workcenter_custom_code/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── mrp_workcenter.py
├── views/
│   └── mrp_workcenter_views.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── workcenter_demo_data.xml
└── README.md
```

## Technical Details

### Dependencies
- mrp (Manufacturing module)

### Model Inheritance
- `mrp.workcenter`

### Fields Added
```python
- tujuan (Char): Default 'EQT'
- division_id (Char): 3 characters
- divisi (Char): Division number
- devisi (Char): Division name
- department_type (Selection): office/manufacturing
- short_code (Char): 3 characters
- sequence_number (Char): 5 digits
- code (Char): Computed field
```

### Computed Method
```python
@api.depends('tujuan', 'department_type', 'short_code', 'sequence_number')
def _compute_workcenter_code(self):
    # Auto-generate code format
```

## Customization

### Mengubah Default Company Code
Edit di `models/mrp_workcenter.py`:
```python
tujuan = fields.Char(
    string='Tujuan',
    default='YOUR_CODE',  # Ganti EQT dengan kode perusahaan Anda
    required=True,
)
```

### Menambah Validation Custom
Edit method `_check_short_code` atau `_check_sequence_number`

## Troubleshooting

### Code tidak auto-generate
- Pastikan field Department Type dan Short Code sudah diisi
- Check apakah ada error di log Odoo

### Module tidak muncul di Apps
- Pastikan module sudah di-copy ke directory addons yang benar
- Update apps list
- Restart Odoo service

### Permission Error
- Check file `security/ir.model.access.csv`
- Pastikan user memiliki role Manufacturing/User atau Manager

## Support & Contact
Untuk pertanyaan atau issues, silakan hubungi tim development.

## License
LGPL-3

## Version History
- **v18.0.1.0.0** - Initial release
  - Basic work center code generation
  - Division fields
  - Auto code generation
  - Demo data
