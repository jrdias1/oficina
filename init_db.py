#!/usr/bin/env python3
"""
Database initialization script for Service Order Management System
Creates tables and populates with initial data
"""

import os
import sys
from datetime import datetime, date
from werkzeug.security import generate_password_hash

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Client, ServiceOrder, ServiceOrderItem, StandardService, CompanyInfo

def init_database():
    """Initialize the database with tables and sample data"""
    
    with app.app_context():
        # Drop all tables and recreate them
        print("Dropping existing tables...")
        db.drop_all()
        
        print("Creating tables...")
        db.create_all()
        
        # Create company information
        print("Creating company information...")
        company_info = CompanyInfo(
            name="Sua Empresa Ltda",
            phone="(11) 99999-9999",
            address="Rua Example, 123 - São Paulo/SP",
            cnpj="00.000.000/0001-00",
            logo_filename="company_logo.svg",
            pix_qr_filename="qr_pix.svg"
        )
        db.session.add(company_info)
        
        # Create default users
        print("Creating default users...")
        
        # Admin user
        admin_user = User(
            username="admin",
            email="admin@empresa.com",
            password_hash=generate_password_hash("admin123"),
            professional_name="Administrador",
            is_admin=True,
            is_active=True
        )
        db.session.add(admin_user)
        
        # Mechanic user
        mechanic_user = User(
            username="mecanico",
            email="mecanico@empresa.com",
            password_hash=generate_password_hash("mec123"),
            professional_name="João Silva",
            is_admin=False,
            is_active=True
        )
        db.session.add(mechanic_user)
        
        # Technician user
        tech_user = User(
            username="tecnico",
            email="tecnico@empresa.com",
            password_hash=generate_password_hash("tec123"),
            professional_name="Maria Santos",
            is_admin=False,
            is_active=True
        )
        db.session.add(tech_user)
        
        # Create standard services
        print("Creating standard services...")
        
        standard_services = [
            {
                "name": "Troca de Óleo",
                "description": "Troca de óleo do motor e filtro",
                "suggested_price": 80.00,
                "category": "Manutenção"
            },
            {
                "name": "Alinhamento e Balanceamento",
                "description": "Alinhamento da direção e balanceamento das rodas",
                "suggested_price": 120.00,
                "category": "Mecânica"
            },
            {
                "name": "Revisão Geral",
                "description": "Revisão completa do veículo",
                "suggested_price": 200.00,
                "category": "Manutenção"
            },
            {
                "name": "Troca de Pastilhas de Freio",
                "description": "Substituição das pastilhas de freio dianteiras",
                "suggested_price": 150.00,
                "category": "Mecânica"
            },
            {
                "name": "Diagnóstico Eletrônico",
                "description": "Diagnóstico completo do sistema eletrônico",
                "suggested_price": 100.00,
                "category": "Diagnóstico"
            },
            {
                "name": "Troca de Bateria",
                "description": "Substituição da bateria do veículo",
                "suggested_price": 300.00,
                "category": "Elétrica"
            },
            {
                "name": "Reparo no Sistema Elétrico",
                "description": "Diagnóstico e reparo de problemas elétricos",
                "suggested_price": 180.00,
                "category": "Elétrica"
            },
            {
                "name": "Pintura Completa",
                "description": "Pintura completa do veículo",
                "suggested_price": 2500.00,
                "category": "Pintura"
            },
            {
                "name": "Funilaria e Pintura",
                "description": "Reparo de lataria e pintura",
                "suggested_price": 800.00,
                "category": "Funilaria"
            },
            {
                "name": "Troca de Pneus",
                "description": "Montagem e balanceamento de pneus novos",
                "suggested_price": 50.00,
                "category": "Mecânica"
            }
        ]
        
        for service_data in standard_services:
            service = StandardService(**service_data)
            db.session.add(service)
        
        # Commit all changes
        print("Saving changes to database...")
        db.session.commit()
        
        print("Database initialization completed successfully!")
        print("\nDefault users created:")
        print("- Admin: admin / admin123")
        print("- Mecânico: mecanico / mec123")
        print("- Técnico: tecnico / tec123")
        print(f"\nStandard services created: {len(standard_services)}")
        print("\nCompany information created with default values.")
        print("\nYou can now start the application with: python main.py")

