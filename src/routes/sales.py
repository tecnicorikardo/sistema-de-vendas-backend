from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.user import User
from src.models.sale import Sale, SaleItem
from src.models.product import Product
from datetime import datetime, timedelta
from sqlalchemy import func

sales_bp = Blueprint('sales', __name__)

def require_admin():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user and user.role == 'admin'

@sales_bp.route('/', methods=['GET'])
@jwt_required()
def get_sales():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Sale.query
        
        # Se não for admin, mostrar apenas as próprias vendas
        if current_user.role != 'admin':
            query = query.filter(Sale.user_id == current_user_id)
        
        # Filtros de data
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
                query = query.filter(Sale.timestamp >= start_date)
            except ValueError:
                return jsonify({'error': 'Formato de data inválido para start_date'}), 400
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
                query = query.filter(Sale.timestamp <= end_date)
            except ValueError:
                return jsonify({'error': 'Formato de data inválido para end_date'}), 400
        
        sales = query.order_by(Sale.timestamp.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'sales': [sale.to_dict() for sale in sales.items],
            'total': sales.total,
            'pages': sales.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sales_bp.route('/', methods=['POST'])
@jwt_required()
def create_sale():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        items = data.get('items', [])
        
        if not items:
            return jsonify({'error': 'Lista de itens é obrigatória'}), 400
        
        total_amount = 0
        sale_items = []
        
        # Validar itens e calcular total
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity')
            
            if not product_id or not quantity:
                return jsonify({'error': 'product_id e quantity são obrigatórios para cada item'}), 400
            
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    return jsonify({'error': 'Quantidade deve ser maior que zero'}), 400
            except ValueError:
                return jsonify({'error': 'Quantidade deve ser um inteiro'}), 400
            
            product = Product.query.get(product_id)
            if not product:
                return jsonify({'error': f'Produto com ID {product_id} não encontrado'}), 404
            
            if product.stock < quantity:
                return jsonify({'error': f'Estoque insuficiente para o produto {product.name}. Disponível: {product.stock}'}), 400
            
            subtotal = float(product.price) * quantity
            total_amount += subtotal
            
            sale_items.append({
                'product': product,
                'quantity': quantity,
                'price_at_sale': product.price
            })
        
        # Criar a venda
        sale = Sale(
            user_id=current_user_id,
            total_amount=total_amount
        )
        
        db.session.add(sale)
        db.session.flush()  # Para obter o ID da venda
        
        # Criar itens da venda e atualizar estoque
        for item_data in sale_items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_data['product'].id,
                quantity=item_data['quantity'],
                price_at_sale=item_data['price_at_sale']
            )
            
            # Atualizar estoque
            item_data['product'].stock -= item_data['quantity']
            
            db.session.add(sale_item)
        
        db.session.commit()
        
        return jsonify(sale.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@sales_bp.route('/reports/summary', methods=['GET'])
@jwt_required()
def get_sales_summary():
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar relatórios.'}), 403
        
        # Vendas de hoje
        today = datetime.now().date()
        today_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.timestamp) == today
        ).scalar() or 0
        
        # Vendas do mês
        start_of_month = today.replace(day=1)
        month_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            Sale.timestamp >= start_of_month
        ).scalar() or 0
        
        # Total de vendas
        total_sales = db.session.query(func.sum(Sale.total_amount)).scalar() or 0
        
        # Número de vendas hoje
        today_count = Sale.query.filter(func.date(Sale.timestamp) == today).count()
        
        # Produtos mais vendidos (últimos 30 dias)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        top_products = db.session.query(
            Product.name,
            func.sum(SaleItem.quantity).label('total_sold')
        ).join(SaleItem).join(Sale).filter(
            Sale.timestamp >= thirty_days_ago
        ).group_by(Product.id, Product.name).order_by(
            func.sum(SaleItem.quantity).desc()
        ).limit(5).all()
        
        return jsonify({
            'today_sales': float(today_sales),
            'month_sales': float(month_sales),
            'total_sales': float(total_sales),
            'today_count': today_count,
            'top_products': [
                {'name': product.name, 'total_sold': int(product.total_sold)}
                for product in top_products
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sales_bp.route('/<int:sale_id>', methods=['GET'])
@jwt_required()
def get_sale(sale_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        sale = Sale.query.get(sale_id)
        if not sale:
            return jsonify({'error': 'Venda não encontrada'}), 404
        
        # Se não for admin, só pode ver as próprias vendas
        if current_user.role != 'admin' and sale.user_id != current_user_id:
            return jsonify({'error': 'Acesso negado'}), 403
        
        return jsonify(sale.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

