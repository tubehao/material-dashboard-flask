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
    pipeline_pure = current_app.config['MODEL_PURE']
    
    # 构建提示以生成Cypher查询语句
    prompt = f"Our dataset contains a knowledge graph stored in a Neo4j database. With node including  rdfs__comment, rdfs__label, <elementId>, <id> and uri. Translate the following natural language query into a Cypher query for Neo4j and wrap the query with '```' \n \n for example, if the natural language query is 'Introduce basketball', the Cypher query should be like '```MATCH (n)-[r]-(neighbor) WHERE n.rdfs__comment CONTAINS 'basketball' OR n.rdfs__label CONTAINS 'basketball' RETURN n, r, neighbor LIMIT 25```'.\nNatural Language Query: {user_message}\n\n\n\nCypher Query:"
    
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
        knowledge_list = []
        # 处理查询结果
        query_results = [record.data() for record in result]
        for record in query_results:
            knowledge = {}
            for key, record in record.items():
                if type(record) == dict:# process the node
                    knowledge[key] = {"comment": str(record.get('rdfs__comment')), "label": str(record.get('rdfs__label'))}
                elif type(record) == tuple:# process the relationship
                    for item in record:
                        if type(item) == dict:
                            if key in knowledge:
                                knowledge[key]['comment'] += ' '+str(item.get('rdfs__comment'))
                                knowledge[key]['label'] += ' '+str(item.get('rdfs__label'))
                            else:
                                knowledge[key] = {"comment": str(item.get('rdfs__comment')), "label": str(item.get('rdfs__label'))}
                        else :
                            if key in knowledge:
                                knowledge[key]['comment'] +=' '+ str(item)
                            else:
                                knowledge[key] = {"comment": str(item), "label": ""}
            knowledge_list.append(knowledge)
    important_results = knowledge_list[:3]
    
    
    # 构建提示以让LLM解决问题
    print(important_results)
    # result_prompt = f"Knowledge: {important_results}\n\n Use the knowledge to answer the following question.  Don't contain the query result in your answer directly, you can just use it to help you. \n\n Question:{user_message}.\nAnswer:"
    result_prompt = f"Knowledge: {important_results}. Use the knowledge to address the following question. Don't contain it in your answer directly, you can just refer to it. \n\n Question: {user_message}. \n Answer:"
    # result_prompt = f"The following knowledge is retrieved from yago and contains the related node and edge, n represents the related concept while r and neighbor represents its neighbor. Knowledge: {important_results}. Use the knowledge to address the following question. Don't contain it in your answer directly, you can just refer to it. \n\n Question: {user_message}. \n Answer:"


    final_output = pipeline_chat(result_prompt, max_new_tokens=200)
    solution = final_output[0]['generated_text'].strip()

    pure_prompt = f"Address the following question. \n\n Question:{user_message}.Answer:"
    pure_output = pipeline_pure(pure_prompt, max_new_tokens=200)
    pure_solution = pure_output[0]['generated_text'].strip()
    
    # 返回解决方案
    print("~~~~~~~~~~~~~~~~~~~~~")
    print(solution[len(result_prompt):])
    return jsonify({
            "solution_part1": solution[len(result_prompt):],  # 第一部分
            "solution_part2": pure_solution[len(pure_prompt):]   # 第二部分
        })
