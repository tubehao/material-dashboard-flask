from flask import Blueprint, request, jsonify, current_app, render_template
from neo4j import GraphDatabase
import re
import os
from werkzeug.utils import secure_filename
import csv

blueprint = Blueprint('table', __name__, url_prefix='/table')

@blueprint.route('/')
def index():
    return render_template('table.html')

@blueprint.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify(success=False, message="No file part")
    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, message="No selected file")
    if file and allowed_file(file.filename):
        print(file.filename)
        filename = secure_filename(file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        
        # 检查并创建上传目录
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        file_path = os.path.join(upload_folder, filename)
        print(file_path)
        file.save(file_path)
        print("saved")
        try:
            import_to_neo4j(file_path)
            return jsonify(success=True)
        except Exception as e:
            return jsonify(success=False, message=str(e))
    return jsonify(success=False, message="File not allowed")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

def import_to_neo4j(file_path):
    driver = current_app.config['NEO4J_DRIVER']
    with driver.session() as session:
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                pass
                # Example query to create nodes and relationships
                # query = """
                # CREATE (n:Node {name: $name})
                # """
                # session.run(query, name=row[0])
