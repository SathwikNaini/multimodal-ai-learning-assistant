from flask import Blueprint, jsonify

health_router = Blueprint('health', __name__)


@health_router.route('/health', methods=['GET'])
def health_check():
    return jsonify({'success': True, 'data': {'status': 'Backend running'}, 'error': None})
