# Laravel Integration Example

## Setup API Key di Odoo

### Cara 1 – Environment Variable (Recommended)
Tambahkan di server Odoo (`.env` atau `systemd service`):
```
PRODUCT_API_KEY=your-secret-key-here
```

### Cara 2 – Odoo System Parameter
Masuk ke: **Settings → Technical → System Parameters**
- Key: `product_serial_api.key`
- Value: `your-secret-key-here`

---

## Laravel Service Class

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;

class OdooProductService
{
    private string $baseUrl;
    private string $apiKey;

    public function __construct()
    {
        $this->baseUrl = config('services.odoo.url');  // e.g. https://odoo.yourdomain.com
        $this->apiKey  = config('services.odoo.api_key');
    }

    /**
     * Get product variant by serial number
     */
    public function getBySerial(string $serialNumber): array
    {
        $response = Http::withHeaders([
            'X-API-Key' => $this->apiKey,
        ])->get("{$this->baseUrl}/api/product/serial/{$serialNumber}");

        if ($response->failed()) {
            throw new \Exception($response->json('error') ?? 'Odoo API error');
        }

        return $response->json();
    }

    /**
     * Search serial numbers (partial match)
     */
    public function searchSerials(string $query = '', int $limit = 20, int $offset = 0): array
    {
        $response = Http::withHeaders([
            'X-API-Key' => $this->apiKey,
        ])->get("{$this->baseUrl}/api/product/serials", [
            'q'      => $query,
            'limit'  => $limit,
            'offset' => $offset,
        ]);

        if ($response->failed()) {
            throw new \Exception($response->json('error') ?? 'Odoo API error');
        }

        return $response->json();
    }
}
```

---

## config/services.php

```php
'odoo' => [
    'url'     => env('ODOO_URL', 'http://localhost:8069'),
    'api_key' => env('ODOO_API_KEY', ''),
],
```

## .env Laravel

```
ODOO_URL=https://odoo.yourdomain.com
ODOO_API_KEY=your-secret-key-here
```

---

## Controller Laravel

```php
<?php

namespace App\Http\Controllers;

use App\Services\OdooProductService;
use Illuminate\Http\Request;

class ProductController extends Controller
{
    public function __construct(private OdooProductService $odoo) {}

    public function showBySerial(string $serial)
    {
        try {
            $data = $this->odoo->getBySerial($serial);
            return view('product.detail', ['product' => $data]);
        } catch (\Exception $e) {
            abort(404, $e->getMessage());
        }
    }

    public function search(Request $request)
    {
        $results = $this->odoo->searchSerials(
            $request->get('q', ''),
            $request->get('limit', 20),
            $request->get('offset', 0),
        );
        return response()->json($results);
    }
}
```

---

## Contoh Response GET /api/product/serial/SN-001

```json
{
  "success": true,
  "serial_number": "SN-001",
  "product_variant": {
    "id": 5,
    "name": "Laptop [8GB, Black]",
    "internal_ref": "LAP-001",
    "barcode": "123456789",
    "sale_price": 15000000.0,
    "cost_price": 12000000.0,
    "uom": "Unit(s)",
    "template": {
      "id": 3,
      "name": "Laptop",
      "description": "High performance laptop",
      "category": "All / Saleable",
      "image_url": "/web/image/product.template/3/image_1920"
    },
    "attributes": [
      {"attribute": "RAM",   "value": "8GB"},
      {"attribute": "Color", "value": "Black"}
    ]
  },
  "stock_lot": {
    "id": 12,
    "lot_name": "SN-001",
    "expiration_date": null,
    "qty_available": 1.0,
    "locations": ["WH/Stock"],
    "company": "Your Company"
  }
}
```
