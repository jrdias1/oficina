import os
import io
import pandas as pd
from datetime import datetime, date
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from app import app, db
from models import User, Client, Vehicle, ServiceOrder, ServiceOrderItem, StandardService, CompanyInfo, generate_os_number
from utils import allowed_file, calculate_totals

@app.route('/')
@login_required
def dashboard():
    """Main dashboard with recent orders and statistics"""
    # Get recent orders
    recent_orders = ServiceOrder.query.order_by(ServiceOrder.created_at.desc()).limit(10).all()
    
    # Get statistics
    total_orders = ServiceOrder.query.count()
    pending_orders = ServiceOrder.query.filter_by(status='Em andamento').count()
    unpaid_orders = ServiceOrder.query.filter_by(is_paid=False).count()
    
    # Get today's revenue
    today = date.today()
    today_revenue = db.session.query(db.func.sum(ServiceOrder.final_total)).filter(
        db.func.date(ServiceOrder.created_at) == today,
        ServiceOrder.is_paid == True
    ).scalar() or 0
    
    return render_template('dashboard.html',
                         recent_orders=recent_orders,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         unpaid_orders=unpaid_orders,
                         today_revenue=today_revenue)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Logout realizado com sucesso!', 'info')
    return redirect(url_for('login'))

@app.route('/create_os', methods=['GET', 'POST'])
@login_required
def create_os():
    """Create new service order"""
    if request.method == 'POST':
        try:
            # Get or create client
            client_name = request.form['client_name']
            client_phone = request.form.get('client_phone', '')
            license_plate = request.form.get('license_plate', '')
            car_model = request.form.get('car_model', '')
            
            # Check if client exists
            client = Client.query.filter_by(name=client_name).first()
            if not client:
                client = Client(
                    name=client_name,
                    phone=client_phone
                )
                db.session.add(client)
                db.session.flush()  # Get the ID
            else:
                # Update client info if provided
                if client_phone:
                    client.phone = client_phone
                client.updated_at = datetime.utcnow()
            
            # Handle vehicle
            vehicle_id = request.form.get('vehicle_id')
            if not vehicle_id and (license_plate or car_model):
                # Create new vehicle if vehicle data is provided
                vehicle = Vehicle(
                    client_id=client.id,
                    license_plate=license_plate,
                    car_model=car_model
                )
                db.session.add(vehicle)
                db.session.flush()
                vehicle_id = vehicle.id
            
            # Create service order
            os_number = generate_os_number()
            service_order = ServiceOrder(
                os_number=os_number,
                professional_id=current_user.id,
                client_id=client.id,
                vehicle_id=int(vehicle_id) if vehicle_id else None,
                labor_total=float(request.form.get('labor_total', 0)),
                general_budget=float(request.form.get('general_budget', 0)),
                discount_type=request.form.get('discount_type', 'none'),
                discount_value=float(request.form.get('discount_value', 0)),
                surcharge_percentage=min(float(request.form.get('surcharge_percentage', 0)), 5.0),
                payment_method=request.form.get('payment_method', ''),
                status=request.form.get('status', 'Em andamento'),
                internal_observations=request.form.get('internal_observations', '')
            )
            
            db.session.add(service_order)
            db.session.flush()  # Get the ID
            
            # Add items
            item_names = request.form.getlist('item_name[]')
            item_quantities = request.form.getlist('item_quantity[]')
            item_prices = request.form.getlist('item_price[]')
            
            material_total = 0
            for i, name in enumerate(item_names):
                if name.strip():
                    quantity = float(item_quantities[i]) if item_quantities[i] else 1.0
                    unit_price = float(item_prices[i]) if item_prices[i] else 0.0
                    total_price = quantity * unit_price
                    material_total += total_price
                    
                    item = ServiceOrderItem(
                        service_order_id=service_order.id,
                        name=name,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                    db.session.add(item)
            
            # Update totals
            service_order.material_total = material_total
            service_order.final_total = calculate_totals(service_order)
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{os_number}_{file.filename}")
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):
                        os.makedirs(app.config['UPLOAD_FOLDER'])
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    service_order.image_filename = filename
            
            db.session.commit()
            flash(f'Ordem de Serviço {os_number} criada com sucesso!', 'success')
            return redirect(url_for('view_os', os_id=service_order.id) + '?created=1')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar OS: {str(e)}', 'danger')
    
    # Get clients and standard services for the form
    clients = Client.query.order_by(Client.name).all()
    standard_services = StandardService.query.filter_by(is_active=True).order_by(StandardService.name).all()
    
    return render_template('create_os.html', clients=clients, standard_services=standard_services)

