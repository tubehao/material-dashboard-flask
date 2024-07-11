# chat/routes.py

from flask import Blueprint, request, jsonify, current_app, render_template
from neo4j import GraphDatabase
import re

blueprint = Blueprint('chat', __name__, url_prefix='/chat')

@blueprint.route('/')
def index():
    return render_template('chat.html')

@blueprint.route('/get_response', methods=['POST'])
def get_response():
    data = request.get_json()
    user_message = data['message']
    
    # 使用初始化后的模型
    pipeline_prompt = current_app.config['MODEL_PIPELINE']
    pipeline_chat = current_app.config['MODEL_SOLUTION']
    
    # 构建提示以生成Cypher查询语句
    prompt = f"Translate the following natural language query into a Cypher query for Neo4j and wrap the query with '```' \n Our dataset contains a knowledge graph stored in a Neo4j database. With node including rdfs__label, rdfs__comment, <elementId>, <id> and uri.\n for example, if the natural language query is 'Introduce Godzilla to me', the Cypher query should be like '```MATCH (n) WHERE n.rdfs__label CONTAINS \"Godzilla\" MATCH (n)-[r]-(neighbor) RETURN n, r, neighbor```'.\nNatural Language Query: {user_message}\n\n\n\nCypher Query:"
    
    # 调用模型生成输出
    output = pipeline_prompt(prompt, max_new_tokens=100)
    generated_text = output[0]['generated_text'].strip()
    
    # 使用正则表达式提取用```包裹的Cypher查询
    match = re.search(r'```(.*?)```', generated_text[len(prompt):], re.DOTALL)
    if match:
        cypher_query = match.group(1).strip()
        print("~~~~~~~~~~~~~~~~~~~~~")
        print(cypher_query)
    else:
        cypher_query = "MATCH (n) RETURN n LIMIT 1"  # 默认查询语句，如果没有匹配到

    # 使用生成的Cypher查询语句在Neo4j中查询
    driver = current_app.config['NEO4J_DRIVER']
    with driver.session() as session:
        result = session.run(cypher_query)
        query_results = [record.data() for record in result]
    important_results = []
    for record in query_results:
        important_record = {key: value for key, value in record.items() if key in ['n', 'neighbor']}
        important_results.append(important_record)
        if len(str(important_results)) > 1000:  # 根据需要调整最大长度
            break
    
    # 构建提示以让LLM解决问题
    result_prompt = f"Based on the following knowledge, provide anwser for {user_message}. You can refer to the Query result, but don't use it directly. \n\nQuery Results: {important_results}\n\n Answer:"
    final_output = pipeline_chat(result_prompt, max_new_tokens=200)
    solution = final_output[0]['generated_text'].strip()
    
    # 返回解决方案
    print("~~~~~~~~~~~~~~~~~~~~~")
    print(solution[len(result_prompt):])
    return jsonify(solution[len(result_prompt):])
