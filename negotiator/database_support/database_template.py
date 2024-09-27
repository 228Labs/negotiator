from contextlib import contextmanager
from typing import Optional, Any, TypeVar

import sqlalchemy
from sqlalchemy import Engine, Connection, CursorResult

T = TypeVar('T')


class DatabaseTemplate:
    def __init__(self, engine: Engine) -> None:
        self.__engine = engine

    @contextmanager
    def transaction(self):
        with self.__engine.begin() as connection:
            yield connection

    def query(self, statement: str, connection: Optional[Connection] = None, **kwargs: Any) -> CursorResult:
        if connection is None:
            with self.transaction() as connection:
                return connection.execute(sqlalchemy.text(statement), kwargs)
        else:
            return connection.execute(sqlalchemy.text(statement), kwargs)