@app.route('/os/<int:os_id>')
@login_required
def view_os(os_id):
    """View service order details"""
    service_order = ServiceOrder.query.get_or_404(os_id)
    company_info = CompanyInfo.get_instance()
    return render_template('edit_os.html', service_order=service_order, company_info=company_info, view_only=True)

@app.route('/edit_os/<int:os_id>', methods=['GET', 'POST'])
@login_required
def edit_os(os_id):
    """Edit existing service order"""
    service_order = ServiceOrder.query.get_or_404(os_id)
    
    if request.method == 'POST':
        try:
            # Update client info
            client = service_order.client
            client.name = request.form['client_name']
            client.phone = request.form.get('client_phone', '')
            client.license_plate = request.form.get('license_plate', '')
            client.car_model = request.form.get('car_model', '')
            client.updated_at = datetime.utcnow()
            
            # Update service order
            service_order.labor_total = float(request.form.get('labor_total', 0))
            service_order.general_budget = float(request.form.get('general_budget', 0))
            service_order.discount_type = request.form.get('discount_type', 'none')
            service_order.discount_value = float(request.form.get('discount_value', 0))
            service_order.surcharge_percentage = min(float(request.form.get('surcharge_percentage', 0)), 5.0)
            service_order.payment_method = request.form.get('payment_method', '')
            service_order.status = request.form.get('status', 'Em andamento')
            service_order.internal_observations = request.form.get('internal_observations', '')
            service_order.updated_at = datetime.utcnow()
            
            # Handle payment status
            if request.form.get('is_paid') == 'on':
                if not service_order.is_paid:
                    service_order.is_paid = True
                    service_order.payment_date = datetime.utcnow()
            else:
                service_order.is_paid = False
                service_order.payment_date = None
            
            # Clear existing items and add new ones
            ServiceOrderItem.query.filter_by(service_order_id=service_order.id).delete()
            
            item_names = request.form.getlist('item_name[]')
            item_quantities = request.form.getlist('item_quantity[]')
            item_prices = request.form.getlist('item_price[]')
            
            material_total = 0
            for i, name in enumerate(item_names):
                if name.strip():
                    quantity = float(item_quantities[i]) if item_quantities[i] else 1.0
                    unit_price = float(item_prices[i]) if item_prices[i] else 0.0
                    total_price = quantity * unit_price
                    material_total += total_price
                    
                    item = ServiceOrderItem(
                        service_order_id=service_order.id,
                        name=name,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                    db.session.add(item)
            
            # Update totals
            service_order.material_total = material_total
            service_order.final_total = calculate_totals(service_order)
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{service_order.os_number}_{file.filename}")
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):
                        os.makedirs(app.config['UPLOAD_FOLDER'])
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    service_order.image_filename = filename
            
            db.session.commit()
            flash('Ordem de Serviço atualizada com sucesso!', 'success')
            return redirect(url_for('view_os', os_id=service_order.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar OS: {str(e)}', 'danger')
    
    company_info = CompanyInfo.get_instance()
    clients = Client.query.order_by(Client.name).all()
    standard_services = StandardService.query.filter_by(is_active=True).order_by(StandardService.name).all()
    
    return render_template('edit_os.html', 
                         service_order=service_order, 
                         company_info=company_info,
                         clients=clients,
                         standard_services=standard_services,
                         view_only=False)

@app.route('/history')
@login_required
def history():
    """Service orders history with filters"""
    # Get filter parameters
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    payment_filter = request.args.get('payment', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query
    query = ServiceOrder.query.join(Client)
    
    if search:
        query = query.filter(
            db.or_(
                Client.name.ilike(f'%{search}%'),
                Client.license_plate.ilike(f'%{search}%'),
                ServiceOrder.os_number.ilike(f'%{search}%')
            )
        )
    
    if status_filter:
        query = query.filter(ServiceOrder.status == status_filter)
    
    if payment_filter == 'paid':
        query = query.filter(ServiceOrder.is_paid == True)
    elif payment_filter == 'unpaid':
        query = query.filter(ServiceOrder.is_paid == False)
    
    if date_from:
        query = query.filter(ServiceOrder.issue_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(ServiceOrder.issue_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    orders = query.order_by(ServiceOrder.created_at.desc()).all()
    
    return render_template('history.html', orders=orders)

@app.route('/reports')
@login_required
def reports():
    """Financial and operational reports"""
    # Get filter parameters
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    client_id = request.args.get('client_id', '')
    
    # Base query
    query = ServiceOrder.query
    
    if date_from:
        query = query.filter(ServiceOrder.issue_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(ServiceOrder.issue_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    if client_id:
        query = query.filter(ServiceOrder.client_id == client_id)
    
    orders = query.all()
    
    # Calculate statistics
    total_revenue = sum(order.final_total for order in orders if order.is_paid)
    pending_revenue = sum(order.final_total for order in orders if not order.is_paid)
    total_orders = len(orders)
    
    clients = Client.query.order_by(Client.name).all()
    
    return render_template('reports.html', 
                         orders=orders,
                         clients=clients,
                         total_revenue=total_revenue,
                         pending_revenue=pending_revenue,
                         total_orders=total_orders)

@app.route('/clients')
@login_required
def clients():
    """Client management"""
    clients = Client.query.order_by(Client.name).all()
    return render_template('clients.html', clients=clients)

@app.route('/services')
@login_required
def services():
    """Standard services management"""
    services = StandardService.query.order_by(StandardService.name).all()
    return render_template('services.html', services=services)

@app.route('/os/<int:os_id>/pdf')
@login_required
def generate_pdf(os_id):
    """Generate PDF for service order"""
    service_order = ServiceOrder.query.get_or_404(os_id)
    company_info = CompanyInfo.get_instance()
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        alignment=1  # Center
    )
    
    # Title
    elements.append(Paragraph(f"ORDEM DE SERVIÇO - {service_order.os_number}", title_style))
    elements.append(Spacer(1, 12))
    
    # Company info
    company_data = [
        ['Empresa:', company_info.name],
        ['Telefone:', company_info.phone],
        ['Endereço:', company_info.address],
        ['CNPJ:', company_info.cnpj],
    ]
    
    company_table = Table(company_data, colWidths=[1.5*inch, 4*inch])
    company_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(company_table)
    elements.append(Spacer(1, 12))
    
    # Client and order info
    vehicle_info = ''
    if service_order.vehicle:
        vehicle_info = f"{service_order.vehicle.license_plate} - {service_order.vehicle.car_model}"
    
    client_data = [
        ['Data:', service_order.issue_date.strftime('%d/%m/%Y')],
        ['Profissional:', service_order.professional.professional_name],
        ['Cliente:', service_order.client.name],
        ['Telefone:', service_order.client.phone or ''],
        ['Veículo:', vehicle_info],
    ]
    
    client_table = Table(client_data, colWidths=[1.5*inch, 4*inch])
    client_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 12))
    
    # Items
    if service_order.items:
        items_data = [['Item', 'Qtd', 'Valor Unit.', 'Total']]
        for item in service_order.items:
            items_data.append([
                item.name,
                str(item.quantity),
                f'R$ {item.unit_price:.2f}',
                f'R$ {item.total_price:.2f}'
            ])
        
        items_table = Table(items_data, colWidths=[3*inch, 0.8*inch, 1*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 12))
    
    # Totals
    totals_data = [
        ['Total Material:', f'R$ {service_order.material_total:.2f}'],
        ['Mão de Obra:', f'R$ {service_order.labor_total:.2f}'],
        ['Total Geral:', f'R$ {service_order.final_total:.2f}'],
    ]
    
    totals_table = Table(totals_data, colWidths=[2*inch, 2*inch])
    totals_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(totals_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'{service_order.os_number}.pdf',
        mimetype='application/pdf'
    )

@app.route('/export/csv')
@login_required
def export_csv():
    """Export service orders to CSV"""
    orders = ServiceOrder.query.join(Client).join(User).all()
    
    data = []
    for order in orders:
        data.append({
            'OS': order.os_number,
            'Data': order.issue_date.strftime('%d/%m/%Y'),
            'Cliente': order.client.name,
            'Telefone': order.client.phone,
            'Placa': order.client.license_plate,
            'Modelo': order.client.car_model,
            'Profissional': order.professional.professional_name,
            'Total Material': order.material_total,
            'Mão de Obra': order.labor_total,
            'Total Geral': order.final_total,
            'Status': order.status,
            'Pago': 'Sim' if order.is_paid else 'Não',
            'Forma Pagamento': order.payment_method,
        })
    
    df = pd.DataFrame(data)
    
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding='utf-8')
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'ordens_servico_{datetime.now().strftime("%Y%m%d")}.csv',
        mimetype='text/csv'
    )

@app.route('/import/csv', methods=['POST'])
@login_required
def import_csv():
    """Import service orders from CSV"""
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        df = pd.read_csv(file)
        imported_count = 0
        
        for _, row in df.iterrows():
            # Create or get client
            client = Client.query.filter_by(name=row['Cliente']).first()
            if not client:
                client = Client(
                    name=row['Cliente'],
                    phone=row.get('Telefone', ''),
                    license_plate=row.get('Placa', ''),
                    car_model=row.get('Modelo', '')
                )
                db.session.add(client)
                db.session.flush()
            
            # Create service order
            os_number = generate_os_number()
            service_order = ServiceOrder(
                os_number=os_number,
                professional_id=current_user.id,
                client_id=client.id,
                material_total=float(row.get('Total Material', 0)),
                labor_total=float(row.get('Mão de Obra', 0)),
                final_total=float(row.get('Total Geral', 0)),
                status=row.get('Status', 'Em andamento'),
                payment_method=row.get('Forma Pagamento', ''),
                is_paid=row.get('Pago', 'Não').lower() == 'sim'
            )
            db.session.add(service_order)
            imported_count += 1
        
        db.session.commit()
        flash(f'{imported_count} ordens de serviço importadas com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao importar arquivo: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

# API endpoints for AJAX calls
@app.route('/api/clients')
@login_required
def api_clients():
    """Get clients list for autocomplete"""
    search = request.args.get('q', '')
    clients = Client.query.filter(Client.name.ilike(f'%{search}%')).limit(10).all()
    return jsonify([{
        'id': client.id,
        'name': client.name,
        'phone': client.phone or '',
        'vehicles': [{
            'id': vehicle.id,
            'license_plate': vehicle.license_plate,
            'car_model': vehicle.car_model
        } for vehicle in client.vehicles]
    } for client in clients])

@app.route('/api/services')
@login_required
def api_services():
    """Get standard services for autocomplete"""
    search = request.args.get('q', '')
    services = StandardService.query.filter(
        StandardService.name.ilike(f'%{search}%'),
        StandardService.is_active == True
    ).limit(10).all()
    return jsonify([{
        'id': service.id,
        'name': service.name,
        'suggested_price': service.suggested_price
    } for service in services])

@app.route('/api/client_vehicles/<int:client_id>')
@login_required
def api_client_vehicles(client_id):
    """Get vehicles for a specific client"""
    vehicles = Vehicle.query.filter_by(client_id=client_id).all()
    
    return jsonify([{
        'id': vehicle.id,
        'license_plate': vehicle.license_plate,
        'car_model': vehicle.car_model,
        'year': vehicle.year,
        'color': vehicle.color
    } for vehicle in vehicles])

@app.route('/api/vehicles', methods=['POST'])
@login_required
def api_add_vehicle():
    """Add a new vehicle to a client"""
    data = request.get_json()
    
    try:
        vehicle = Vehicle(
            client_id=data['client_id'],
            license_plate=data['license_plate'],
            car_model=data.get('car_model', ''),
            year=data.get('year'),
            color=data.get('color', '')
        )
        db.session.add(vehicle)
        db.session.commit()
        
        return jsonify({
            'id': vehicle.id,
            'license_plate': vehicle.license_plate,
            'car_model': vehicle.car_model,
            'year': vehicle.year,
            'color': vehicle.color
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/settings')
@login_required
def settings():
    """Company settings page"""
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem acessar as configurações.', 'danger')
        return redirect(url_for('dashboard'))
    
    company_info = CompanyInfo.get_instance()
    return render_template('settings.html', company_info=company_info)

@app.route('/settings', methods=['POST'])
@login_required
def update_settings():
    """Update company settings"""
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem alterar as configurações.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        company_info = CompanyInfo.get_instance()
        
        company_info.name = request.form.get('company_name', company_info.name)
        company_info.phone = request.form.get('company_phone', company_info.phone)
        company_info.address = request.form.get('company_address', company_info.address)
        company_info.cnpj = request.form.get('company_cnpj', company_info.cnpj)
        
        # Handle logo upload
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename and allowed_file(logo_file.filename):
                filename = secure_filename(f"logo_{logo_file.filename}")
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                logo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                company_info.logo_filename = filename
        
        # Handle PIX QR code upload
        if 'pix_qr' in request.files:
            pix_file = request.files['pix_qr']
            if pix_file and pix_file.filename and allowed_file(pix_file.filename):
                filename = secure_filename(f"pix_{pix_file.filename}")
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                pix_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                company_info.pix_qr_filename = filename
        
        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar configurações: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/print_os/<int:os_id>')
@login_required
def print_os(os_id):
    """Print-friendly view of service order"""
    service_order = ServiceOrder.query.get_or_404(os_id)
    company_info = CompanyInfo.get_instance()
    return render_template('print_os.html', service_order=service_order, company_info=company_info)
