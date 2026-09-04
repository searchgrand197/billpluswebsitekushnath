from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def parse_rental_details(notes):
    """Parse rental details from invoice notes."""
    details = []
    lines = notes.split('\n')
    current_item = {}
    
    for line in lines:
        line = line.strip()
        if line.startswith('Product:'):
            if current_item:
                details.append(current_item)
            current_item = {'product': line[8:].strip()}
        elif line.startswith('Quantity:'):
            current_item['quantity'] = line[9:].strip()
        elif line.startswith('Days:'):
            current_item['days'] = line[5:].strip()
        elif line.startswith('Amount:'):
            current_item['amount'] = line[7:].strip()
    
    if current_item:
        details.append(current_item)
    
    return details 