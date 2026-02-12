"""
Financial Specialist Agent.

This module implements the concrete specialist agent for financial domain
questions in RFP documents. It handles budget, payment schemes, guarantees,
and financial capacity requirements.

Example:
    from app.agents.specialists import FinancialSpecialistAgent
    
    agent = FinancialSpecialistAgent(llm=llm_service, logger=agent_logger)
    response = await agent.generate(question, context_docs)
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseSpecialistAgent, LLMProtocol, LoggerProtocol
from app.agents.prompts import FINANCIAL_PROMPT, RESPONSE_FORMAT_TEMPLATE
from app.core.exceptions import AgentProcessingError

# [Skill Integration] - Financial Table Parser
try:
    from skills.financial_table_parser.impl import extract_financial_tables
    FINANCIAL_PARSER_AVAILABLE = True
except ImportError:
    FINANCIAL_PARSER_AVAILABLE = False


class FinancialSpecialistAgent(BaseSpecialistAgent):
    """
    Specialist agent for financial and economic aspects of RFPs.
    
    Handles questions related to:
    - Official budget and component breakdown
    - Funding sources
    - Payment schemes and milestones
    - Required guarantees (bid maintenance, performance, advance)
    - Price adjustment mechanisms
    - Financial capacity requirements (equity, liquidity, billing)

    Enhanced with:
    - Financial Table Parser skill for deterministic extraction of budgets and price tables
    """

    DOMAIN: str = "financial"
    SYSTEM_PROMPT: str = FINANCIAL_PROMPT

    def __init__(
        self,
        llm: LLMProtocol,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """
        Initialize the Financial Specialist Agent.

        Args:
            llm: LLM service implementing LLMProtocol for generation.
            logger: Optional logger implementing LoggerProtocol for tracing.
        """
        super().__init__(llm=llm, logger=logger)

    async def generate(
        self,
        question: str,
        context: List[Document],
    ) -> str:
        """
        Generate a financial analysis response for the given question.

        This method processes the question using the financial specialist's
        expertise in budgets, payments, guarantees, and financial requirements.

        Args:
            question: The user's financial-related question.
            context: List of relevant document chunks for context.

        Returns:
            A formatted response with financial analysis, including
            amounts, percentages, and specific citations from documents.

        Raises:
            AgentProcessingError: If the LLM invocation fails.

        Example:
            >>> response = await agent.generate(
            ...     "¿Cuál es el presupuesto total?",
            ...     context_docs
            ... )
        """
        self._log_enter({"question": question, "context_size": len(context)})

        try:
            # Format context from documents
            context_text = self._format_context(context)

            if not context_text.strip():
                self._log_exit("No financial context available")
                return "No encontré información financiera relevante para responder tu pregunta."

            self._log_debug(f"Processing with {len(context)} documents")
            
            # --- SKILL INTEGRATION: Financial Table Parser ---
            skill_context = ""
            if FINANCIAL_PARSER_AVAILABLE and context:
                try:
                    # Group pages by source file to minimize opens
                    files_to_pages = {}
                    for doc in context:
                        source = doc.metadata.get("source")
                        page = doc.metadata.get("page")
                        if source and page is not None:
                            if source not in files_to_pages:
                                files_to_pages[source] = set()
                            files_to_pages[source].add(int(page))
                    
                    tables_found = []
                    for file_path, pages in files_to_pages.items():
                        # Limit pages to prevent slow processing (e.g., max 5 unique pages per query)
                        # We sort and take a subset if needed, or just process all if reasonable count
                        sorted_pages = sorted(list(pages))[:5] 
                        page_range = ",".join(str(p) for p in sorted_pages)
                        
                        try:
                            # Run parser
                            result = extract_financial_tables(
                                file_path=file_path,
                                page_range=page_range,
                                confidence_threshold=0.6
                            )
                            
                            for table in result.tables:
                                # Format brief summary table in Markdown
                                headers = " | ".join(table.headers)
                                sep = " | ".join(["---"] * len(table.headers))
                                rows_md = []
                                for r in table.rows:
                                    row_vals = [str(r.raw_data.get(h, "")) for h in table.headers_original]
                                    rows_md.append(" | ".join(row_vals))
                                
                                table_md = f"\n**Tabla en Pág {table.page_number} (Total detectado: {table.total_detected:,.2f} {table.currency_detected})**\n"
                                table_md += f"| {headers} |\n| {sep} |\n"
                                table_md += "\n".join([f"| {row} |" for row in rows_md])
                                tables_found.append(table_md)

                        except Exception as p_err:
                            self._log_debug(f"Parser skipped file {file_path}: {p_err}")
                            continue

                    if tables_found:
                        skill_context = (
                            f"\n\n--- [SKILL] TABLAS FINANCIERAS DETECTADAS ---\n"
                            f"{chr(10).join(tables_found)}\n"
                            f"----------------------------------------------\n"
                        )
                        self._log_debug(f"Skill 'financial-table-parser' extracted {len(tables_found)} tables")
                    
                except Exception as s_err:
                    self._log_error(f"Skill 'financial-table-parser' execution failed: {s_err}")
                    skill_context = ""
            # -----------------------------------------------

            # Build the full system prompt with response format
            full_system_prompt = f"{self.SYSTEM_PROMPT}\n\n{RESPONSE_FORMAT_TEMPLATE}"

            # Construct messages for LLM
            messages = [
                SystemMessage(content=full_system_prompt),
                HumanMessage(
                    content=f"Contexto del documento:\n{context_text}\n{skill_context}\n\nPregunta: {question}"
                ),
            ]

            # Invoke LLM
            response = await self._llm.ainvoke(messages)
            answer = response.content

            self._log_exit(f"Generated {len(answer)} chars")
            return answer

        except Exception as e:
            self._log_error(e)
            raise AgentProcessingError(
                message="Failed to generate financial response",
                agent_name=self.node_name,
                original_error=e,
            )
