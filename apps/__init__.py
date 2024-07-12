# __init__.py

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
import transformers
import os
from neo4j import GraphDatabase

db = SQLAlchemy()
login_manager = LoginManager()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('authentication', 'home', 'chat'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def configure_database(app):
    @app.before_first_request
    def initialize_database():
        try:
            db.create_all()
        except Exception as e:
            print('> Error: DBMS Exception: ' + str(e) )
            # fallback to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
            print('> Fallback to SQLite ')
            db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

def initialize_model(app):
    model_id = "meta-llama/Meta-Llama-3-8B"
    app.config['MODEL_PIPELINE'] = transformers.pipeline(
        "text-generation",
        model=model_id,
        tokenizer=model_id,
        device=0  # 如果没有GPU，设置为-1
    )
    app.config['MODEL_SOLUTION'] = transformers.pipeline(
        "text-generation",
        model=model_id,
        tokenizer=model_id,
        device=2  # 如果没有GPU，设置为-1
    )
    app.config['MODEL_PURE'] = transformers.pipeline(
        "text-generation",
        model=model_id,
        tokenizer=model_id,
        device=1  # 如果没有GPU，设置为-1
    )

def initialize_neo4j(app):
    uri = "bolt://localhost:7687"  # 根据需要替换为您的实际地址
    username = "neo4j"
    password = "neo4j/pwd"
    app.config['NEO4J_DRIVER'] = GraphDatabase.driver(uri, auth=(username, password))

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    initialize_model(app)
    initialize_neo4j(app)
    return app
