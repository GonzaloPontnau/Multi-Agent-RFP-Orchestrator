"""
Tech Stack Mapper - Implementation

Extracts and normalizes technology mentions from RFP documents.
Features:
- Canonical name normalization
- Category classification
- Requirement level detection (Mandatory/Nice-to-have/Forbidden)
- Version constraint extraction
- Compatibility scoring

Author: TenderCortex Team
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from .definition import (
        AmbiguousTechError,
        CompatibilityResult,
        EmptyInputError,
        RequirementLevel,
        TechCategory,
        TechEntity,
        TechMapperError,
        TechStackOutput,
    )
except ImportError:
    from definition import (
        AmbiguousTechError,
        CompatibilityResult,
        EmptyInputError,
        RequirementLevel,
        TechCategory,
        TechEntity,
        TechMapperError,
        TechStackOutput,
    )

logger = logging.getLogger(__name__)


# ============================================================================
# CANONICAL MAPPING DICTIONARY
# ============================================================================

CANONICAL_MAP: Dict[str, Tuple[str, TechCategory]] = {
    # ----- JavaScript/TypeScript Ecosystem -----
    "javascript": ("JavaScript", TechCategory.LANGUAGE),
    "js": ("JavaScript", TechCategory.LANGUAGE),
    "ecmascript": ("JavaScript", TechCategory.LANGUAGE),
    "typescript": ("TypeScript", TechCategory.LANGUAGE),
    "ts": ("TypeScript", TechCategory.LANGUAGE),
    "nodejs": ("Node.js", TechCategory.FRAMEWORK),
    "node.js": ("Node.js", TechCategory.FRAMEWORK),
    "node": ("Node.js", TechCategory.FRAMEWORK),
    "react": ("React", TechCategory.FRAMEWORK),
    "reactjs": ("React", TechCategory.FRAMEWORK),
    "react.js": ("React", TechCategory.FRAMEWORK),
    "react js": ("React", TechCategory.FRAMEWORK),
    "vuejs": ("Vue.js", TechCategory.FRAMEWORK),
    "vue.js": ("Vue.js", TechCategory.FRAMEWORK),
    "vue": ("Vue.js", TechCategory.FRAMEWORK),
    "angular": ("Angular", TechCategory.FRAMEWORK),
    "angularjs": ("AngularJS", TechCategory.FRAMEWORK),
    "nextjs": ("Next.js", TechCategory.FRAMEWORK),
    "next.js": ("Next.js", TechCategory.FRAMEWORK),
    "nuxt": ("Nuxt.js", TechCategory.FRAMEWORK),
    "nuxtjs": ("Nuxt.js", TechCategory.FRAMEWORK),
    "express": ("Express.js", TechCategory.FRAMEWORK),
    "expressjs": ("Express.js", TechCategory.FRAMEWORK),
    "nestjs": ("NestJS", TechCategory.FRAMEWORK),
    "nest.js": ("NestJS", TechCategory.FRAMEWORK),
    
    # ----- Python Ecosystem -----
    "python": ("Python", TechCategory.LANGUAGE),
    "python3": ("Python", TechCategory.LANGUAGE),
    "python 3": ("Python", TechCategory.LANGUAGE),
    "py": ("Python", TechCategory.LANGUAGE),
    "django": ("Django", TechCategory.FRAMEWORK),
    "flask": ("Flask", TechCategory.FRAMEWORK),
    "fastapi": ("FastAPI", TechCategory.FRAMEWORK),
    "pandas": ("Pandas", TechCategory.FRAMEWORK),
    "numpy": ("NumPy", TechCategory.FRAMEWORK),
    "tensorflow": ("TensorFlow", TechCategory.FRAMEWORK),
    "pytorch": ("PyTorch", TechCategory.FRAMEWORK),
    "scikit-learn": ("scikit-learn", TechCategory.FRAMEWORK),
    "sklearn": ("scikit-learn", TechCategory.FRAMEWORK),
    "celery": ("Celery", TechCategory.FRAMEWORK),
    
    # ----- Java Ecosystem -----
    "java": ("Java", TechCategory.LANGUAGE),
    "openjdk": ("Java", TechCategory.LANGUAGE),
    "jdk": ("Java", TechCategory.LANGUAGE),
    "spring": ("Spring Framework", TechCategory.FRAMEWORK),
    "spring framework": ("Spring Framework", TechCategory.FRAMEWORK),
    "springboot": ("Spring Boot", TechCategory.FRAMEWORK),
    "spring boot": ("Spring Boot", TechCategory.FRAMEWORK),
    "spring-boot": ("Spring Boot", TechCategory.FRAMEWORK),
    "hibernate": ("Hibernate", TechCategory.FRAMEWORK),
    "maven": ("Maven", TechCategory.TOOL),
    "gradle": ("Gradle", TechCategory.TOOL),
    
    # ----- .NET Ecosystem -----
    "c#": ("C#", TechCategory.LANGUAGE),
    "csharp": ("C#", TechCategory.LANGUAGE),
    ".net": (".NET", TechCategory.FRAMEWORK),
    "dotnet": (".NET", TechCategory.FRAMEWORK),
    ".net core": (".NET Core", TechCategory.FRAMEWORK),
    "asp.net": ("ASP.NET", TechCategory.FRAMEWORK),
    "aspnet": ("ASP.NET", TechCategory.FRAMEWORK),
    "blazor": ("Blazor", TechCategory.FRAMEWORK),
    
    # ----- Go Ecosystem -----
    "golang": ("Go", TechCategory.LANGUAGE),
    "go lang": ("Go", TechCategory.LANGUAGE),
    # "go" handled specially due to ambiguity
    
    # ----- Rust Ecosystem -----
    "rust": ("Rust", TechCategory.LANGUAGE),
    "rustlang": ("Rust", TechCategory.LANGUAGE),
    
    # ----- PHP Ecosystem -----
    "php": ("PHP", TechCategory.LANGUAGE),
    "laravel": ("Laravel", TechCategory.FRAMEWORK),
    "symfony": ("Symfony", TechCategory.FRAMEWORK),
    "wordpress": ("WordPress", TechCategory.FRAMEWORK),
    
    # ----- Ruby Ecosystem -----
    "ruby": ("Ruby", TechCategory.LANGUAGE),
    "rails": ("Ruby on Rails", TechCategory.FRAMEWORK),
    "ruby on rails": ("Ruby on Rails", TechCategory.FRAMEWORK),
    "ror": ("Ruby on Rails", TechCategory.FRAMEWORK),
    
    # ----- Databases -----
    "postgresql": ("PostgreSQL", TechCategory.DATABASE),
    "postgres": ("PostgreSQL", TechCategory.DATABASE),
    "pgsql": ("PostgreSQL", TechCategory.DATABASE),
    "mysql": ("MySQL", TechCategory.DATABASE),
    "mariadb": ("MariaDB", TechCategory.DATABASE),
    "oracle": ("Oracle Database", TechCategory.DATABASE),
    "oracle database": ("Oracle Database", TechCategory.DATABASE),
    "oracle db": ("Oracle Database", TechCategory.DATABASE),
    "sql server": ("SQL Server", TechCategory.DATABASE),
    "sqlserver": ("SQL Server", TechCategory.DATABASE),
    "mssql": ("SQL Server", TechCategory.DATABASE),
    "mongodb": ("MongoDB", TechCategory.DATABASE),
    "mongo": ("MongoDB", TechCategory.DATABASE),
    "redis": ("Redis", TechCategory.DATABASE),
    "elasticsearch": ("Elasticsearch", TechCategory.DATABASE),
    "elastic": ("Elasticsearch", TechCategory.DATABASE),
    "cassandra": ("Cassandra", TechCategory.DATABASE),
    "dynamodb": ("DynamoDB", TechCategory.DATABASE),
    "sqlite": ("SQLite", TechCategory.DATABASE),
    "couchdb": ("CouchDB", TechCategory.DATABASE),
    "neo4j": ("Neo4j", TechCategory.DATABASE),
    
    # ----- Cloud Providers -----
    "aws": ("AWS", TechCategory.INFRASTRUCTURE),
    "amazon web services": ("AWS", TechCategory.INFRASTRUCTURE),
    "azure": ("Microsoft Azure", TechCategory.INFRASTRUCTURE),
    "microsoft azure": ("Microsoft Azure", TechCategory.INFRASTRUCTURE),
    "gcp": ("Google Cloud Platform", TechCategory.INFRASTRUCTURE),
    "google cloud": ("Google Cloud Platform", TechCategory.INFRASTRUCTURE),
    "google cloud platform": ("Google Cloud Platform", TechCategory.INFRASTRUCTURE),
    "digitalocean": ("DigitalOcean", TechCategory.INFRASTRUCTURE),
    "heroku": ("Heroku", TechCategory.INFRASTRUCTURE),
    "vercel": ("Vercel", TechCategory.INFRASTRUCTURE),
    "netlify": ("Netlify", TechCategory.INFRASTRUCTURE),
    
    # ----- DevOps / Infrastructure -----
    "docker": ("Docker", TechCategory.INFRASTRUCTURE),
    "kubernetes": ("Kubernetes", TechCategory.INFRASTRUCTURE),
    "k8s": ("Kubernetes", TechCategory.INFRASTRUCTURE),
    "openshift": ("OpenShift", TechCategory.INFRASTRUCTURE),
    "terraform": ("Terraform", TechCategory.INFRASTRUCTURE),
    "ansible": ("Ansible", TechCategory.INFRASTRUCTURE),
    "jenkins": ("Jenkins", TechCategory.INFRASTRUCTURE),
    "gitlab ci": ("GitLab CI", TechCategory.INFRASTRUCTURE),
    "github actions": ("GitHub Actions", TechCategory.INFRASTRUCTURE),
    "circleci": ("CircleCI", TechCategory.INFRASTRUCTURE),
    "nginx": ("NGINX", TechCategory.INFRASTRUCTURE),
    "apache": ("Apache HTTP Server", TechCategory.INFRASTRUCTURE),
    "traefik": ("Traefik", TechCategory.INFRASTRUCTURE),
    "istio": ("Istio", TechCategory.INFRASTRUCTURE),
    "prometheus": ("Prometheus", TechCategory.INFRASTRUCTURE),
    "grafana": ("Grafana", TechCategory.INFRASTRUCTURE),
    "datadog": ("Datadog", TechCategory.INFRASTRUCTURE),
    
    # ----- Message Queues -----
    "rabbitmq": ("RabbitMQ", TechCategory.INFRASTRUCTURE),
    "kafka": ("Apache Kafka", TechCategory.INFRASTRUCTURE),
    "apache kafka": ("Apache Kafka", TechCategory.INFRASTRUCTURE),
    "sqs": ("Amazon SQS", TechCategory.INFRASTRUCTURE),
    "activemq": ("ActiveMQ", TechCategory.INFRASTRUCTURE),
    
    # ----- Security & Certifications -----
    "iso 27001": ("ISO 27001", TechCategory.SECURITY_CERT),
    "iso27001": ("ISO 27001", TechCategory.SECURITY_CERT),
    "iso 27002": ("ISO 27002", TechCategory.SECURITY_CERT),
    "iso 9001": ("ISO 9001", TechCategory.SECURITY_CERT),
    "iso9001": ("ISO 9001", TechCategory.SECURITY_CERT),
    "soc2": ("SOC 2", TechCategory.SECURITY_CERT),
    "soc 2": ("SOC 2", TechCategory.SECURITY_CERT),
    "gdpr": ("GDPR", TechCategory.SECURITY_CERT),
    "hipaa": ("HIPAA", TechCategory.SECURITY_CERT),
    "pci dss": ("PCI DSS", TechCategory.SECURITY_CERT),
    "pci-dss": ("PCI DSS", TechCategory.SECURITY_CERT),
    "ens": ("ENS", TechCategory.SECURITY_CERT),
    "cmmi": ("CMMI", TechCategory.SECURITY_CERT),
    "oauth": ("OAuth", TechCategory.SECURITY_CERT),
    "oauth2": ("OAuth 2.0", TechCategory.SECURITY_CERT),
    "saml": ("SAML", TechCategory.SECURITY_CERT),
    "ldap": ("LDAP", TechCategory.SECURITY_CERT),
    "ssl": ("SSL/TLS", TechCategory.SECURITY_CERT),
    "tls": ("SSL/TLS", TechCategory.SECURITY_CERT),
    
    # ----- Methodologies -----
    "agile": ("Agile", TechCategory.METHODOLOGY),
    "scrum": ("Scrum", TechCategory.METHODOLOGY),
    "kanban": ("Kanban", TechCategory.METHODOLOGY),
    "devops": ("DevOps", TechCategory.METHODOLOGY),
    "ci/cd": ("CI/CD", TechCategory.METHODOLOGY),
    "cicd": ("CI/CD", TechCategory.METHODOLOGY),
    "tdd": ("TDD", TechCategory.METHODOLOGY),
    "bdd": ("BDD", TechCategory.METHODOLOGY),
    
    # ----- Tools -----
    "git": ("Git", TechCategory.TOOL),
    "github": ("GitHub", TechCategory.TOOL),
    "gitlab": ("GitLab", TechCategory.TOOL),
    "bitbucket": ("Bitbucket", TechCategory.TOOL),
    "jira": ("Jira", TechCategory.TOOL),
    "confluence": ("Confluence", TechCategory.TOOL),
    "slack": ("Slack", TechCategory.TOOL),
    "teams": ("Microsoft Teams", TechCategory.TOOL),
    "figma": ("Figma", TechCategory.TOOL),
    "postman": ("Postman", TechCategory.TOOL),
    "swagger": ("Swagger/OpenAPI", TechCategory.TOOL),
    "openapi": ("Swagger/OpenAPI", TechCategory.TOOL),
}


# ============================================================================
# CONTEXT KEYWORDS
# ============================================================================

MANDATORY_KEYWORDS = [
    "debe", "deberá", "deberan", "obligatorio", "obligatoria",
    "requerido", "requerida", "imprescindible", "indispensable",
    "excluyente", "necesario", "necesaria", "exigido", "exigida",
    "must", "shall", "required", "mandatory", "essential",
]

NICE_TO_HAVE_KEYWORDS = [
    "valorará", "valorara", "deseable", "preferible", "preferente",
    "opcional", "plus", "bonificará", "bonificara", "puntuará",
    "puntuara", "adicional", "ventaja", "bonus",
    "preferred", "bonus", "nice to have", "nice-to-have",
    "optional", "desirable", "advantage",
]

FORBIDDEN_KEYWORDS = [
    "no usar", "no utilizar", "prohibido", "prohibida",
    "evitar", "nunca", "migrar desde", "migrar de",
    "reemplazar", "sustituir", "legacy", "obsoleto", "obsoleta",
    "descartado", "descartada", "excluido", "excluida",
    "must not", "forbidden", "avoid", "migrate from",
    "replace", "deprecated", "legacy",
]


# ============================================================================
# TECH STACK MAPPER CLASS
# ============================================================================

class TechStackMapper:
    """
    Technology stack extractor and normalizer.
    
    Extracts technology mentions from text, normalizes to canonical names,
    and classifies by category and requirement level.
    
    Usage:
        mapper = TechStackMapper()
        result = mapper.extract(["Backend en Python con Django..."])
        
        for entity in result.entities:
            print(f"{entity.canonical_name}: {entity.requirement_level}")
    
    Raises:
        EmptyInputError: If input text is empty
    """
    
    # Context window for requirement level detection (chars)
    CONTEXT_WINDOW = 50
    # Minimum confidence for ambiguous terms
    AMBIGUOUS_THRESHOLD = 0.6
    
    def __init__(self):
        """Initialize the Tech Stack Mapper."""
        # Build lowercase lookup for faster matching
        self._build_patterns()
    
    def _build_patterns(self):
        """Build regex patterns for tech detection."""
        # Sort by length (longer matches first)
        terms = sorted(CANONICAL_MAP.keys(), key=len, reverse=True)
        
        # Build pattern that matches whole words
        escaped = [re.escape(t) for t in terms]
        self._tech_pattern = re.compile(
            r'\b(' + '|'.join(escaped) + r')\b',
            re.IGNORECASE
        )
        
        # Special pattern for "Go" (needs context validation)
        self._go_pattern = re.compile(
            r'\b(en\s+go|con\s+go|golang|go\s+lang|lenguaje\s+go|'
            r'using\s+go|in\s+go|with\s+go)\b',
            re.IGNORECASE
        )
        
        # Version pattern
        self._version_pattern = re.compile(
            r'(?:v(?:ersion)?\.?\s*)?(\d+(?:\.\d+)*(?:\.\d+)?)'
            r'|([<>=!]+\s*\d+(?:\.\d+)*)',
            re.IGNORECASE
        )
    
    def extract(
        self,
        text_chunks: List[str],
        company_stack: Optional[List[str]] = None,
        include_context: bool = True,
    ) -> TechStackOutput:
        """
        Extract technology stack from text chunks.
        
        Args:
            text_chunks: List of text fragments to analyze.
            company_stack: Optional list of company technologies for matching.
            include_context: Include context snippets in output.
        
        Returns:
            TechStackOutput with all detected technologies.
        
        Raises:
            EmptyInputError: If text_chunks is empty.
        """
        if not text_chunks:
            raise EmptyInputError()
        
        combined_text = " ".join(text_chunks)
        if not combined_text.strip():
            raise EmptyInputError()
        
        logger.info(f"Extracting tech stack from {len(text_chunks)} chunks")
        
        entities: List[TechEntity] = []
        seen: Set[str] = set()  # Track canonical names to avoid duplicates
        warnings: List[str] = []
        
        # Find all tech mentions
        for match in self._tech_pattern.finditer(combined_text):
            raw = match.group(0)
            raw_lower = raw.lower()
            
            if raw_lower not in CANONICAL_MAP:
                continue
            
            canonical, category = CANONICAL_MAP[raw_lower]
            
            # Skip duplicates
            if canonical in seen:
                continue
            seen.add(canonical)
            
            # Get context around match
            start = max(0, match.start() - self.CONTEXT_WINDOW)
            end = min(len(combined_text), match.end() + self.CONTEXT_WINDOW)
            context = combined_text[start:end].strip()
            
            # Extract version if present
            version = self._extract_version(context, canonical)
            
            # Determine requirement level from context
            req_level = self._detect_requirement_level(context)
            
            entity = TechEntity(
                raw_text=raw,
                canonical_name=canonical,
                category=category,
                version_constraint=version,
                requirement_level=req_level,
                context_snippet=context if include_context else "",
                confidence=0.9,
            )
            entities.append(entity)
        
        # Check for "Go" specially (ambiguous)
        if "go" not in seen or "Go" not in seen:
            for match in self._go_pattern.finditer(combined_text):
                if "Go" in seen:
                    continue
                seen.add("Go")
                
                start = max(0, match.start() - self.CONTEXT_WINDOW)
                end = min(len(combined_text), match.end() + self.CONTEXT_WINDOW)
                context = combined_text[start:end].strip()
                
                req_level = self._detect_requirement_level(context)
                
                entity = TechEntity(
                    raw_text=match.group(0),
                    canonical_name="Go",
                    category=TechCategory.LANGUAGE,
                    requirement_level=req_level,
                    context_snippet=context if include_context else "",
                    confidence=0.85,  # Lower confidence due to ambiguity
                )
                entities.append(entity)
                warnings.append(
                    f"'Go' detectado con contexto. Verificar si es el lenguaje "
                    f"o el verbo inglés."
                )
        
        # Build categorized lists
        mandatory = [e for e in entities if e.requirement_level == RequirementLevel.MANDATORY]
        nice_to_have = [e for e in entities if e.requirement_level == RequirementLevel.NICE_TO_HAVE]
        forbidden = [e for e in entities if e.requirement_level == RequirementLevel.FORBIDDEN]
        
        # Group by category
        by_category: Dict[str, List[TechEntity]] = {}
        for category in TechCategory:
            cat_entities = [e for e in entities if e.category == category]
            if cat_entities:
                by_category[category.value] = cat_entities
        
        # Calculate compatibility if company_stack provided
        compatibility = None
        if company_stack:
            compatibility = self._calculate_compatibility(entities, company_stack)
        
        # Generate summary
        summary = self._generate_summary(mandatory, nice_to_have, forbidden)
        
        logger.info(
            f"Found {len(entities)} technologies: "
            f"{len(mandatory)} mandatory, {len(nice_to_have)} nice-to-have, "
            f"{len(forbidden)} forbidden"
        )
        
        return TechStackOutput(
            entities=entities,
            stack_summary=summary,
            mandatory_stack=mandatory,
            nice_to_have_stack=nice_to_have,
            forbidden_stack=forbidden,
            by_category=by_category,
            compatibility=compatibility,
            total_entities=len(entities),
            warnings=warnings,
        )
    
    def _extract_version(
        self,
        context: str,
        tech_name: str,
    ) -> Optional[str]:
        """Extract version constraint from context."""
        # Look for version near the technology name
        tech_lower = tech_name.lower()
        context_lower = context.lower()
        
        # Find position of tech
        pos = context_lower.find(tech_lower)
        if pos == -1:
            return None
        
        # Look for version within 15 chars after tech name (very close)
        end_pos = pos + len(tech_name)
        version_area = context[end_pos:end_pos + 15]
        
        # Only match if version starts immediately after tech name
        # Patterns: "Java 17", "Python 3.10", ">=3.8"
        match = re.match(r'^\s*(\d+(?:\.\d+)*|[<>=!]+\s*\d+(?:\.\d+)*)', version_area)
        if match:
            version = match.group(1)
            if version:
                return version.strip()
        
        return None
    
    def _detect_requirement_level(self, context: str, tech_position: int = -1) -> RequirementLevel:
        """
        Detect requirement level from context.
        
        Uses proximity-based scoring: keywords closer to the tech mention
        have more weight. Also respects sentence boundaries.
        """
        context_lower = context.lower()
        
        # Find the sentence containing the tech (rough heuristic)
        # Split by common sentence delimiters
        sentences = [s.strip() for s in context_lower.replace('\n', '. ').split('.') if s.strip()]
        
        # Score each requirement level
        scores = {
            RequirementLevel.FORBIDDEN: 0,
            RequirementLevel.NICE_TO_HAVE: 0,
            RequirementLevel.MANDATORY: 0,
        }
        
        # Check each sentence for keywords
        for sentence in sentences:
            # FORBIDDEN - only if directly associated
            for keyword in FORBIDDEN_KEYWORDS:
                if keyword in sentence:
                    # Higher score if the sentence is short (direct statement)
                    word_count = len(sentence.split())
                    if word_count < 15:
                        scores[RequirementLevel.FORBIDDEN] += 3
                    else:
                        scores[RequirementLevel.FORBIDDEN] += 1
            
            # NICE_TO_HAVE
            for keyword in NICE_TO_HAVE_KEYWORDS:
                if keyword in sentence:
                    word_count = len(sentence.split())
                    if word_count < 20:
                        scores[RequirementLevel.NICE_TO_HAVE] += 3
                    else:
                        scores[RequirementLevel.NICE_TO_HAVE] += 1
            
            # MANDATORY
            for keyword in MANDATORY_KEYWORDS:
                if keyword in sentence:
                    word_count = len(sentence.split())
                    if word_count < 20:
                        scores[RequirementLevel.MANDATORY] += 3
                    else:
                        scores[RequirementLevel.MANDATORY] += 1
        
        # Determine winner (forbidden > nice_to_have > mandatory)
        if scores[RequirementLevel.FORBIDDEN] >= 2:
            return RequirementLevel.FORBIDDEN
        
        if scores[RequirementLevel.NICE_TO_HAVE] >= 2:
            return RequirementLevel.NICE_TO_HAVE
        
        if scores[RequirementLevel.MANDATORY] >= 1:
            return RequirementLevel.MANDATORY
        
        # Default to mandatory (safer assumption for RFPs)
        return RequirementLevel.MANDATORY
    
    def _calculate_compatibility(
        self,
        entities: List[TechEntity],
        company_stack: List[str],
    ) -> CompatibilityResult:
        """Calculate compatibility between RFP requirements and company stack."""
        company_lower = {s.lower() for s in company_stack}
        
        required = {
            e.canonical_name for e in entities 
            if e.requirement_level == RequirementLevel.MANDATORY
        }
        forbidden = {
            e.canonical_name for e in entities 
            if e.requirement_level == RequirementLevel.FORBIDDEN
        }
        
        # Matched: company has and RFP requires
        matched = [
            name for name in required 
            if name.lower() in company_lower
        ]
        
        # Missing: RFP requires but company doesn't have
        missing = [
            name for name in required 
            if name.lower() not in company_lower
        ]
        
        # Extra: company has but RFP doesn't require
        required_lower = {r.lower() for r in required}
        extra = [
            s for s in company_stack 
            if s.lower() not in required_lower
        ]
        
        # Conflicts: company uses but RFP forbids
        conflicts = [
            name for name in forbidden 
            if name.lower() in company_lower
        ]
        
        # Calculate score
        if not required:
            score = 1.0
        else:
            score = len(matched) / len(required)
        
        # Penalty for conflicts
        if conflicts:
            score = max(0, score - 0.3 * len(conflicts))
        
        return CompatibilityResult(
            matched=matched,
            missing=missing,
            extra=extra,
            conflicts=conflicts,
            score=round(score, 2),
            has_blockers=len(conflicts) > 0,
        )
    
    def _generate_summary(
        self,
        mandatory: List[TechEntity],
        nice_to_have: List[TechEntity],
        forbidden: List[TechEntity],
    ) -> str:
        """Generate natural language summary."""
        parts = []
        
        if mandatory:
            names = [e.canonical_name for e in mandatory[:5]]
            s = ", ".join(names)
            if len(mandatory) > 5:
                s += f" (+{len(mandatory) - 5} más)"
            parts.append(f"Stack requerido: {s}")
        
        if nice_to_have:
            names = [e.canonical_name for e in nice_to_have[:3]]
            s = ", ".join(names)
            parts.append(f"Deseable: {s}")
        
        if forbidden:
            names = [e.canonical_name for e in forbidden]
            parts.append(f"Prohibido: {', '.join(names)}")
        
        return ". ".join(parts) + "." if parts else "No se detectaron tecnologías."


# Convenience function
def extract_tech_stack(
    text: str,
    company_stack: Optional[List[str]] = None,
) -> TechStackOutput:
    """
    Extract tech stack with default settings.
    
    Convenience function for simple use cases.
    """
    mapper = TechStackMapper()
    return mapper.extract([text], company_stack)
