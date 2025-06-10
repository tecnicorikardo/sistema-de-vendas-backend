from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.user import User
from src.models.category import Category

categories_bp = Blueprint('categories', __name__)

def require_admin():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user and user.role == 'admin'

@categories_bp.route('/', methods=['GET'])
@jwt_required()
def get_categories():
    try:
        categories = Category.query.all()
        return jsonify([category.to_dict() for category in categories]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@categories_bp.route('/', methods=['POST'])
@jwt_required()
def create_category():
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem criar categorias.'}), 403
        
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Nome da categoria é obrigatório'}), 400
        
        # Verificar se a categoria já existe
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category:
            return jsonify({'error': 'Categoria já existe'}), 400
        
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        
        return jsonify(category.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@categories_bp.route('/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem editar categorias.'}), 403
        
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'error': 'Categoria não encontrada'}), 404
        
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Nome da categoria é obrigatório'}), 400
        
        # Verificar se o novo nome já existe
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category and existing_category.id != category_id:
            return jsonify({'error': 'Nome da categoria já existe'}), 400
        
        category.name = name
        db.session.commit()
        
        return jsonify(category.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@categories_bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem deletar categorias.'}), 403
        
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'error': 'Categoria não encontrada'}), 404
        
        # Verificar se há produtos associados à categoria
        if category.products:
            return jsonify({'error': 'Não é possível deletar categoria com produtos associados'}), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({'message': 'Categoria deletada com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

