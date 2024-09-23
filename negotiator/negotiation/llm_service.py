import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from freeplay import Freeplay, RecordPayload, CallInfo, ResponseInfo
from freeplay.model import OpenAIFunctionCall
from freeplay.resources.prompts import FormattedPrompt
from freeplay.resources.sessions import Session, TraceInfo

from negotiator.negotiation.negotiation_service import NegotiationService, Negotiation, Message

RESOLVE_NEGOTIATION_TOOL_NAME = "resolve_negotiation"
resolve_negotiation_tool_spec = {
    "type": "function",
    "function": {
        "name": RESOLVE_NEGOTIATION_TOOL_NAME,
        "description": "Resolve the negotiation with a final negotiated price from the user. Only use this tool if you "
                       "have mutually agreed to a price with the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "final_price": {
                    "type": "number",
                    "description": "The user's final agreed upon price.",
                },
            },
            "required": ["final_price"],
            "additionalProperties": False,
        },
    },
}

freeplay_prompt_name = 'negotiator'
freeplay_environment = 'latest'


@dataclass
class ResolvedNegotiation:
    final_price: int
    leaderboard_rank: int


class LLMService:
    def __init__(
            self,
            negotiation_service: NegotiationService,
            freeplay_client: Freeplay,
            call_llm: Any,
            freeplay_project_id: str
    ):
        self.negotiation_service = negotiation_service
        self.freeplay_client = freeplay_client
        self.call_llm = call_llm
        self.freeplay_project_id = freeplay_project_id

    def call_and_record_negotiator_chat_turn(self, negotiation: Negotiation, user_message: Message) -> str | ResolvedNegotiation:
        # Retrieve prompt from Freeplay
        prompt = self.freeplay_client.prompts.get_formatted(
            self.freeplay_project_id,
            freeplay_prompt_name,
            freeplay_environment,
            {},
            negotiation.with_message(user_message).messages_dict()
        )
        session = self.freeplay_client.sessions.restore_session(str(negotiation.id))
        trace = session.create_trace(user_message.content)

        # Make the call to OpenAI
        start_time = time.time()
        chat_completion = self.call_llm(
            model=prompt.prompt_info.model,
            messages=prompt.llm_prompt,
            tools=[resolve_negotiation_tool_spec],
            **prompt.prompt_info.model_parameters
        )
        end_time = time.time()

        llm_message = chat_completion.choices[0].message

        if llm_message.tool_calls and llm_message.tool_calls[0].function.name == RESOLVE_NEGOTIATION_TOOL_NAME:
            arguments = llm_message.tool_calls[0].function.arguments
            self.__log_message_to_freeplay(
                negotiation,
                prompt,
                arguments,
                session,
                trace,
                start_time,
                end_time,
                ResponseInfo(
                    function_call_response=OpenAIFunctionCall(
                        {'name': RESOLVE_NEGOTIATION_TOOL_NAME, 'arguments': arguments}))
            )
            tool_args = json.loads(arguments)
            self.negotiation_service.add_messages(negotiation.id, [
                user_message
            ])
            return self.resolve_negotiation(negotiation, **tool_args)

        # Add message to Negotiation in the database
        reply = llm_message.content
        reply_id = uuid4()
        self.negotiation_service.add_messages(negotiation.id, [
            user_message,
            Message(id=reply_id, role='assistant', content=reply),
        ])

        self.__log_message_to_freeplay(
            negotiation, prompt, reply, session, trace, start_time, end_time, ResponseInfo()
        )

        return reply

    def resolve_negotiation(self, negotiation: Negotiation, final_price: int) -> ResolvedNegotiation:
        # TODO: Make your changes here!
        return ResolvedNegotiation(
            final_price,
            leaderboard_rank=0
        )

    def __log_message_to_freeplay(
            self,
            negotiation: Negotiation,
            prompt: FormattedPrompt,
            reply: str,
            session: Session,
            trace: TraceInfo,
            start_time: float,
            end_time: float,
            response_info: ResponseInfo
    ) -> None:
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
                response_info=response_info,
                trace_info=trace
            )
        )
        trace.record_output(self.freeplay_project_id, reply)
