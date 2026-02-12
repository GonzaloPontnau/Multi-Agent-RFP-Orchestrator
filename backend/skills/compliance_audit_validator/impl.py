"""
Compliance Audit Validator - Implementation

LLM-powered requirement compliance auditing with:
- Traffic light protocol (COMPLIANT/NON_COMPLIANT/PARTIAL/MISSING_INFO)
- Gap analysis for non-compliant requirements
- Severity detection (MANDATORY vs DESIRABLE)
- Skeptical auditor prompt engineering

Author: TenderCortex Team
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

try:
    from .definition import (
        AuditResult,
        BatchAuditResult,
        ComplianceCheckInput,
        ComplianceStatus,
        ComplianceValidatorError,
        InsufficientContextError,
        LLMServiceError,
        ParseResponseError,
        RequirementCategory,
        SeverityLevel,
    )
except ImportError:
    from definition import (
        AuditResult,
        BatchAuditResult,
        ComplianceCheckInput,
        ComplianceStatus,
        ComplianceValidatorError,
        InsufficientContextError,
        LLMServiceError,
        ParseResponseError,
        RequirementCategory,
        SeverityLevel,
    )

logger = logging.getLogger(__name__)


# Keywords for severity detection
MANDATORY_KEYWORDS = {
    # Spanish
    "debe", "deberá", "deberán", "obligatorio", "obligatoria",
    "excluyente", "indispensable", "imprescindible", "requisito",
    "necesario", "necesaria", "requerido", "requerida",
    # English
    "shall", "must", "required", "mandatory", "essential",
    "necessary", "obligation", "compulsory",
}

DESIRABLE_KEYWORDS = {
    # Spanish
    "valorará", "valorara", "deseable", "preferible", "preferente",
    "opcional", "adicional", "plus", "ventaja", "puntuará",
    "bonificación", "mejora",
    # English
    "should", "may", "desirable", "preferred", "optional",
    "plus", "bonus", "advantage", "recommended",
}


# System prompt for the skeptical auditor
AUDITOR_SYSTEM_PROMPT = """Eres un AUDITOR DE LICITACIONES extremadamente estricto y escéptico. Tu trabajo es determinar si una empresa CUMPLE o NO CUMPLE un requisito específico de un pliego de licitación.

## REGLAS INAMOVIBLES:

1. **Presunción de Incumplimiento**: Si la información NO está EXPLÍCITAMENTE en el contexto de la empresa, asume que NO lo tienen. No inventes ni supongas.

2. **Pesimismo Constructivo**: Es mejor un falso negativo (decir que no cumple cuando sí cumple) que un falso positivo (decir que cumple cuando no cumple). Los falsos positivos causan descalificaciones.

3. **Detección de Severidad**:
   - Verbos como "DEBE", "DEBERÁ", "SHALL", "MUST", "obligatorio", "excluyente" → MANDATORY
   - Verbos como "se valorará", "deseable", "preferible", "plus" → DESIRABLE

4. **Evidencia Obligatoria**: Debes citar EXACTAMENTE el fragmento del contexto que respalda tu veredicto. Si no hay fragmento que citar, el status debe ser MISSING_INFO.

5. **Gap Analysis**: Para status NON_COMPLIANT o PARTIAL, DEBES generar un análisis de brecha específico indicando QUÉ falta exactamente.

## FORMATO DE RESPUESTA (JSON ESTRICTO):

```json
{
    "status": "compliant|non_compliant|partial|missing_info",
    "confidence_score": 0.0-1.0,
    "severity_detected": "mandatory|desirable",
    "reasoning": "Explicación paso a paso del análisis...",
    "gap_analysis": "Qué falta exactamente para cumplir (null si COMPLIANT)",
    "evidence_found": "Fragmento textual del contexto citado (null si MISSING_INFO)"
}
```

