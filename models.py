from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import text

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    professional_name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with service orders
    service_orders = db.relationship('ServiceOrder', backref='professional', lazy=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with vehicles and service orders
    vehicles = db.relationship('Vehicle', backref='client', lazy=True, cascade='all, delete-orphan')
    service_orders = db.relationship('ServiceOrder', backref='client', lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    license_plate = db.Column(db.String(10), nullable=False)
    car_model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    color = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with service orders will be handled via queries

class StandardService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    suggested_price = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ServiceOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    os_number = db.Column(db.String(20), unique=True, nullable=False)
    issue_date = db.Column(db.Date, default=datetime.utcnow().date)
    
    # Professional responsible
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Client and vehicle information
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    
    # Financial information
    material_total = db.Column(db.Float, default=0.0)
    labor_total = db.Column(db.Float, default=0.0)
    general_budget = db.Column(db.Float, default=0.0)
    discount_type = db.Column(db.String(10), default='none')  # 'none', 'percentage', 'fixed'
    discount_value = db.Column(db.Float, default=0.0)
    surcharge_percentage = db.Column(db.Float, default=0.0)  # Max 5%
    final_total = db.Column(db.Float, default=0.0)
    
    # Status and payment
    status = db.Column(db.String(20), default='Em andamento')  # Em andamento, Finalizado, Cancelado
    payment_method = db.Column(db.String(50))
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime)
    
    # Additional information
    internal_observations = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with service items
    items = db.relationship('ServiceOrderItem', backref='service_order', lazy=True, cascade='all, delete-orphan')

class ServiceOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Float, default=1.0)
    unit_price = db.Column(db.Float, default=0.0)
    total_price = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CompanyInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default='Sua Empresa Ltda')
    phone = db.Column(db.String(20), default='(11) 99999-9999')
    address = db.Column(db.String(300), default='Rua Example, 123 - Cidade/Estado')
    cnpj = db.Column(db.String(20), default='00.000.000/0001-00')
    logo_filename = db.Column(db.String(255), default='company_logo.svg')
    pix_qr_filename = db.Column(db.String(255), default='qr_pix.svg')
    
    @classmethod
    def get_instance(cls):
        """Get the singleton company info instance"""
        instance = cls.query.first()
        if not instance:
            instance = cls()
            db.session.add(instance)
            db.session.commit()
        return instance

# Function to generate OS number
def generate_os_number():
    from datetime import datetime
    current_year = datetime.now().year
    
    # Get the last OS number for current year
    last_os = ServiceOrder.query.filter(
        ServiceOrder.os_number.like(f'OS-{current_year}-%')
    ).order_by(ServiceOrder.os_number.desc()).first()
    
    if last_os:
        # Extract the sequential number and increment
        last_number = int(last_os.os_number.split('-')[-1])
        next_number = last_number + 1
    else:
        next_number = 1
    
    return f'OS-{current_year}-{next_number:04d}'
