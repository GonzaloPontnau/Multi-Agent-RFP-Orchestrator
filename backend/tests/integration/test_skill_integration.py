
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Path Setup similar to test_rfp_loader.py to ensure imports work
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Set dummy env vars to satisfy Settings validation
os.environ["GROQ_API_KEY"] = "dummy_groq_key"
os.environ["HUGGINGFACE_API_KEY"] = "dummy_hf_key"
os.environ["PINECONE_API_KEY"] = "dummy_pinecone_key"
os.environ["PINECONE_ENV"] = "dummy_env"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["OPENAI_API_KEY"] = "dummy_openai_key"
os.environ["TAVILY_API_KEY"] = "dummy_tavily_key"

# Imports from app
from app.agents.specialists.technical_agent import TechnicalSpecialistAgent
from app.agents.specialists.financial_agent import FinancialSpecialistAgent
from app.agents.risk_sentinel import risk_audit
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

# Mock Skills imports if they fail (for environment w/o deps)
# But we assume they work as per previous steps.

@pytest.mark.asyncio
class TestSkillIntegration:

    async def test_technical_agent_uses_tech_mapper(self):
        """Verify TechnicalAgent extracts tech stack and injects it into prompt."""
        
        # Mock LLM
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = AIMessage(content="Analysis complete.")
        
        agent = TechnicalSpecialistAgent(llm=mock_llm)
        
        # Context with obvious tech keywords
        context = [
            Document(page_content="We require Python 3.11 and PostgreSQL database with React frontend."),
            Document(page_content="Legacy system uses Java 8.")
        ]
        
        # We assume real extract_tech_stack works if imports match.
        # If not, we patch it. Let's patch it to verify call.
        with patch("app.agents.specialists.technical_agent.extract_tech_stack") as mock_mapper:
            # Setup mock return
            mock_result = MagicMock()
            mock_result.entities = [MagicMock(canonical_name="Python"), MagicMock(canonical_name="PostgreSQL")]
            mock_result.stack_summary = "STACK DETECTED"
            mock_mapper.return_value = mock_result
            
            response = await agent.generate("Describe the stack", context)
            
            # Verify mapper called
            mock_mapper.assert_called_once()
            
            # Verify prompt contained the summary
            call_args = mock_llm.ainvoke.call_args
            # call_args[0] is args, call_args[0][0] is messages list
            messages = call_args[0][0]
            last_msg = messages[-1].content
            
            assert "ANÁLISIS AUTOMÁTICO DE STACK TECNOLÓGICO" in last_msg
            assert "STACK DETECTED" in last_msg
            assert "Python" in last_msg


    async def test_financial_agent_uses_table_parser(self):
        """Verify FinancialAgent calls parser and injects tables."""
        
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = AIMessage(content="Budget is 100k.")
        
        agent = FinancialSpecialistAgent(llm=mock_llm)
        
        context = [
            Document(page_content="Page text", metadata={"source": "/tmp/test.pdf", "page": 1})
        ]
        
        with patch("app.agents.specialists.financial_agent.extract_financial_tables") as mock_parser:
            # Setup mock return
            mock_table = MagicMock()
            mock_table.page_number = 1
            mock_table.total_detected = 1000.0
            mock_table.currency_detected = "USD"
            mock_table.headers = ["Item", "Cost"]
            mock_table.headers_original = ["Item", "Cost"]
            mock_table.rows = [MagicMock(raw_data={"Item": "Server", "Cost": "1000"})]
            
            mock_result = MagicMock()
            mock_result.tables = [mock_table]
            mock_parser.return_value = mock_result
            
            await agent.generate("What is the cost?", context)
            
            # Verify parser called
            mock_parser.assert_called()
            
            # Verify prompt injection
            messages = mock_llm.ainvoke.call_args[0][0]
            prompt = messages[-1].content
            
            assert "TABLAS FINANCIERAS DETECTADAS" in prompt
            assert "Total detectado: 1,000.00 USD" in prompt
            assert "Server" in prompt


    async def test_risk_sentinel_uses_calculator(self):
        """Verify RiskSentinel uses RiskScoreCalculator when JSON contains risk_factors."""
        
        # Mock LLM to return JSON with risk_factors
        llm_response_json = """
        {
            "risk_factors": [
                {
                    "description": "The proposed solution cost is significantly higher than budget",
                    "category": "financial",
                    "severity": "high",
                    "probability": 0.9
                }
            ],
            "compliance_status": "approved",
            "gate_passed": true,
            "issues": []
        }
        """
        
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = AIMessage(content=llm_response_json)
        
        # Patch get_llm to return our mock
        with patch("app.agents.risk_sentinel.get_llm", return_value=mock_llm):
            # Patch RiskScoreCalculator to ensure we control the calc 
            # OR we trust real logic. Real logic is deterministic, let's use valid input.
            # Severity HIGH (score 15) * 0.9 = 13.5 penalty.
            # Base 100 - 13.5 = 86.5.
            # Thresholds: GO >= 70. So Recommendation should be GO.
            # But High Risk Count = 1.
            # Logic: If High Risk > 0, returns (GO, "but review high risks").
            
            risk_level, compliance, issues, gate = await risk_audit(
                answer="Proposed solution cost is high.",
                context=[Document(page_content="Budget is low.")],
                question="Is it viable?"
            )
            
            # Check if logs contain evidence of calculator
            # Since we can't easily check logs here without capturing them,
            # we check the side effects: issues list should contain Score.
            
            score_issue = next((i for i in issues if "[RiskScore]" in i), None)
            assert score_issue is not None, f"Expected [RiskScore] in issues, got: {issues}"
            assert "Score: 86.5" in score_issue
            
            # Verify risk level logic
            # Score 86.5 is > 70, so Low/Medium usually, but High Risk present might affect it?
            # Code: if score < 70 -> high. if score < 40 -> critical.
            # Else determined by mapped recommendation.
            # Rec was GO -> risk_level="low".
            assert risk_level == "low"
            assert compliance == "approved"
            assert gate is True

