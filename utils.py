import os
from models import ServiceOrder

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_totals(service_order):
    """Calculate final total with discounts and surcharges"""
    # Base total: material + labor
    base_total = service_order.material_total + service_order.labor_total
    
    # Apply general budget if higher
    if service_order.general_budget > base_total:
        base_total = service_order.general_budget
    
    # Apply discount
    if service_order.discount_type == 'percentage':
        discount_amount = base_total * (service_order.discount_value / 100)
    elif service_order.discount_type == 'fixed':
        discount_amount = service_order.discount_value
    else:
        discount_amount = 0
    
    total_after_discount = base_total - discount_amount
    
    # Apply surcharge (max 5%)
    surcharge_amount = total_after_discount * (service_order.surcharge_percentage / 100)
    
    final_total = total_after_discount + surcharge_amount
    
    return max(final_total, 0)  # Ensure total is never negative

def format_currency(value):
    """Format value as Brazilian currency"""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def format_date(date_obj):
    """Format date as dd/mm/yyyy"""
    if date_obj:
        return date_obj.strftime('%d/%m/%Y')
    return ''

def format_datetime(datetime_obj):
    """Format datetime as dd/mm/yyyy HH:MM"""
    if datetime_obj:
        return datetime_obj.strftime('%d/%m/%Y %H:%M')
    return ''
