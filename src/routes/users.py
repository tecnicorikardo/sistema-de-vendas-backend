from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.database import db
from src.models.user import User

users_bp = Blueprint('users', __name__)

def require_admin():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user and user.role == 'admin'

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.'}), 403
        
        users = User.query.all()
        return jsonify([user.to_dict() for user in users]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/', methods=['POST'])
@jwt_required()
def create_user():
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem criar usuários.'}), 403
        
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'funcionario')
        
        if not username or not password:
            return jsonify({'error': 'Username e password são obrigatórios'}), 400
        
        if role not in ['admin', 'funcionario']:
            return jsonify({'error': 'Role deve ser admin ou funcionario'}), 400
        
        # Verificar se o usuário já existe
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'error': 'Usuário já existe'}), 400
        
        user = User(username=username, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem editar usuários.'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        if 'username' in data:
            # Verificar se o novo username já existe
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Username já existe'}), 400
            user.username = data['username']
        
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        if 'role' in data:
            if data['role'] not in ['admin', 'funcionario']:
                return jsonify({'error': 'Role deve ser admin ou funcionario'}), 400
            user.role = data['role']
        
        db.session.commit()
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        if not require_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem deletar usuários.'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Não permitir deletar o próprio usuário
        current_user_id = get_jwt_identity()
        if user_id == current_user_id:
            return jsonify({'error': 'Não é possível deletar o próprio usuário'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'Usuário deletado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