RESPONDE ÚNICAMENTE CON EL JSON. Sin explicaciones adicionales."""


class ComplianceAuditValidator:
    """
    LLM-powered compliance auditor for RFP requirements.
    
    Analyzes requirements against company context and emits
    structured verdicts with gap analysis.
    
    Usage:
        validator = ComplianceAuditValidator(llm_service)
        result = await validator.validate(
            requirement_text="El licitante DEBERÁ contar con ISO 27001",
            requirement_source_page=32,
            company_context="Certificaciones: ISO 9001, ISO 14001"
        )
        
        if result.is_showstopper():
            print(f"⚠️ SHOWSTOPPER: {result.gap_analysis}")
    
    Raises:
        LLMServiceError: If LLM communication fails
        ParseResponseError: If response cannot be parsed
    """
    
    def __init__(self, llm_service=None):
        """
        Initialize the Compliance Audit Validator.
        
        Args:
            llm_service: The LLM service for generating verdicts.
                         If None, will attempt to import from app.services.
        """
        self._llm_service = llm_service
        self._initialized = False
    
    async def _ensure_service(self):
        """Lazy initialization of LLM service."""
        if self._llm_service is None:
            try:
                from app.services.llm_factory import get_llm
                self._llm_service = get_llm()
            except ImportError:
                raise LLMServiceError(
                    "No se pudo importar LLM service. Asegúrese de "
                    "ejecutar desde el contexto correcto de la aplicación."
                )
        self._initialized = True
    
    async def validate(
        self,
        requirement_text: str,
        requirement_source_page: int,
        company_context: str,
        requirement_category: Optional[RequirementCategory] = None,
    ) -> AuditResult:
        """
        Validate a single requirement against company context.
        
        Args:
            requirement_text: Exact text of the requirement from RFP.
            requirement_source_page: Page number in the RFP.
            company_context: Relevant company profile fragments.
            requirement_category: Optional category for classification.
        
        Returns:
            AuditResult with verdict and gap analysis.
        
        Raises:
            LLMServiceError: If LLM communication fails.
            ParseResponseError: If response cannot be parsed.
        """
        # Validate input
        input_data = ComplianceCheckInput(
            requirement_text=requirement_text,
            requirement_source_page=requirement_source_page,
            company_context=company_context,
            requirement_category=requirement_category,
        )
        
        await self._ensure_service()
        
        # Pre-detect severity based on keywords
        pre_severity = self._detect_severity(input_data.requirement_text)
        
        logger.info(
            f"Validating requirement (page {requirement_source_page}): "
            f"'{requirement_text[:50]}...' [pre-severity: {pre_severity.value}]"
        )
        
        # Build the audit prompt
        user_prompt = self._build_user_prompt(input_data)
        
        try:
            # Call LLM
            response = await self._call_llm(user_prompt)
            
            # Parse response
            result = self._parse_response(
                response, 
                requirement_source_page,
                pre_severity
            )
            
            return result
            
        except Exception as e:
            if isinstance(e, ComplianceValidatorError):
                raise
            raise LLMServiceError(str(e), e)
    
    async def validate_batch(
        self,
        requirements: List[Dict[str, Any]],
    ) -> BatchAuditResult:
        """
        Validate multiple requirements.
        
        Args:
            requirements: List of dicts with requirement_text, 
                          requirement_source_page, company_context.
        
        Returns:
            BatchAuditResult with aggregate statistics.
        """
        results = []
        
        for req in requirements:
            try:
                result = await self.validate(
                    requirement_text=req["requirement_text"],
                    requirement_source_page=req["requirement_source_page"],
                    company_context=req["company_context"],
                    requirement_category=req.get("requirement_category"),
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error validating requirement: {e}")
                # Create a MISSING_INFO result for failed validations
                results.append(AuditResult(
                    status=ComplianceStatus.MISSING_INFO,
                    confidence_score=0.0,
                    reasoning=f"Error durante la validación: {str(e)}",
                    severity_detected=SeverityLevel.MANDATORY,
                    requirement_page=req["requirement_source_page"],
                ))
        
        batch_result = BatchAuditResult(results=results)
        batch_result.calculate_stats()
        
        return batch_result
    
    def _detect_severity(self, requirement_text: str) -> SeverityLevel:
        """
        Pre-detect severity based on keyword analysis.
        
        This is a heuristic; the LLM will confirm or override.
        """
        text_lower = requirement_text.lower()
        
        # Check for mandatory keywords
        for keyword in MANDATORY_KEYWORDS:
            if keyword in text_lower:
                return SeverityLevel.MANDATORY
        
        # Check for desirable keywords
        for keyword in DESIRABLE_KEYWORDS:
            if keyword in text_lower:
                return SeverityLevel.DESIRABLE
        
        # Default to mandatory for safety
        return SeverityLevel.MANDATORY
    
    def _build_user_prompt(self, input_data: ComplianceCheckInput) -> str:
        """Build the user prompt for the LLM."""
        category_str = ""
        if input_data.requirement_category:
            category_str = f"\nCategoría del requisito: {input_data.requirement_category.value}"
        
        return f"""## REQUISITO A EVALUAR (Página {input_data.requirement_source_page}):
