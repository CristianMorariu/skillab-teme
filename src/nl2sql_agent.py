"""
NL2SQL Agent - TODO: Implementează nodurile
"""

import json
import logging
import re
from pathlib import Path
from typing import Literal

import pandas as pd
import sqlparse
from langgraph.graph import END, StateGraph
from skillab import get_llm
from skillab.llm.base import LLMProvider
from skillab.prompts import PromptRegistry
from sqlalchemy import text
from state import NL2SQLState

from database import transaction

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class NL2SQLAgent:
    """
    Flow:
        get_context → generate_sql → validate → execute
                                        ↓
                                    handle_error
    """

    def __init__(
        self,
        table_name: str,
        schema_path: str,
        db_url: str = "postgresql://demo:demo123@localhost:5433/rag_demo",
        max_retries: int = 2,
        llm: LLMProvider | None = None,
    ):
        self.table_name = table_name
        self.db_url = db_url
        self.max_retries = max_retries
        self.llm = llm or get_llm()
        self.prompts = PromptRegistry(str(PROMPTS_DIR))

        # Load schema
        self.schema = json.loads(Path(schema_path).read_text())

        self.graph = self._build_graph()

    # === NODES ===

    def node_get_context(self, state: NL2SQLState) -> dict:
        """COMPLET."""
        return {
            "schema_context": self.schema,
            "table_name": self.table_name,
        }

    def node_generate_sql(self, state: NL2SQLState) -> dict:

        logger.info(f"[GENERATE] {state.question}")

        prompt = self.prompts.render(
            "nl2sql_generate",
            table_name=self.table_name,
            table_description=state.schema_context.get("description", ""),
            columns=state.schema_context.get("columns", {}),
            business_rules={},
            question=state.question,
        )

        response = self.llm.generate_sync([{"role": "user", "content": prompt}])
        sql = re.sub(r"```sql\s*", "", response)
        sql = re.sub(r"```\s*", "", sql).strip()

        return {"sql_query": sql}

    def node_validate_sql(self, state: NL2SQLState) -> dict:

        sql = state.sql_query
        logger.info(f"[VALIDATE] {sql[:50]}...")

        forbidden = ["drop", "delete", "insert", "update", "truncate", "--"]
        if any(kw in sql.lower() for kw in forbidden):
            return {
                "is_valid": False,
                "validation_error": f"SQL contine operatii interzise",
            }

        statements = sqlparse.parse(sql)
        if not statements or statements[0].get_type() != "SELECT":
            return {"is_valid": False, "validation_error": "Doar SELECT este permis."}

        return {"is_valid": True, "validation_error": ""}

    def node_execute_sql(self, state: NL2SQLState) -> dict:

        logger.info("[EXECUTE]")

        try:
            with transaction() as session:
                result = session.execute(text(state.sql_query))
                df = pd.DataFrame(result.mappings().all())
            return {"result": df, "status": "success", "execution_error": ""}
        except Exception as e:
            return {"execution_error": str(e), "status": "failed"}

    def node_handle_error(self, state: NL2SQLState) -> dict:
        """
        TODO: Handle error + retry.

        1. Increment retry_count
        2. Dacă >= max_retries: return {"status": "failed"}
        3. Renderează prompt "nl2sql_error"
        4. Apelează LLM pentru SQL corectat
        5. Return {"sql_query": new_sql, "retry_count": ...}
        """
        logger.info("[ERROR]")

        new_retry = state.retry_count + 1
        if new_retry >= state.max_retries:
            return {"status": "failed", "retry_count": new_retry}

        error_msg = state.execution_error or state.validation_error
        prompt = self.prompts.render(
            "nl2sql_error",
            table_name=self.table_name,
            question=state.question,
            failed_sql=state.sql_query,
            error_message=error_msg,
            columns=state.schema_context.get("columns", {}),
        )

        response = self.llm.generate_sync([{"role": "user", "content": prompt}])
        sql = re.sub(r"```sql\s*", "", response)
        sql = re.sub(r"```\s*", "", sql).strip()
        return {
            "sql_query": sql,
            "retry_count": new_retry,
            "is_valid": False,
            "validation_error": "",
            "execution_error": "",
        }

    # === ROUTING ===

    def _route_after_validate(self, state: NL2SQLState) -> str:
        return "execute_sql" if state.is_valid else "handle_error"

    def _route_after_execute(self, state: NL2SQLState) -> str:
        return END if not state.execution_error else "handle_error"

    def _route_after_error(self, state: NL2SQLState) -> str:
        return "generate_sql" if state.retry_count < self.max_retries else END

    # === GRAPH ===

    def _build_graph(self):
        graph = StateGraph(NL2SQLState)

        graph.add_node("get_context", self.node_get_context)
        graph.add_node("generate_sql", self.node_generate_sql)
        graph.add_node("validate_sql", self.node_validate_sql)
        graph.add_node("execute_sql", self.node_execute_sql)
        graph.add_node("handle_error", self.node_handle_error)

        graph.set_entry_point("get_context")
        graph.add_edge("get_context", "generate_sql")
        graph.add_edge("generate_sql", "validate_sql")
        graph.add_conditional_edges(
            "validate_sql", self._route_after_validate, ["execute_sql", "handle_error"]
        )
        graph.add_conditional_edges(
            "execute_sql", self._route_after_execute, [END, "handle_error"]
        )
        graph.add_conditional_edges(
            "handle_error", self._route_after_error, ["generate_sql", END]
        )

        return graph.compile()

    def run(self, question: str) -> NL2SQLState:
        """Execută agentul."""
        initial = NL2SQLState(
            question=question,
            table_name=self.table_name,
            max_retries=self.max_retries,
        )
        return self.graph.invoke(initial)
