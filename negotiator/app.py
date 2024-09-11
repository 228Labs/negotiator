import logging

import openai
import sqlalchemy
from flask import Flask
from freeplay import Freeplay

from negotiator.database_support.database_template import DatabaseTemplate
from negotiator.environment import Environment
from negotiator.health_api import health_api
from negotiator.index_page import index_page
from negotiator.negotiation.message_gateway import MessageGateway
from negotiator.negotiation.negotiation_gateway import NegotiationGateway
from negotiator.negotiation.negotiation_page import negotiation_page, LLMService
from negotiator.negotiation.negotiation_service import NegotiationService

logger = logging.getLogger(__name__)


def create_app(env: Environment = Environment.from_env()) -> Flask:
    app = Flask(__name__)
    app.secret_key = env.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = env.database_url
    openai.api_key = env.openai_api_key

    db = sqlalchemy.create_engine(env.database_url, pool_size=4)
    db_template = DatabaseTemplate(db)

    freeplay_client = Freeplay(env.freeplay_api_key, 'https://app.freeplay.ai/api')

    negotiation_gateway = NegotiationGateway(db_template)
    message_gateway = MessageGateway(db_template)
    negotiation_service = NegotiationService(db_template, negotiation_gateway, message_gateway)
    llm_service = LLMService(negotiation_service, freeplay_client, env.freeplay_project_id)
    app.register_blueprint(index_page())
    app.register_blueprint(negotiation_page(negotiation_service, llm_service))
    app.register_blueprint(health_api())

    return app
