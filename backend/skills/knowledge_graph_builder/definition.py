"""
Knowledge Graph Builder - Data Definitions

Pydantic models for contract dependency graph construction.
Supports ontology-constrained nodes and edges.

Author: TenderCortex Team
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class NodeType(str, Enum):
    """
    Taxonomía de tipos de nodo en el grafo contractual.
    
    Ontología restringida para evitar "bola de pelo".
    """
    REQUIREMENT = "requirement"   # Requisito del pliego
    STAKEHOLDER = "stakeholder"   # Actor (Cliente, Proveedor)
    MILESTONE = "milestone"       # Hito de proyecto/pago
    RESOURCE = "resource"         # Recurso (servidor, licencia)
    RISK = "risk"                 # Riesgo identificado
    DOCUMENT = "document"         # Documento/Anexo
    CLAUSE = "clause"             # Cláusula específica


class EdgeType(str, Enum):
    """
    Tipos de relaciones permitidas entre nodos.
    
    Semántica direccional: source → target
    """
    DEPENDS_ON = "depends_on"       # A no puede existir sin B
    BLOCKS = "blocks"               # Si A ocurre, B no puede
    REQUIRES = "requires"           # A necesita B para funcionar
    RELATED_TO = "related_to"       # A menciona o refiere a B
    TRIGGERED_BY = "triggered_by"   # A sucede porque B sucedió
    CONFLICTS_WITH = "conflicts_with"  # A y B son mutuamente excluyentes
    MENTIONS = "mentions"           # A hace referencia a B


class GraphNode(BaseModel):
    """
    Representa un nodo en el grafo de conocimiento.
    """
    
    id: str = Field(
        ...,
        description="Identificador único normalizado (snake_case)."
    )
    
    label: str = Field(
        ...,
        description="Nombre legible por humanos."
    )
    
    type: NodeType = Field(
        default=NodeType.REQUIREMENT,
        description="Tipo de nodo según la ontología."
    )
    
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Propiedades adicionales del nodo."
    )
    
    source_page: Optional[int] = Field(
        default=None,
        description="Página del documento donde se encontró."
    )
    
    source_section: Optional[str] = Field(
        default=None,
        description="Sección del documento (ej. 'Cláusula 5')."
    )
    
    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        """Normaliza el ID a snake_case."""
        # Remover caracteres especiales y normalizar
        normalized = re.sub(r'[^\w\s]', '', v.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        return normalized[:50]  # Limitar longitud


class GraphEdge(BaseModel):
    """
    Representa una arista (relación) en el grafo.
    """
    
    source: str = Field(
        ...,
        description="ID del nodo origen."
    )
    
    target: str = Field(
        ...,
        description="ID del nodo destino."
    )
    
    relation: EdgeType = Field(
        ...,
        description="Tipo de relación según la ontología."
    )
    
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fuerza de la relación (0-1)."
    )
    
    label: Optional[str] = Field(
        default=None,
        description="Etiqueta descriptiva para visualización."
    )
    
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Propiedades adicionales de la arista."
    )
    
    def to_mermaid_arrow(self) -> str:
        """Genera la representación Mermaid de esta arista."""
        label = self.label or self.relation.value.upper()
        return f'{self.source} -->|{label}| {self.target}'


class CycleInfo(BaseModel):
    """Información sobre un ciclo detectado (deadlock)."""
    
    nodes: List[str] = Field(
        description="Lista de nodos en el ciclo."
    )
    
    description: str = Field(
        description="Descripción del deadlock."
    )
    
    severity: str = Field(
        default="high",
        description="Severidad: high, medium, low"
    )


class GraphOutput(BaseModel):
    """
    Resultado completo de la construcción del grafo.
    """
    
    nodes: List[GraphNode] = Field(
        default_factory=list,
        description="Lista de nodos en el grafo."
    )
    
    edges: List[GraphEdge] = Field(
        default_factory=list,
        description="Lista de aristas en el grafo."
    )
    
    mermaid_code: Optional[str] = Field(
        default=None,
        description="Código Mermaid para visualización."
    )
    
    cycles_detected: List[CycleInfo] = Field(
        default_factory=list,
        description="Ciclos (deadlocks) detectados."
    )
    
    total_nodes: int = Field(
        default=0,
        description="Total de nodos en el grafo."
    )
    
    total_edges: int = Field(
        default=0,
        description="Total de aristas en el grafo."
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Advertencias sobre la estructura."
    )
    
    section_label: Optional[str] = Field(
        default=None,
        description="Sección del documento analizada."
    )
    
    def has_deadlocks(self) -> bool:
        """Retorna True si hay ciclos detectados."""
        return len(self.cycles_detected) > 0
    
    def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """Busca un nodo por su ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edges_from(self, node_id: str) -> List[GraphEdge]:
        """Retorna todas las aristas que salen de un nodo."""
        return [e for e in self.edges if e.source == node_id]
    
    def get_edges_to(self, node_id: str) -> List[GraphEdge]:
        """Retorna todas las aristas que llegan a un nodo."""
        return [e for e in self.edges if e.target == node_id]
    
    def to_summary(self) -> str:
        """Genera resumen del grafo."""
        deadlock_warning = ""
        if self.cycles_detected:
            deadlock_warning = f" ⚠️ {len(self.cycles_detected)} deadlock(s)"
        
        return (
            f"📊 Grafo: {self.total_nodes} nodos, {self.total_edges} aristas"
            f"{deadlock_warning}"
        )


class TripleExtraction(BaseModel):
    """Tripleta extraída por el LLM."""
    
    subject: GraphNode = Field(description="Nodo sujeto.")
    predicate: EdgeType = Field(description="Tipo de relación.")
    object: GraphNode = Field(description="Nodo objeto.")
    confidence: float = Field(default=0.8, ge=0, le=1)


# Custom Exceptions

class KnowledgeGraphError(Exception):
    """Excepción base para errores del grafo."""
    pass


class InvalidNodeTypeError(KnowledgeGraphError):
    """Tipo de nodo no válido."""
    def __init__(self, node_type: str):
        self.node_type = node_type
        valid = [t.value for t in NodeType]
        super().__init__(
            f"Tipo de nodo '{node_type}' no válido. "
            f"Tipos permitidos: {valid}"
        )


class InvalidEdgeTypeError(KnowledgeGraphError):
    """Tipo de arista no válido."""
    def __init__(self, edge_type: str):
        self.edge_type = edge_type
        valid = [t.value for t in EdgeType]
        super().__init__(
            f"Tipo de arista '{edge_type}' no válido. "
            f"Tipos permitidos: {valid}"
        )


class GraphTooLargeError(KnowledgeGraphError):
    """El grafo excede el límite recomendado."""
    def __init__(self, nodes: int, max_nodes: int):
        self.nodes = nodes
        self.max_nodes = max_nodes
        super().__init__(
            f"El grafo tiene {nodes} nodos, excede el límite de {max_nodes}. "
            f"Procese por secciones para evitar explosión de nodos."
        )