def create_sample_data():
    """Create sample clients and service orders for demonstration"""
    
    with app.app_context():
        print("Creating sample data...")
        
        # Get users
        admin_user = User.query.filter_by(username="admin").first()
        mechanic_user = User.query.filter_by(username="mecanico").first()
        
        if not admin_user or not mechanic_user:
            print("Users not found. Please run init_database() first.")
            return
        
        # Create sample clients
        sample_clients = [
            {
                "name": "Carlos Silva",
                "phone": "(11) 98765-4321",
                "license_plate": "ABC-1234",
                "car_model": "Honda Civic 2018"
            },
            {
                "name": "Ana Santos",
                "phone": "(11) 87654-3210",
                "license_plate": "DEF-5678",
                "car_model": "Toyota Corolla 2020"
            },
            {
                "name": "Pedro Oliveira",
                "phone": "(11) 76543-2109",
                "license_plate": "GHI-9012",
                "car_model": "Volkswagen Gol 2019"
            }
        ]
        
        clients = []
        for client_data in sample_clients:
            client = Client(**client_data)
            db.session.add(client)
            clients.append(client)
        
        db.session.flush()  # Get IDs
        
        # Create sample service orders
        from models import generate_os_number
        
        # OS 1 - Completed and paid
        os1 = ServiceOrder(
            os_number=generate_os_number(),
            issue_date=date(2024, 12, 1),
            professional_id=mechanic_user.id,
            client_id=clients[0].id,
            material_total=80.00,
            labor_total=50.00,
            final_total=130.00,
            status="Finalizado",
            payment_method="PIX",
            is_paid=True,
            payment_date=datetime(2024, 12, 1, 16, 30)
        )
        db.session.add(os1)
        db.session.flush()
        
        # Add items to OS1
        item1 = ServiceOrderItem(
            service_order_id=os1.id,
            name="Óleo Motor 5W30",
            quantity=4,
            unit_price=15.00,
            total_price=60.00
        )
        item2 = ServiceOrderItem(
            service_order_id=os1.id,
            name="Filtro de Óleo",
            quantity=1,
            unit_price=20.00,
            total_price=20.00
        )
        db.session.add_all([item1, item2])
        
        # OS 2 - In progress, not paid
        os2 = ServiceOrder(
            os_number=generate_os_number(),
            issue_date=date.today(),
            professional_id=admin_user.id,
            client_id=clients[1].id,
            material_total=300.00,
            labor_total=200.00,
            final_total=500.00,
            status="Em andamento",
            payment_method="Cartão de Crédito",
            is_paid=False
        )
        db.session.add(os2)
        db.session.flush()
        
        # Add items to OS2
        item3 = ServiceOrderItem(
            service_order_id=os2.id,
            name="Pastilhas de Freio",
            quantity=1,
            unit_price=150.00,
            total_price=150.00
        )
        item4 = ServiceOrderItem(
            service_order_id=os2.id,
            name="Discos de Freio",
            quantity=2,
            unit_price=75.00,
            total_price=150.00
        )
        db.session.add_all([item3, item4])
        
        # OS 3 - Completed, not paid
        os3 = ServiceOrder(
            os_number=generate_os_number(),
            issue_date=date(2024, 12, 10),
            professional_id=mechanic_user.id,
            client_id=clients[2].id,
            material_total=120.00,
            labor_total=80.00,
            final_total=200.00,
            status="Finalizado",
            payment_method="Dinheiro",
            is_paid=False,
            internal_observations="Cliente prometeu pagar na próxima semana"
        )
        db.session.add(os3)
        db.session.flush()
        
        # Add items to OS3
        item5 = ServiceOrderItem(
            service_order_id=os3.id,
            name="Alinhamento",
            quantity=1,
            unit_price=60.00,
            total_price=60.00
        )
        item6 = ServiceOrderItem(
            service_order_id=os3.id,
            name="Balanceamento",
            quantity=1,
            unit_price=60.00,
            total_price=60.00
        )
        db.session.add_all([item5, item6])
        
        db.session.commit()
        print(f"Sample data created:")
        print(f"- {len(clients)} clients")
        print(f"- 3 service orders")
        print(f"- 6 service order items")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Service Order Management System database")
    parser.add_argument("--sample", action="store_true", help="Create sample data after initialization")
    parser.add_argument("--sample-only", action="store_true", help="Create only sample data (database must be initialized)")
    
    args = parser.parse_args()
    
    if args.sample_only:
        create_sample_data()
    else:
        init_database()
        if args.sample:
            create_sample_data()
