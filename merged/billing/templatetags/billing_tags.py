from django import template
from django.template.defaulttags import register

register = template.Library()

@register.filter
def sum_total(rentals):
    """Calculate the total amount for a list of rentals."""
    return sum(rental.calculate_total() for rental in rentals)

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key."""
    if not dictionary or not isinstance(dictionary, dict):
        return 0
    return dictionary.get(key, 0)

@register.filter
def all_items_returned(rental_list):
    """Check if all items in a rental list are fully returned."""
    # Only check unbilled rentals
    unbilled_rentals = [rental for rental in rental_list if not rental.is_final_bill_generated]
    if not unbilled_rentals:  # If no unbilled rentals, return True
        return True
    return all(rental.is_fully_returned() for rental in unbilled_rentals)

@register.filter
def subtract(value, arg):
    """Subtract arg from value, handling type conversions and errors."""
    try:
        if isinstance(value, dict):
            value = 0
        if isinstance(arg, dict):
            arg = arg.get(value, 0)  # If arg is a dict, get the value using the first arg as key
        return float(value or 0) - float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def split(value, arg):
    """Split a string by the given separator."""
    if not value:
        return []
    return value.split(arg)

@register.filter
def has_new_items_after_bill(rentals):
    """
    Check if there are any new items added after the last bill generation.
    Returns True if there are new items, False otherwise.
    """
    # Check if any items have been billed
    has_billed_items = any(rental.is_final_bill_generated for rental in rentals)
    
    # If no items have been billed yet, return True
    if not has_billed_items:
        return True

    # Check if any items were added after the first billed item
    for rental in rentals:
        if not rental.is_final_bill_generated:
            # Check if there are any return records
            if rental.return_history.exists():
                # Get the latest return date
                latest_return = rental.return_history.order_by('-return_date').first()
                if latest_return and latest_return.return_date > rental.rent_date:
                    return True
            else:
                # If no returns yet, consider it a new item
                return True

    return False 