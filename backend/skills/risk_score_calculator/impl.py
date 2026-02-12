"""
Risk Score Calculator - Implementation

Deterministic bid viability scoring with:
- Weighted severity scoring
- Kill switch for CRITICAL risks
- Category breakdown
- Risk matrix generation

Author: TenderCortex Team
"""

import logging
from typing import Dict, List, Optional

try:
    from .definition import (
        CategoryBreakdown,
        EmptyRiskListError,
        InvalidRiskDataError,
        Recommendation,
        RiskAssessmentOutput,
        RiskCalculatorError,
        RiskCategory,
        RiskFactorInput,
        RiskMatrixCell,
        Severity,
    )
except ImportError:
    from definition import (
        CategoryBreakdown,
        EmptyRiskListError,
        InvalidRiskDataError,
        Recommendation,
        RiskAssessmentOutput,
        RiskCalculatorError,
        RiskCategory,
        RiskFactorInput,
        RiskMatrixCell,
        Severity,
    )

logger = logging.getLogger(__name__)


# Severity weights for scoring
SEVERITY_WEIGHTS: Dict[Severity, float] = {
    Severity.LOW: 2.0,
    Severity.MEDIUM: 5.0,
    Severity.HIGH: 15.0,
    Severity.CRITICAL: 100.0,  # Will trigger kill switch anyway
}

# Recommendation thresholds
THRESHOLD_GO = 70.0
THRESHOLD_REVIEW = 40.0

# Probability levels for risk matrix
PROBABILITY_THRESHOLDS = {
    "low": (0.0, 0.33),
    "medium": (0.33, 0.66),
    "high": (0.66, 1.01),
}

# Impact levels based on severity
SEVERITY_TO_IMPACT = {
    Severity.LOW: "low",
    Severity.MEDIUM: "medium",
    Severity.HIGH: "high",
    Severity.CRITICAL: "high",
}

# Risk matrix colors
MATRIX_COLORS = {
    ("low", "low"): "green",
    ("low", "medium"): "green",
    ("low", "high"): "yellow",
    ("medium", "low"): "green",
    ("medium", "medium"): "yellow",
    ("medium", "high"): "red",
    ("high", "low"): "yellow",
    ("high", "medium"): "red",
    ("high", "high"): "red",
}


