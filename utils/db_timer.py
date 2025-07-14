# db/query_timer.py
import time
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine
import logging

logger = logging.getLogger("query_timer")
logger.setLevel(logging.INFO)

def attach_query_timer(engine: AsyncEngine):
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info["query_start_time"] = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.perf_counter() - conn.info["query_start_time"]
        logger.info(f"[DB] Query time: {total:.4f}s | SQL: {statement.strip()}")
