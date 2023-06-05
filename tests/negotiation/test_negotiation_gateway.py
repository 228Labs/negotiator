from typing import cast
from unittest import TestCase
from uuid import UUID

from negotiator.database_support.result_mapping import map_one_result
from negotiator.negotiation.negotiation_gateway import NegotiationGateway, NegotiationRecord
from tests.db_test_support import test_db_template


class TestNegotiationGateway(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.db = test_db_template()
        self.db.clear()

        self.gateway = NegotiationGateway(self.db)

    def test_create(self):
        returned_id = self.gateway.create()

        result = self.db.query("select id from negotiations")

        self.assertIsNotNone(returned_id)
        stored_id = map_one_result(result, lambda row: row['id'])
        self.assertEqual(returned_id, stored_id)

    def test_find(self):
        negotiation_id = self.gateway.create()

        result = self.gateway.find(negotiation_id)

        self.assertIsNotNone(result)
        negotiation = cast(NegotiationRecord, result)
        self.assertEqual(negotiation_id, negotiation.id)

    def test_find__not_found(self):
        result = self.gateway.find(UUID('768081d3-43d8-4280-bde0-5c4c187d3174'))

        self.assertIsNone(result)
