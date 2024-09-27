from typing import cast
from unittest import TestCase
from uuid import UUID

from negotiator.negotiation.negotiation_repository import NegotiationRepository, NegotiationRecord
from tests.db_test_support import test_db_template


class TestNegotiationRepository(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.db = test_db_template()
        self.db.clear()

        self.repository = NegotiationRepository(self.db)

    def test_create(self):
        returned_id = self.repository.create()

        result = self.db.query_to_dict("select id from negotiations")

        self.assertIsNotNone(returned_id)
        self.assertEqual(
            [{'id': returned_id}],
            result
        )

    def test_find(self):
        negotiation_id = self.repository.create()

        result = self.repository.find(negotiation_id)

        self.assertIsNotNone(result)
        negotiation = cast(NegotiationRecord, result)
        self.assertEqual(negotiation_id, negotiation.id)

    def test_find__not_found(self):
        result = self.repository.find(UUID('768081d3-43d8-4280-bde0-5c4c187d3174'))

        self.assertIsNone(result)
