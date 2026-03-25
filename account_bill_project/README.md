# account_bill_project

**Odoo 18 Custom Addons — Vendor Bills dengan Analytic Header, COA Item & Approval Workflow**

---

## Fitur

| Fitur | Keterangan |
|-------|------------|
| **Account Analytic di Header** | Pilih project sekali di header → semua baris otomatis ikut |
| **% Alokasi** | Atur persentase distribusi analytic (default 100%) |
| **Item = COA** | Kolom product disembunyikan, user langsung pilih akun COA |
| **Approval Workflow** | Finance Manager → Direktur Keuangan (jika total ≥ limit) |
| **Batas Direktur Configurable** | Diatur di Accounting → Configuration → Settings |
| **Log Approval** | Setiap aksi approval tercatat di model `account.bill.approval.log` |
| **Notifikasi Chatter** | Pesan otomatis di chatter saat status approval berubah |

---

## Alur Approval

```
Draft
  │
  ▼ [Klik "Ajukan Persetujuan"]
Waiting Finance Manager
  │
  ▼ [Finance Manager klik "Setujui"]
  ├── Total < Limit → Approved ✅
  └── Total ≥ Limit → Waiting Direktur Keuangan
                          │
                          ▼ [Direktur klik "Setujui"]
                        Approved ✅

  (Setiap tahap bisa → Ditolak ❌ dengan alasan)
```

> Tagihan hanya bisa di-**Konfirmasi** (post) setelah status = **Approved**.

---

## Instalasi

```bash
# 1. Copy folder ke direktori addons Odoo
cp -r account_bill_project /path/to/odoo/addons/

# 2. Update apps list
./odoo-bin -d <database> --update=account_bill_project

# 3. Atau install via menu:
#    Settings → Apps → Search "Account Bill Project" → Install
```

---

## Konfigurasi

1. Buka **Accounting → Configuration → Settings**
2. Scroll ke section **Bill Project Approval**
3. Set **Batas Persetujuan Direktur (Rp)** — default: Rp 50.000.000

---

## Security Groups

| Group | Akses |
|-------|-------|
| `group_bill_approval_manager` | Dapat approve/reject sebagai Finance Manager |
| `group_bill_approval_director` | Dapat approve sebagai Direktur Keuangan |

Assign group via **Settings → Users → Edit User → Tab Akses**

---

## Dependensi Odoo

```
account
analytic
mail
```

---

## Struktur File

```
account_bill_project/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── account_move.py           ← Field & logic utama (analytic, approval)
│   ├── account_move_line.py      ← Sync analytic per baris, validasi COA
│   ├── account_bill_approval.py  ← Model log approval
│   └── res_config_settings.py    ← Setting batas direktur
├── wizard/
│   ├── __init__.py
│   ├── bill_rejection_wizard.py  ← Wizard tolak dengan alasan
│   └── bill_approval_wizard_views.xml
├── views/
│   ├── account_move_views.xml    ← Inherit form & list vendor bills
│   ├── account_bill_approval_views.xml ← List pending approval
│   ├── res_config_settings_views.xml
│   └── menus.xml
├── security/
│   ├── ir.model.access.csv
│   └── account_bill_project_security.xml
├── static/
│   └── src/
│       ├── js/
│       │   └── analytic_sync.js  ← OWL patch: sync analytic header → lines
│       └── scss/
│           └── account_bill_project.scss
└── README.md
```

---

## Cara Pakai

### 1. Buat Vendor Bill
- Buka **Accounting → Vendors → Bills → New**
- Isi vendor, tanggal, jurnal seperti biasa

### 2. Set Analytic Header
- Di field **Analytic Account (Project)**: pilih project
- Set **% Alokasi** (default 100%)
- Semua baris akan otomatis menggunakan analytic yang sama

### 3. Isi Baris dengan COA
- Klik **Add a line**
- Pilih **Account** (COA) langsung — kolom product tersembunyi
- Isi qty, harga, keterangan

### 4. Ajukan Persetujuan
- Klik tombol **Ajukan Persetujuan**
- Status berubah → *Menunggu Finance Manager*
- Finance Manager mendapat notifikasi di chatter

### 5. Proses Approval
- Finance Manager buka tagihan → klik **Setujui (Manager)**
- Jika total ≥ limit → lanjut ke Direktur
- Setelah **Approved** → klik **Confirm** untuk posting jurnal

---

## Catatan Pengembang

- `x_analytic_distribution` disimpan sebagai JSON sesuai format Odoo 18 analytic widget
- Sync dari header ke lines terjadi di dua tempat:
  - **Python** (`_onchange_analytic_header`): saat save / server-side
  - **JavaScript** (`analytic_sync.js`): real-time di UI (OWL useEffect patch)
- Jika ingin multi-analytic per baris, cukup hapus sync JS dan biarkan user edit per baris

---

*Odoo 18 Compatible | License: LGPL-3*