"{input_data.requirement_text}"
{category_str}

## CONTEXTO DE LA EMPRESA:
{input_data.company_context}

## TU TAREA:
Analiza si la empresa CUMPLE el requisito. Aplica las reglas del auditor escéptico.
Responde ÚNICAMENTE con el JSON estructurado."""
    
    async def _call_llm(self, user_prompt: str) -> str:
        """Call the LLM service with the audit prompt."""
        try:
            # The exact method depends on your LLM service implementation
            # This is a generic interface that should work with most services
            
            if hasattr(self._llm_service, 'ainvoke'):
                # LangChain style
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [
                    SystemMessage(content=AUDITOR_SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
                response = await self._llm_service.ainvoke(messages)
                return response.content
            
            elif hasattr(self._llm_service, 'chat'):
                # OpenAI style
                response = await self._llm_service.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,  # Low temperature for consistency
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content
            
            elif hasattr(self._llm_service, 'generate'):
                # Generic generate method
                full_prompt = f"{AUDITOR_SYSTEM_PROMPT}\n\n{user_prompt}"
                response = await self._llm_service.generate(full_prompt)
                return response
            
            else:
                raise LLMServiceError(
                    "LLM service does not have a recognized interface"
                )
                
        except Exception as e:
            raise LLMServiceError(f"Error calling LLM: {str(e)}", e)
    
    def _parse_response(
        self,
        response: str,
        requirement_page: int,
        pre_severity: SeverityLevel,
    ) -> AuditResult:
        """Parse the LLM response into an AuditResult."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ParseResponseError(response)
            
            data = json.loads(json_match.group())
            
            # Map status string to enum
            status_str = data.get("status", "missing_info").lower()
            status_map = {
                "compliant": ComplianceStatus.COMPLIANT,
                "non_compliant": ComplianceStatus.NON_COMPLIANT,
                "partial": ComplianceStatus.PARTIAL,
                "missing_info": ComplianceStatus.MISSING_INFO,
            }
            status = status_map.get(status_str, ComplianceStatus.MISSING_INFO)
            
            # Map severity string to enum
            severity_str = data.get("severity_detected", "mandatory").lower()
            severity = (
                SeverityLevel.DESIRABLE 
                if severity_str == "desirable" 
                else SeverityLevel.MANDATORY
            )
            
            # If LLM didn't detect, use our pre-detection
            if not data.get("severity_detected"):
                severity = pre_severity
            
            return AuditResult(
                status=status,
                confidence_score=float(data.get("confidence_score", 0.7)),
                reasoning=data.get("reasoning", "Sin razonamiento proporcionado."),
                gap_analysis=data.get("gap_analysis"),
                severity_detected=severity,
                evidence_found=data.get("evidence_found"),
                requirement_page=requirement_page,
            )
            
        except json.JSONDecodeError as e:
            raise ParseResponseError(response)
        except Exception as e:
            raise ParseResponseError(f"Error parsing: {str(e)} - Response: {response}")
    
    def validate_sync(
        self,
        requirement_text: str,
        requirement_source_page: int,
        company_context: str,
        requirement_category: Optional[RequirementCategory] = None,
    ) -> AuditResult:
        """
        Synchronous wrapper for validate().
        
        For use in non-async contexts.
        """
        import asyncio
        return asyncio.run(self.validate(
            requirement_text=requirement_text,
            requirement_source_page=requirement_source_page,
            company_context=company_context,
            requirement_category=requirement_category,
        ))


# Convenience function
async def audit_requirement(
    requirement_text: str,
    requirement_source_page: int,
    company_context: str,
) -> AuditResult:
    """
    Audit a single requirement with default settings.
    
    Convenience function for simple use cases.
    """
    validator = ComplianceAuditValidator()
    return await validator.validate(
        requirement_text=requirement_text,
        requirement_source_page=requirement_source_page,
        company_context=company_context,
    )
