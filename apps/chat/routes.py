# chat/routes.py

from flask import Blueprint, request, jsonify, render_template

blueprint = Blueprint('chat', __name__, url_prefix='/chat')

@blueprint.route('/')
def index():
    return render_template('home/chat.html')

@blueprint.route('/get_response', methods=['POST'])
def get_response():
    data = request.get_json()
    user_message = data['message']
    # 这里可以添加实际的处理逻辑，比如调用聊天机器人API或其他处理
    bot_response = f"你说的是: {user_message}"  # 示例响应
    return jsonify(bot_response)
