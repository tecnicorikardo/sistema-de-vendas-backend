from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.user import User
from src.models.product import Product
from src.models.category import Category

products_bp = Blueprint('products', __name__)

def require_admin():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user and user.role == 'admin'

@products_bp.route('/', methods=['GET'])
@jwt_required()
def get_products():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        category_id = request.args.get('category_id', type=int)
        
        query = Product.query
        
        if search:
            query = query.filter(Product.name.contains(search))
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        products = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'products': [product.to_dict() for product in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/', methods=['POST'])
@jwt_required()
def create_product():
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem criar produtos.'}), 403
        
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        price = data.get('price')
        stock = data.get('stock', 0)
        category_id = data.get('category_id')
        
        if not name or not price or not category_id:
            return jsonify({'error': 'Nome, preço e categoria são obrigatórios'}), 400
        
        # Verificar se a categoria existe
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'error': 'Categoria não encontrada'}), 404
        
        try:
            price = float(price)
            stock = int(stock)
        except ValueError:
            return jsonify({'error': 'Preço deve ser um número e estoque deve ser um inteiro'}), 400
        
        if price < 0 or stock < 0:
            return jsonify({'error': 'Preço e estoque devem ser valores positivos'}), 400
        
        product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify(product.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@products_bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem editar produtos.'}), 403
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            product.name = data['name']
        
        if 'description' in data:
            product.description = data['description']
        
        if 'price' in data:
            try:
                price = float(data['price'])
                if price < 0:
                    return jsonify({'error': 'Preço deve ser um valor positivo'}), 400
                product.price = price
            except ValueError:
                return jsonify({'error': 'Preço deve ser um número'}), 400
        
        if 'stock' in data:
            try:
                stock = int(data['stock'])
                if stock < 0:
                    return jsonify({'error': 'Estoque deve ser um valor positivo'}), 400
                product.stock = stock
            except ValueError:
                return jsonify({'error': 'Estoque deve ser um inteiro'}), 400
        
        if 'category_id' in data:
            category = Category.query.get(data['category_id'])
            if not category:
                return jsonify({'error': 'Categoria não encontrada'}), 404
            product.category_id = data['category_id']
        
        db.session.commit()
        return jsonify(product.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@products_bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem deletar produtos.'}), 403
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'message': 'Produto deletado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@products_bp.route('/<int:product_id>/stock', methods=['PUT'])
@jwt_required()
def update_stock(product_id):
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem atualizar estoque.'}), 403
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        data = request.get_json()
        new_stock = data.get('stock')
        
        if new_stock is None:
            return jsonify({'error': 'Novo valor de estoque é obrigatório'}), 400
        
        try:
            new_stock = int(new_stock)
            if new_stock < 0:
                return jsonify({'error': 'Estoque deve ser um valor positivo'}), 400
        except ValueError:
            return jsonify({'error': 'Estoque deve ser um inteiro'}), 400
        
        product.stock = new_stock
        db.session.commit()
        
        return jsonify(product.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

