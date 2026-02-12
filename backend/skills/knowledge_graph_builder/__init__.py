"""
Knowledge Graph Builder Skill

Constructs contract dependency graphs for TenderCortex.
Detects cycles (deadlocks) and exports to Mermaid/GraphML.
"""

from .definition import (
    CycleInfo,
    EdgeType,
    GraphEdge,
    GraphNode,
    GraphOutput,
    GraphTooLargeError,
    InvalidEdgeTypeError,
    InvalidNodeTypeError,
    KnowledgeGraphError,
    NodeType,
    TripleExtraction,
)

from .impl import (
    KnowledgeGraphBuilder,
    build_contract_graph,
    TRIPLE_EXTRACTION_PROMPT,
)

__all__ = [
    # Classes
    "KnowledgeGraphBuilder",
    # Models
    "CycleInfo",
    "EdgeType",
    "GraphEdge",
    "GraphNode",
    "GraphOutput",
    "NodeType",
    "TripleExtraction",
    # Exceptions
    "GraphTooLargeError",
    "InvalidEdgeTypeError",
    "InvalidNodeTypeError",
    "KnowledgeGraphError",
    # Functions
    "build_contract_graph",
    # Constants
    "TRIPLE_EXTRACTION_PROMPT",
]
