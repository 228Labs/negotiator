import json
import time
from uuid import uuid4

import openai
from freeplay import Freeplay, RecordPayload, CallInfo, ResponseInfo
from freeplay.model import OpenAIFunctionCall

from negotiator.negotiation.negotiation_service import NegotiationService, Negotiation, Message


class LLMService:
    def __init__(self, negotiation_service: NegotiationService, freeplay_client: Freeplay, freeplay_project_id: str):
        self.negotiation_service = negotiation_service
        self.freeplay_client = freeplay_client
        self.freeplay_project_id = freeplay_project_id

    def call_and_record_negotiator_chat_turn(self, negotiation: Negotiation, user_message: Message) -> str:
        # Retrieve prompt from Freeplay
        prompt = self.freeplay_client.prompts.get_formatted(
            self.freeplay_project_id,
            'negotiator',
            'latest',
            {},
            negotiation.with_message(user_message).messages_dict()
        )
        session = self.freeplay_client.sessions.restore_session(str(negotiation.id))
        trace = session.create_trace(user_message.content)

        # Make the call to OpenAI
        start_time = time.time()
        chat_completion = openai.ChatCompletion.create(
            model=prompt.prompt_info.model,
            messages=prompt.llm_prompt,
            **prompt.prompt_info.model_parameters
        )
        end_time = time.time()

        reply = chat_completion.choices[0].message.content

        reply_id = uuid4()
        self.negotiation_service.add_messages(negotiation.id, [
            user_message,
            Message(id=reply_id, role='assistant', content=reply),
        ])

        # Record call to Freeplay
        all_messages = prompt.all_messages({'role': 'assistant', 'content': reply})
        self.freeplay_client.recordings.create(
            RecordPayload(
                all_messages=all_messages,
                inputs={
                    'initial_assistant_message': negotiation.messages[0].content
                },
                session_info=session.session_info,
                prompt_info=prompt.prompt_info,
                call_info=CallInfo.from_prompt_info(prompt.prompt_info, start_time=start_time, end_time=end_time),
                response_info=ResponseInfo(),
                trace_info=trace
            )
        )
        if reply:
            trace.record_output(self.freeplay_project_id, reply)

        return reply
