from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import Connection

from negotiator.database_support.database_template import DatabaseTemplate
from negotiator.negotiation.message_gateway import MessageGateway
from negotiator.negotiation.negotiation_gateway import NegotiationGateway


@dataclass
class Message:
    id: UUID
    role: str
    content: str


@dataclass
class Negotiation:
    id: UUID
    messages: list[Message]

    def with_message(self, message: Message) -> 'Negotiation':
        return Negotiation(
            id=self.id,
            messages=[*self.messages, message]
        )

    def messages_dict(self) -> list[dict[str, str]]:
        return [
            {'role': m.role, 'content': m.content}
            for m in self.messages
            if m.role in ['user', 'assistant', 'system']
        ]


@dataclass
class NegotiationWithMessage:
    id: UUID
    message_count: int
    final_message: str


class NegotiationService:

    def __init__(
            self,
            db: DatabaseTemplate,
            negotiation_gateway: NegotiationGateway,
            message_gateway: MessageGateway,
    ) -> None:
        self.__db = db
        self.__negotiation_gateway = negotiation_gateway
        self.__message_gateway = message_gateway

    def create(self) -> Optional[UUID]:
        with self.__db.transaction() as connection:
            return self.__create_negotiation(connection)

    def find(self, negotiation_id: UUID) -> Optional[Negotiation]:
        with self.__db.transaction() as connection:
            negotiation = self.__negotiation_gateway.find(negotiation_id, connection)
            if negotiation is None:
                return None

            message_records = self.__message_gateway.list_for_negotiation(negotiation.id, connection)

            return Negotiation(
                id=negotiation.id,
                messages=[
                    Message(id=record.id, role=record.role, content=record.content)
                    for record in message_records
                ]
            )

    def add_messages(self, negotiation_id: UUID, messages: List[Message]) -> None:
        with self.__db.transaction() as connection:
            self.__create_messages(connection, negotiation_id, messages)

    def truncate(self, negotiation_id: UUID, at_message_id: UUID) -> None:
        self.__message_gateway.truncate_for_negotiation(
            negotiation_id=negotiation_id,
            at_message_id=at_message_id,
        )

    def __create_negotiation(self, connection: Connection) -> Optional[UUID]:
        assistant_message = 'Hi there. I see you\'re looking at this 2020 Toyota 4Runner. How can I help you?'

        negotiation_id = self.__negotiation_gateway.create(connection)
        if negotiation_id is None:
            connection.rollback()
            return None

        self.__message_gateway.create(negotiation_id, uuid4(), 'assistant', assistant_message, connection)

        return negotiation_id

    def __create_messages(self, connection: Connection, negotiation_id: UUID, messages: List[Message]) -> None:
        for message in messages:
            self.__message_gateway.create(
                negotiation_id=negotiation_id,
                id=message.id,
                role=message.role,
                content=message.content,
                connection=connection,
            )
