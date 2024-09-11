from dataclasses import dataclass
from typing import cast
from uuid import UUID

from flask import Blueprint, render_template, redirect, request, jsonify
from flask.typing import ResponseReturnValue

from negotiator.negotiation.llm_service import LLMService
from negotiator.negotiation.negotiation_service import NegotiationService, Negotiation, Message
from negotiator.web_support import json_support


@dataclass
class MessageInfo:
    id: UUID
    role: str
    content: str


@dataclass
class NegotiationInfo:
    id: UUID
    messages: list[MessageInfo]





def negotiation_page(
        negotiation_service: NegotiationService,
        llm_service: LLMService,
) -> Blueprint:
    page = Blueprint('negotiation_page', __name__)

    @page.post('/negotiation')
    def create() -> ResponseReturnValue:
        negotiation_id = negotiation_service.create()
        return redirect(f'/negotiation/{negotiation_id}')

    @page.get('/negotiation/<negotiation_id>')
    def show(negotiation_id: UUID) -> ResponseReturnValue:
        negotiation = negotiation_service.find(negotiation_id)

        if negotiation is None:
            return redirect('/')

        return render_template(
            'negotiation.html',
            negotiation_json=json_support.encode(to_info(negotiation))
        )

    @page.post('/negotiation/<negotiation_id>/messages')
    def new_message(negotiation_id: UUID) -> ResponseReturnValue:
        negotiation = negotiation_service.find(negotiation_id)
        if negotiation is None:
            return redirect('/')

        request_body = cast(dict[str, str], request.get_json(silent=False))

        user_message = Message(
            id=UUID(request_body['id']),
            content=request_body['content'],
            role='user',
        )

        reply = llm_service.call_and_record_negotiator_chat_turn(negotiation, user_message)

        return jsonify({
            'id': reply,
            'role': 'assistant',
            'content': reply,
        }), 201

    @page.post('/negotiation/<negotiation_id>/messages/<message_id>/reset')
    def reset(negotiation_id: UUID, message_id: UUID) -> ResponseReturnValue:
        negotiation_service.truncate(negotiation_id=negotiation_id, at_message_id=message_id)

        return '', 204

    return page


def to_info(record: Negotiation) -> NegotiationInfo:
    return NegotiationInfo(
        id=record.id,
        messages=[
            MessageInfo(id=m.id, role=m.role, content=m.content)
            for m in record.messages
            if m.role != 'system'
        ]
    )
