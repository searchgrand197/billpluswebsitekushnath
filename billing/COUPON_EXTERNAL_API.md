# Coupon generator ↔ Billvice (BMS) integration

This file is maintained **in the Billvice repo** (`billing/COUPON_EXTERNAL_API.md`).  
If the coupon server project keeps a copy under `docs/COUPON_EXTERNAL_API.md`, treat **this** document as the Billvice-side wiring notes; keep them in sync when URLs or behaviour change.

Configure endpoints only in **`billing/coupon_api.py`** (`base_url`, `apply_coupon_path`, `redeem_coupon_path`).

---

## Status (coupon server — implemented)

| Route | Purpose |
|--------|--------|
| `POST /api/coupons/apply` **or** `POST /api/coupons/apply/` | **Validate only** — same lookup rules as redeem (user-owned or admin); rejects missing code, not found, already used, expired; **does not** change DB. |
| `POST /api/redeem` | **Consume coupon** — marks status used, saves. |

**Do not** point `apply_coupon_path` at `/api/redeem`. Apply must not mark coupons used.

---

## 1. Apply / validate (`coupon_apply` → proxy)

**Billvice:** `POST /billing/coupons/apply/` (Django) forwards to `{base_url}{apply_coupon_path}` with the coupon session cookie (`connect.sid` from Settings login).

**Upstream (coupon server):**

- **URLs:** `POST /api/coupons/apply` and `POST /api/coupons/apply/` (both supported).
- **Body (JSON):** `{ "code": "ABC123", "amount": 500.0 }`  
  - `code` — required  
  - `amount` — optional; when sent, server enforces `minAmount` (see below).

**Success:**

- `success: true`, `message: "Coupon is valid"` (or similar)
- `coupon: { title, type, percentage, flat, minAmount, festival }` — same shape as redeem’s coupon object.
- If `amount` was provided, response may also include: `amount`, `discountAmount`, `finalAmount` (server-side preview math).

Billvice **invoice UI** still computes discount from `coupon.type` / `percentage` / `flat` against the **GST-inclusive total** in the browser; the extra `discountAmount` / `finalAmount` fields are optional for display/debug.

**Failure examples:**

- Generic: `{ "success": false, "error": "..." }`
- Minimum order: when `amount < minAmount`:  
  `{ "success": false, "error": "Minimum order not met", "minAmount": ..., "amount": ... }`

---

## 2. Redeem (`create_invoice` → proxy)

**When:** User submits **Create Invoice** (not **Print Token** only), and an external coupon code is present (not manual `10%`).

**Billvice:** Server-side `_redeem_external_coupon_if_needed` → `POST {redeem_coupon_url}` with `{ "code": "ABC123" }` and the same session cookie.

This must remain the **only** path that marks the coupon used in the coupon DB.

---

## 3. Manual discount in Billvice

Entry like `10%` in the coupon box is applied locally; **no** apply/redeem call.

---

## 4. Checklist

1. Coupon server: `apply` + `redeem` as above; auth cookie forwarded like login/create.
2. Billvice: `billing/coupon_api.py` — set `base_url` to your coupon server (e.g. `http://192.168.56.1:3000/`).
3. Billvice: `apply_coupon_path = "/api/coupons/apply/"` (trailing slash OK; server accepts both forms).
