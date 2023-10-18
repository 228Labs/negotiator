from dataclasses import dataclass
from typing import Optional, List, Tuple
from uuid import UUID, uuid4

from sqlalchemy import Connection

from negotiator.database_support.database_template import DatabaseTemplate
from negotiator.negotiation.message_gateway import MessageGateway, MessageRecord
from negotiator.negotiation.negotiation_gateway import NegotiationGateway, NegotiationRecord


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


@dataclass
class NegotiationOutcome:
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
            negotiation_record, message_records = self.__find_negotiation(connection, negotiation_id)
            if negotiation_record is None:
                return None

            return Negotiation(
                id=negotiation_record.id,
                messages=[
                    Message(id=record.id, role=record.role, content=record.content)
                    for record in message_records
                ]
            )

    def find_all_negotiations_with_outcome(self) -> List[NegotiationOutcome]:
        # TODO: Implement method to retrieve page data
        with self.__db.transaction() as connection:
            all_negotiations = self.__negotiation_gateway.find_all(connection)
            negotation_outcomes = []
            for negotiation in all_negotiations:
                messages = self.__message_gateway.list_for_negotiation(negotiation.id, connection)
                negotation_outcomes.append(
                    NegotiationOutcome(
                        negotiation.id,
                        message_count=len(messages),
                        final_message=messages[-1].content
                    )
                )
            return negotation_outcomes

    def add_messages(self, negotiation_id: UUID, messages: List[Message]) -> None:
        with self.__db.transaction() as connection:
            self.__create_messages(connection, negotiation_id, messages)

    def truncate(self, negotiation_id: UUID, at_message_id: UUID) -> None:
        self.__message_gateway.truncate_for_negotiation(
            negotiation_id=negotiation_id,
            at_message_id=at_message_id,
        )

    def __create_negotiation(self, connection: Connection) -> Optional[UUID]:
        system_message = """
            You are a used car salesman talking to someone who is hoping to buy one of the cars that you have in
            stock, a 2020 Toyota 4Runner. You paid $20,000 for the truck, and would like to get at least $22,000 for
            it. The list price is $30,000. Negotiate with the potential buyer to get the best price.
        
            Don't tell the buyer what you purchased the truck for, or your minimum selling price. Your financial
            bonus is based on getting the highest possible price for the truck.
        
            Don't talk to the buyer about any other vehicles you have available, try to make a deal on this one.
        
            You'd like to make the deal today, so if the buyer says that they need time to think try to pressure
            or incentivize them into making the deal now.
        """
        assistant_message = 'Hi there. I see you\'re looking at this 2020 Toyota 4Runner. How can I help you?'

        negotiation_id = self.__negotiation_gateway.create(connection)
        if negotiation_id is None:
            connection.rollback()
            return None

        self.__message_gateway.create(negotiation_id, uuid4(), 'system', system_message, connection)
        self.__message_gateway.create(negotiation_id, uuid4(), 'assistant', assistant_message, connection)

        return negotiation_id

    def __find_negotiation(
            self,
            connection: Connection,
            negotiation_id: UUID,
    ) -> Tuple[Optional[NegotiationRecord], List[MessageRecord]]:
        negotiation = self.__negotiation_gateway.find(negotiation_id, connection)
        if negotiation is None:
            return None, []

        messages = self.__message_gateway.list_for_negotiation(negotiation.id, connection)

        return negotiation, messages

    def __create_messages(self, connection: Connection, negotiation_id: UUID, messages: List[Message]) -> None:
        for message in messages:
            self.__message_gateway.create(
                negotiation_id=negotiation_id,
                id=message.id,
                role=message.role,
                content=message.content,
                connection=connection,
            )
