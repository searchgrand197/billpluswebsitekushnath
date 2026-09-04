"""Decimal-safe purchase-order GST and totals (backend is source of truth)."""
from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal('0.01')
GST_RATES = [Decimal('0'), Decimal('5'), Decimal('12'), Decimal('18'), Decimal('28')]
GSTIN_RE = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'


def money(value):
    return Decimal(str(value or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def company_default_gst():
    from .models import CompanySettings
    cs = CompanySettings.objects.first()
    if cs is not None and cs.gst_percentage is not None:
        return Decimal(str(cs.gst_percentage))
    return Decimal('0')


def allowed_gst_rates():
    rates = {Decimal(str(r)) for r in GST_RATES}
    rates.add(company_default_gst())
    return sorted(rates)


def selling_breakdown(before, gst_rate):
    before = money(before)
    rate = Decimal(str(gst_rate or 0))
    gst_amt = money(before * rate / Decimal('100'))
    return before, gst_amt, money(before + gst_amt)


def before_from_inclusive(after, gst_rate):
    after = Decimal(str(after or 0))
    rate = Decimal(str(gst_rate or 0))
    divisor = Decimal('1') + (rate / Decimal('100'))
    if divisor <= 0:
        return money(after), Decimal('0.00'), money(after)
    before = money(after / divisor)
    gst_amt = money(after - before)
    return before, gst_amt, money(after)


# GSTIN first two digits (Haryana = 06)
STATE_NAME_TO_CODE = {
    'andhra pradesh': '37',
    'arunachal pradesh': '12',
    'assam': '18',
    'bihar': '10',
    'chhattisgarh': '22',
    'goa': '30',
    'gujarat': '24',
    'haryana': '06',
    'himachal pradesh': '02',
    'jharkhand': '20',
    'karnataka': '29',
    'kerala': '32',
    'madhya pradesh': '23',
    'maharashtra': '27',
    'manipur': '14',
    'meghalaya': '17',
    'mizoram': '15',
    'nagaland': '13',
    'odisha': '21',
    'punjab': '03',
    'rajasthan': '08',
    'sikkim': '11',
    'tamil nadu': '33',
    'telangana': '36',
    'tripura': '16',
    'uttar pradesh': '09',
    'uttarakhand': '05',
    'west bengal': '19',
    'andaman and nicobar islands': '35',
    'chandigarh': '04',
    'dadra and nagar haveli and daman and diu': '26',
    'delhi': '07',
    'jammu and kashmir': '01',
    'ladakh': '38',
    'lakshadweep': '31',
    'puducherry': '34',
}


def _norm_state(name):
    return ' '.join((name or '').strip().lower().split())


def gstin_state_code(gstin):
    code = (gstin or '').strip().upper()[:2]
    if len(code) == 2 and code.isdigit():
        return code
    return ''


def state_to_code(state_name):
    return STATE_NAME_TO_CODE.get(_norm_state(state_name), '')


def resolve_place_code(gstin='', state_name=''):
    return gstin_state_code(gstin) or state_to_code(state_name)


def is_interstate(party_gstin, company_gstin, party_state='', company_state=''):
    """True when place of supply is a different state than the company (IGST).

    Intra-state (e.g. both Haryana): CGST + SGST.
    Inter-state (Haryana to another state): IGST.
    Unknown / walk-in with no state is treated as intra-state.
    """
    party = resolve_place_code(party_gstin, party_state)
    company = resolve_place_code(company_gstin, company_state)
    if party and company:
        return party != company
    ps, cs = _norm_state(party_state), _norm_state(company_state)
    if ps and cs:
        return ps != cs
    return False


def calc_line(qty, rate, discount, gst_rate, interstate):
    qty = Decimal(str(qty or 0))
    basic = money(qty * Decimal(str(rate or 0)))
    disc = money(discount)
    if disc < 0:
        disc = Decimal('0')
    if disc > basic:
        disc = basic
    taxable = money(basic - disc)
    rate_d = Decimal(str(gst_rate or 0))
    gst = money(taxable * rate_d / Decimal('100'))
    if interstate:
        igst, cgst, sgst = gst, Decimal('0.00'), Decimal('0.00')
    else:
        cgst = money(gst / 2)
        sgst = money(gst - cgst)
        igst = Decimal('0.00')
    total = money(taxable + cgst + sgst + igst)
    return {
        'basic': basic,
        'discount': disc,
        'taxable_amount': taxable,
        'gst_rate': rate_d,
        'cgst': cgst,
        'sgst': sgst,
        'igst': igst,
        'total': total,
    }


def calc_charge(amount, gst_applicable, gst_rate, interstate):
    amt = money(amount)
    if not gst_applicable or amt == 0:
        return {'amount': amt, 'cgst': Decimal('0.00'), 'sgst': Decimal('0.00'), 'igst': Decimal('0.00'), 'total': amt}
    gst = money(amt * Decimal(str(gst_rate or 0)) / Decimal('100'))
    if interstate:
        return {'amount': amt, 'cgst': Decimal('0.00'), 'sgst': Decimal('0.00'), 'igst': gst, 'total': money(amt + gst)}
    cgst = money(gst / 2)
    sgst = money(gst - cgst)
    return {'amount': amt, 'cgst': cgst, 'sgst': sgst, 'igst': Decimal('0.00'), 'total': money(amt + cgst + sgst)}
