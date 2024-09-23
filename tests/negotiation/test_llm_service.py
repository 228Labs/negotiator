import json
import uuid
from unittest import TestCase, mock
from unittest.mock import MagicMock

from freeplay.resources.prompts import FormattedPrompt, PromptInfo
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function
from openai.types.completion_usage import CompletionTokensDetails

from negotiator.negotiation.llm_service import LLMService, RESOLVE_NEGOTIATION_TOOL_NAME
from negotiator.negotiation.message_repository import MessageRepository
from negotiator.negotiation.negotiation_repository import NegotiationRepository
from negotiator.negotiation.negotiation_service import NegotiationService, Message
from tests.db_test_support import test_db_template


class TestNegotiationPage(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.db = test_db_template()
        self.db.clear()

        negotiation_repository = NegotiationRepository(self.db)
        message_repository = MessageRepository(self.db)

        self.negotiation_service = NegotiationService(self.db, negotiation_repository, message_repository)
        self.project_id = str(uuid.uuid4())
        self.freeplay_mock = mock.Mock()
        self.freeplay_mock.prompts.get_formatted.return_value = FormattedPrompt(
            prompt_info=PromptInfo(
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                'template',
                'latest',
                model_parameters={},
                provider_info=None,
                provider='openai',
                model='gpt-4o',
                flavor_name='openai_chat',
                project_id=str(uuid.uuid4())
            ),
            messages=[],
            formatted_prompt=[],
            formatted_prompt_text=None
        )
        freeplay_project_id = uuid.uuid4()
        self.mock_call_llm = MagicMock()
        self.llm_service = LLMService(
            self.negotiation_service, self.freeplay_mock, self.mock_call_llm, freeplay_project_id)

    def test_openai_response(self):
        # Create a simple dictionary that mimics the OpenAI response
        self.mock_call_llm.return_value = self.mock_openai_response_message('Assistant response')
        negotiation_id = self.negotiation_service.create()
        negotiation = self.negotiation_service.find(negotiation_id)
        self.assertEqual(1, len(negotiation.messages))

        # Test logic
        new_message = Message(
            id=uuid.uuid4(),
            role='user',
            content='A new message!'
        )

        self.llm_service.call_and_record_negotiator_chat_turn(negotiation, new_message)

        # Assertion
        updated_negotiation = self.negotiation_service.find(negotiation_id)
        self.assertEqual(3, len(updated_negotiation.messages))
        self.assertEqual('A new message!', updated_negotiation.messages[1].content)
        self.assertEqual('Assistant response', updated_negotiation.messages[2].content)

    def test_resolve_negotiation(self):
        # Create a simple dictionary that mimics the OpenAI response
        self.mock_call_llm.return_value = self.mock_openai_tool_call(15_000)
        negotiation_id = self.negotiation_service.create()
        negotiation = self.negotiation_service.find(negotiation_id)
        self.assertEqual(1, len(negotiation.messages))

        # Test logic
        new_message = Message(
            id=uuid.uuid4(),
            role='user',
            content='Final user message'
        )

        self.llm_service.call_and_record_negotiator_chat_turn(negotiation, new_message)

        # Assertion
        updated_negotiation = self.negotiation_service.find(negotiation_id)
        self.assertEqual(2, len(updated_negotiation.messages))
        self.assertEqual('Final user message', updated_negotiation.messages[1].content)

    def mock_openai_tool_call(self, final_price: int):
        return ChatCompletion(
            id='chatcmpl-AAVY5zYwj6TXgZwqAwDno6EpuGfzy',
            choices=[
                Choice(
                    finish_reason='stop',
                    index=0,
                    logprobs=None,
                    message=ChatCompletionMessage(
                        content=None,
                        refusal=None,
                        role='assistant',
                        function_call=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="call_" + str(uuid.uuid4()),
                                type="function",
                                function=Function(
                                    name=RESOLVE_NEGOTIATION_TOOL_NAME,
                                    arguments=json.dumps({'final_price': final_price})
                                )
                            )
                        ])
                )
            ],
            created=1727067917,
            model='gpt-4o-2024-08-06',
            object='chat.completion',
            service_tier=None,
            system_fingerprint='fp_5050236cbd',
            usage=CompletionUsage(
                completion_tokens=40,
                prompt_tokens=421,
                total_tokens=461,
                completion_tokens_details=CompletionTokensDetails(reasoning_tokens=0)
            )
        )

    def mock_openai_response_message(self, message_content: str):
        return ChatCompletion(
            id='chatcmpl-AAVY5zYwj6TXgZwqAwDno6EpuGfzy',
            choices=[
                Choice(
                    finish_reason='stop',
                    index=0,
                    logprobs=None,
                    message=ChatCompletionMessage(
                        content=message_content,
                        refusal=None,
                        role='assistant',
                        function_call=None,
                        tool_calls=None)
                )
            ],
            created=1727067917,
            model='gpt-4o-2024-08-06',
            object='chat.completion',
            service_tier=None,
            system_fingerprint='fp_5050236cbd',
            usage=CompletionUsage(
                completion_tokens=40,
                prompt_tokens=421,
                total_tokens=461,
                completion_tokens_details=CompletionTokensDetails(reasoning_tokens=0)
            )
        )