class RiskScoreCalculator:
    """
    Deterministic bid viability calculator.
    
    Converts qualitative risk findings into a quantitative score (0-100)
    with GO/NO-GO/REVIEW recommendation.
    
    Usage:
        calculator = RiskScoreCalculator()
        result = calculator.calculate([
            RiskFactorInput(
                description="Margen bajo",
                category=RiskCategory.FINANCIAL,
                severity=Severity.HIGH,
                probability=0.8,
                source_agent="FinancialAgent"
            ),
        ])
        
        print(f"Score: {result.total_score}, Rec: {result.recommendation}")
    
    Raises:
        EmptyRiskListError: If risk list is empty
        InvalidRiskDataError: If risk data is malformed
    """
    
    BASE_SCORE = 100.0
    
    def __init__(
        self,
        go_threshold: float = THRESHOLD_GO,
        review_threshold: float = THRESHOLD_REVIEW,
        allow_empty_risks: bool = False,
    ):
        """
        Initialize the Risk Score Calculator.
        
        Args:
            go_threshold: Minimum score for GO recommendation (default: 70)
            review_threshold: Minimum score for REVIEW recommendation (default: 40)
            allow_empty_risks: If True, empty risk list returns perfect score
        """
        self.go_threshold = go_threshold
        self.review_threshold = review_threshold
        self.allow_empty_risks = allow_empty_risks
    
    def calculate(
        self,
        risks: List[RiskFactorInput],
    ) -> RiskAssessmentOutput:
        """
        Calculate the viability score from a list of risks.
        
        Args:
            risks: List of RiskFactorInput from various agents.
        
        Returns:
            RiskAssessmentOutput with score, recommendation, and breakdown.
        
        Raises:
            EmptyRiskListError: If risks is empty and allow_empty_risks=False.
        """
        # Handle empty list
        if not risks:
            if self.allow_empty_risks:
                return self._create_perfect_score()
            raise EmptyRiskListError()
        
        logger.info(f"Calculating risk score for {len(risks)} risks")
        
        # Step 1: Check for Kill Switch (CRITICAL risks)
        critical_risks = [
            r for r in risks if r.severity == Severity.CRITICAL
        ]
        
        if critical_risks:
            return self._create_kill_switch_result(critical_risks, risks)
        
        # Step 2: Calculate weighted penalties
        total_penalty = 0.0
        category_penalties: Dict[RiskCategory, float] = {
            cat: 0.0 for cat in RiskCategory
        }
        category_counts: Dict[RiskCategory, int] = {
            cat: 0 for cat in RiskCategory
        }
        high_risk_count = 0
        
        for risk in risks:
            weight = SEVERITY_WEIGHTS[risk.severity]
            penalty = weight * risk.probability
            
            total_penalty += penalty
            category_penalties[risk.category] += penalty
            category_counts[risk.category] += 1
            
            if risk.severity == Severity.HIGH:
                high_risk_count += 1
        
        # Step 3: Calculate scores
        total_score = max(0.0, self.BASE_SCORE - total_penalty)
        
        # Step 4: Build category breakdown
        breakdown = {}
        for cat in RiskCategory:
            cat_score = max(0.0, self.BASE_SCORE - category_penalties[cat])
            breakdown[cat.value] = CategoryBreakdown(
                category=cat,
                score=cat_score,
                risk_count=category_counts[cat],
                total_penalty=category_penalties[cat],
            )
        
        # Step 5: Determine recommendation
        recommendation, reason = self._determine_recommendation(
            total_score, high_risk_count, risks
        )
        
        # Step 6: Build risk matrix
        risk_matrix = self._build_risk_matrix(risks)
        
        logger.info(
            f"Score: {total_score:.1f}, Recommendation: {recommendation.value}"
        )
        
        return RiskAssessmentOutput(
            total_score=round(total_score, 2),
            recommendation=recommendation,
            recommendation_reason=reason,
            critical_flags=[],
            kill_switch_activated=False,
            breakdown_by_category=breakdown,
            total_risks=len(risks),
            high_risks_count=high_risk_count,
            risk_matrix=risk_matrix,
        )
    
    def _create_perfect_score(self) -> RiskAssessmentOutput:
        """Create a perfect score result for empty risk list."""
        breakdown = {
            cat.value: CategoryBreakdown(
                category=cat,
                score=100.0,
                risk_count=0,
                total_penalty=0.0,
            )
            for cat in RiskCategory
        }
        
        return RiskAssessmentOutput(
            total_score=100.0,
            recommendation=Recommendation.GO,
            recommendation_reason="No se detectaron riesgos.",
            critical_flags=[],
            kill_switch_activated=False,
            breakdown_by_category=breakdown,
            total_risks=0,
            high_risks_count=0,
            risk_matrix=[],
        )
    
    def _create_kill_switch_result(
        self,
        critical_risks: List[RiskFactorInput],
        all_risks: List[RiskFactorInput],
    ) -> RiskAssessmentOutput:
        """Create a kill switch result when CRITICAL risks are found."""
        critical_flags = [r.description for r in critical_risks]
        
        # Still calculate breakdown for informational purposes
        category_counts: Dict[RiskCategory, int] = {
            cat: 0 for cat in RiskCategory
        }
        for risk in all_risks:
            category_counts[risk.category] += 1
        
        breakdown = {
            cat.value: CategoryBreakdown(
                category=cat,
                score=0.0 if category_counts[cat] > 0 else 100.0,
                risk_count=category_counts[cat],
                total_penalty=100.0 if category_counts[cat] > 0 else 0.0,
            )
            for cat in RiskCategory
        }
        
        logger.warning(
            f"Kill Switch activated! Critical risks: {critical_flags}"
        )
        
        return RiskAssessmentOutput(
            total_score=0.0,
            recommendation=Recommendation.NO_GO,
            recommendation_reason=(
                f"Kill Switch activado: {len(critical_risks)} riesgo(s) "
                f"CRÍTICO(s) detectado(s). La propuesta no es viable."
            ),
            critical_flags=critical_flags,
            kill_switch_activated=True,
            breakdown_by_category=breakdown,
            total_risks=len(all_risks),
            high_risks_count=sum(
                1 for r in all_risks if r.severity == Severity.HIGH
            ),
            risk_matrix=self._build_risk_matrix(all_risks),
        )
    
    def _determine_recommendation(
        self,
        score: float,
        high_risk_count: int,
        risks: List[RiskFactorInput],
    ) -> tuple:
        """Determine recommendation based on score and risk profile."""
        if score >= self.go_threshold:
            if high_risk_count > 0:
                return (
                    Recommendation.GO,
                    f"Score favorable ({score:.1f}), pero revisar "
                    f"{high_risk_count} riesgo(s) alto(s)."
                )
            return (
                Recommendation.GO,
                f"Propuesta viable con score de {score:.1f}/100."
            )
        
        elif score >= self.review_threshold:
            return (
                Recommendation.REVIEW,
                f"Score moderado ({score:.1f}). Se requiere revisión "
                f"manual antes de decidir."
            )
        
        else:
            return (
                Recommendation.NO_GO,
                f"Score insuficiente ({score:.1f}). "
                f"La acumulación de riesgos desaconseja presentarse."
            )
    
    def _build_risk_matrix(
        self,
        risks: List[RiskFactorInput],
    ) -> List[RiskMatrixCell]:
        """Build the 3x3 risk matrix for visualization."""
        # Initialize matrix cells
        matrix: Dict[tuple, List[str]] = {
            (impact, prob): []
            for impact in ["low", "medium", "high"]
            for prob in ["low", "medium", "high"]
        }
        
        # Classify each risk
        for risk in risks:
            impact = SEVERITY_TO_IMPACT[risk.severity]
            
            # Determine probability level
            prob_level = "high"
            for level, (low, high) in PROBABILITY_THRESHOLDS.items():
                if low <= risk.probability < high:
                    prob_level = level
                    break
            
            matrix[(impact, prob_level)].append(risk.description)
        
        # Convert to list of RiskMatrixCell
        cells = []
        for (impact, prob), descriptions in matrix.items():
            if descriptions:  # Only include non-empty cells
                cells.append(RiskMatrixCell(
                    impact_level=impact,
                    probability_level=prob,
                    risks=descriptions,
                    color=MATRIX_COLORS.get((impact, prob), "green"),
                ))
        
        return cells
    
    def calculate_from_dicts(
        self,
        risk_dicts: List[dict],
    ) -> RiskAssessmentOutput:
        """
        Calculate score from a list of dictionaries.
        
        Convenience method for when risks come from JSON/API.
        """
        risks = [RiskFactorInput(**d) for d in risk_dicts]
        return self.calculate(risks)


# Convenience function
def calculate_viability_score(
    risks: List[RiskFactorInput],
) -> RiskAssessmentOutput:
    """
    Calculate viability score with default settings.
    
    Convenience function for simple use cases.
    """
    calculator = RiskScoreCalculator()
    return calculator.calculate(risks)
