"""
Knowledge Graph Builder - Implementation

Constructs dependency graphs from contract text using:
- networkx for graph structure
- LLM for triple extraction
- Cycle detection for deadlocks
- Mermaid/GraphML export

Author: TenderCortex Team
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

try:
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
except ImportError:
    from definition import (
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

logger = logging.getLogger(__name__)


# LLM prompt for triple extraction
TRIPLE_EXTRACTION_PROMPT = """Eres un experto en análisis contractual. Tu tarea es extraer TODAS las relaciones entre entidades de un texto legal/contractual.

## Tipos de Entidades (Nodos)
- requirement: Requisito del pliego
- stakeholder: Actor (Cliente, Proveedor, Contratista)
- milestone: Hito de proyecto o pago
- resource: Recurso (servidor, licencia, personal)
- risk: Riesgo o penalidad
- document: Documento o Anexo
- clause: Cláusula específica

## Tipos de Relaciones (Predicados)
- depends_on: A no puede existir/completarse sin B
- blocks: Si A ocurre, B no puede ocurrir
- requires: A necesita B para funcionar
- triggered_by: A sucede porque/después de que B sucedió
- conflicts_with: A y B son mutuamente excluyentes
- mentions: A hace referencia a B

## Formato de Salida (JSON Array)
[
  {
    "subject": {"id": "identificador_unico", "label": "Nombre Legible", "type": "tipo"},
    "predicate": "tipo_de_relacion",
    "object": {"id": "identificador_unico", "label": "Nombre Legible", "type": "tipo"}
  }
]

## REGLAS IMPORTANTES
1. Cada entidad debe tener un ID único en snake_case
2. Usa SOLO los tipos de nodos y relaciones listados arriba
3. Extrae TODAS las relaciones implícitas y explícitas
4. Si hay dependencia temporal ("después de", "tras"), usa triggered_by
5. Si hay dependencia lógica ("requiere", "necesita"), usa requires o depends_on

## TEXTO A ANALIZAR:
{text}

## SALIDA (solo JSON, sin explicaciones):"""


class KnowledgeGraphBuilder:
    """
    Constructs contract dependency graphs.
    
    Uses LLM for triple extraction and networkx for graph operations.
    Detects cycles (deadlocks) and exports to Mermaid/GraphML.
    
    Usage:
        builder = KnowledgeGraphBuilder()
        result = builder.build_from_text(
            "El pago se libera tras la aprobación..."
        )
        
        if result.has_deadlocks():
            print("⚠️ Deadlock detected!")
        
        print(result.mermaid_code)
    
    Raises:
        GraphTooLargeError: If graph exceeds node limit
    """
    
    MAX_NODES = 50  # Prevent graph explosion
    
    def __init__(self, llm_service=None):
        """
        Initialize the Knowledge Graph Builder.
        
        Args:
            llm_service: LLM service for triple extraction.
                         If None, will use mock extraction.
        """
        if not NETWORKX_AVAILABLE:
            raise KnowledgeGraphError(
                "networkx is required. Install with: pip install networkx"
            )
        
        self._llm_service = llm_service
        self._graph: Optional[nx.DiGraph] = None
    
    def build_from_text(
        self,
        text: str,
        section_label: Optional[str] = None,
        existing_graph: Optional[GraphOutput] = None,
        use_llm: bool = True,
    ) -> GraphOutput:
        """
        Build knowledge graph from contract text.
        
        Args:
            text: Contract section text to analyze.
            section_label: Label for the section (e.g., "Cláusula 5").
            existing_graph: Previous graph to extend (incremental build).
            use_llm: If True, use LLM for extraction. If False, use patterns.
        
        Returns:
            GraphOutput with nodes, edges, and Mermaid code.
        
        Raises:
            GraphTooLargeError: If resulting graph exceeds MAX_NODES.
        """
        logger.info(f"Building graph from text ({len(text)} chars)")
        
        # Initialize or load existing graph
        if existing_graph:
            self._graph = self._load_from_output(existing_graph)
        else:
            self._graph = nx.DiGraph()
        
        # Extract triples
        if use_llm and self._llm_service:
            triples = self._extract_triples_llm(text)
        else:
            triples = self._extract_triples_pattern(text)
        
        # Add triples to graph
        nodes_added = []
        edges_added = []
        
        for triple in triples:
            # Add subject node
            if triple.subject.id not in self._graph:
                self._graph.add_node(
                    triple.subject.id,
                    label=triple.subject.label,
                    type=triple.subject.type.value,
                    properties=triple.subject.properties,
                    section=section_label,
                )
                nodes_added.append(triple.subject)
            
            # Add object node
            if triple.object.id not in self._graph:
                self._graph.add_node(
                    triple.object.id,
                    label=triple.object.label,
                    type=triple.object.type.value,
                    properties=triple.object.properties,
                    section=section_label,
                )
                nodes_added.append(triple.object)
            
            # Add edge
            self._graph.add_edge(
                triple.subject.id,
                triple.object.id,
                relation=triple.predicate.value,
                weight=triple.confidence,
            )
            edges_added.append(GraphEdge(
                source=triple.subject.id,
                target=triple.object.id,
                relation=triple.predicate,
                weight=triple.confidence,
            ))
        
        # Check size limit
        if len(self._graph.nodes) > self.MAX_NODES:
            raise GraphTooLargeError(len(self._graph.nodes), self.MAX_NODES)
        
        # Detect cycles
        cycles = self.find_cycles()
        
        # Build output
        all_nodes = self._get_all_nodes()
        all_edges = self._get_all_edges()
        
        warnings = []
        if cycles:
            warnings.append(
                f"⚠️ {len(cycles)} deadlock(s) detectado(s). "
                f"Revise las dependencias circulares."
            )
        
        if len(self._graph.nodes) > 30:
            warnings.append(
                f"El grafo tiene {len(self._graph.nodes)} nodos. "
                f"Considere subdividir para mejor visualización."
            )
        
        mermaid = self.to_mermaid()
        
        logger.info(
            f"Graph built: {len(all_nodes)} nodes, {len(all_edges)} edges, "
            f"{len(cycles)} cycles"
        )
        
        return GraphOutput(
            nodes=all_nodes,
            edges=all_edges,
            mermaid_code=mermaid,
            cycles_detected=cycles,
            total_nodes=len(all_nodes),
            total_edges=len(all_edges),
            warnings=warnings,
            section_label=section_label,
        )
    
    def _extract_triples_llm(self, text: str) -> List[TripleExtraction]:
        """Extract triples using LLM."""
        try:
            prompt = TRIPLE_EXTRACTION_PROMPT.format(text=text)
            
            # Call LLM (sync or async depending on service)
            if hasattr(self._llm_service, 'invoke'):
                response = self._llm_service.invoke(prompt)
                content = response.content if hasattr(response, 'content') else str(response)
            else:
                content = str(self._llm_service(prompt))
            
            # Parse JSON response
            json_match = re.search(r'\[[\s\S]*\]', content)
            if not json_match:
                logger.warning("No JSON found in LLM response, using pattern extraction")
                return self._extract_triples_pattern(text)
            
            data = json.loads(json_match.group())
            return self._parse_triples(data)
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}, using pattern extraction")
            return self._extract_triples_pattern(text)
    
    def _extract_triples_pattern(self, text: str) -> List[TripleExtraction]:
        """
        Extract triples using pattern matching (fallback).
        
        Basic heuristics for common contract patterns.
        """
        triples = []
        text_lower = text.lower()
        
        # Pattern: "X se libera/realiza tras/después de Y"
        pattern_triggered = re.finditer(
            r'(?:el\s+)?(\w+(?:\s+\w+)?)\s+(?:se\s+)?(?:libera|realiza|ejecuta|completa)\s+'
            r'(?:tras|después de|luego de)\s+(?:la\s+)?(\w+(?:\s+\w+)?)',
            text_lower
        )
        for match in pattern_triggered:
            subject = match.group(1).strip()
            obj = match.group(2).strip()
            triples.append(TripleExtraction(
                subject=GraphNode(id=subject, label=subject.title(), type=NodeType.MILESTONE),
                predicate=EdgeType.TRIGGERED_BY,
                object=GraphNode(id=obj, label=obj.title(), type=NodeType.MILESTONE),
                confidence=0.7,
            ))
        
        # Pattern: "X requiere/necesita Y"
        pattern_requires = re.finditer(
            r'(?:el\s+|la\s+)?(\w+(?:\s+\w+)?)\s+(?:requiere|necesita|depende de)\s+'
            r'(?:el\s+|la\s+)?(\w+(?:\s+\w+)?)',
            text_lower
        )
        for match in pattern_requires:
            subject = match.group(1).strip()
            obj = match.group(2).strip()
            triples.append(TripleExtraction(
                subject=GraphNode(id=subject, label=subject.title(), type=NodeType.REQUIREMENT),
                predicate=EdgeType.REQUIRES,
                object=GraphNode(id=obj, label=obj.title(), type=NodeType.RESOURCE),
                confidence=0.7,
            ))
        
        # Pattern: "si X falla/no se cumple, Y"
        pattern_blocks = re.finditer(
            r'si\s+(?:el\s+|la\s+)?(\w+(?:\s+\w+)?)\s+(?:falla|no se cumple|no ocurre)[,\s]+'
            r'(?:se aplicará\s+)?(?:el\s+|la\s+)?(\w+(?:\s+\w+)?)',
            text_lower
        )
        for match in pattern_blocks:
            subject = match.group(1).strip()
            obj = match.group(2).strip()
            triples.append(TripleExtraction(
                subject=GraphNode(id=subject, label=subject.title(), type=NodeType.RESOURCE),
                predicate=EdgeType.BLOCKS,
                object=GraphNode(id=obj, label=obj.title(), type=NodeType.RISK),
                confidence=0.6,
            ))
        
        return triples
    
    def _parse_triples(self, data: List[Dict]) -> List[TripleExtraction]:
        """Parse JSON triples into TripleExtraction objects."""
        triples = []
        
        for item in data:
            try:
                subject_data = item.get("subject", {})
                object_data = item.get("object", {})
                predicate_str = item.get("predicate", "related_to")
                
                # Parse node types
                subject_type = self._parse_node_type(subject_data.get("type", "requirement"))
                object_type = self._parse_node_type(object_data.get("type", "requirement"))
                
                # Parse edge type
                edge_type = self._parse_edge_type(predicate_str)
                
                triple = TripleExtraction(
                    subject=GraphNode(
                        id=subject_data.get("id", "unknown"),
                        label=subject_data.get("label", "Unknown"),
                        type=subject_type,
                    ),
                    predicate=edge_type,
                    object=GraphNode(
                        id=object_data.get("id", "unknown"),
                        label=object_data.get("label", "Unknown"),
                        type=object_type,
                    ),
                    confidence=item.get("confidence", 0.8),
                )
                triples.append(triple)
                
            except Exception as e:
                logger.warning(f"Failed to parse triple: {e}")
                continue
        
        return triples
    
    def _parse_node_type(self, type_str: str) -> NodeType:
        """Parse string to NodeType enum."""
        type_lower = type_str.lower()
        for nt in NodeType:
            if nt.value == type_lower:
                return nt
        return NodeType.REQUIREMENT
    
    def _parse_edge_type(self, edge_str: str) -> EdgeType:
        """Parse string to EdgeType enum."""
        edge_lower = edge_str.lower()
        for et in EdgeType:
            if et.value == edge_lower:
                return et
        return EdgeType.RELATED_TO
    
    def find_cycles(self) -> List[CycleInfo]:
        """
        Find all cycles (deadlocks) in the graph.
        
        Returns:
            List of CycleInfo with nodes involved in each cycle.
        """
        if self._graph is None:
            return []
        
        cycles = []
        try:
            # Find all simple cycles
            nx_cycles = list(nx.simple_cycles(self._graph))
            
            for cycle in nx_cycles:
                # Get labels for better description
                labels = []
                for node_id in cycle:
                    node_data = self._graph.nodes.get(node_id, {})
                    labels.append(node_data.get("label", node_id))
                
                cycle_info = CycleInfo(
                    nodes=cycle,
                    description=(
                        f"Dependencia circular: {' → '.join(labels)} → {labels[0]}"
                    ),
                    severity="high" if len(cycle) <= 3 else "medium",
                )
                cycles.append(cycle_info)
                
        except Exception as e:
            logger.warning(f"Error finding cycles: {e}")
        
        return cycles
    
    def to_mermaid(self) -> str:
        """
        Generate Mermaid diagram code.
        
        Returns:
            String with Mermaid graph definition.
        """
        if self._graph is None or len(self._graph.nodes) == 0:
            return "graph TD\n    empty[No nodes]"
        
        lines = ["graph TD"]
        
        # Add node definitions with labels
        for node_id in self._graph.nodes:
            node_data = self._graph.nodes[node_id]
            label = node_data.get("label", node_id)
            node_type = node_data.get("type", "requirement")
            
            # Shape based on type
            if node_type == "milestone":
                lines.append(f'    {node_id}(("{label}"))')
            elif node_type == "risk":
                lines.append(f'    {node_id}[/"{label}"\\]')
            elif node_type == "stakeholder":
                lines.append(f'    {node_id}[["{label}"]]')
            else:
                lines.append(f'    {node_id}["{label}"]')
        
        # Add edges
        for source, target in self._graph.edges:
            edge_data = self._graph.edges[source, target]
            relation = edge_data.get("relation", "related_to")
            lines.append(f'    {source} -->|{relation}| {target}')
        
        return "\n".join(lines)
    
    def export_graphml(self, filepath: str):
        """Export graph to GraphML format."""
        if self._graph is None:
            raise KnowledgeGraphError("No graph to export")
        
        nx.write_graphml(self._graph, filepath)
        logger.info(f"Graph exported to {filepath}")
    
    def _get_all_nodes(self) -> List[GraphNode]:
        """Get all nodes as GraphNode objects."""
        nodes = []
        for node_id in self._graph.nodes:
            data = self._graph.nodes[node_id]
            node = GraphNode(
                id=node_id,
                label=data.get("label", node_id),
                type=NodeType(data.get("type", "requirement")),
                properties=data.get("properties", {}),
                source_section=data.get("section"),
            )
            nodes.append(node)
        return nodes
    
    def _get_all_edges(self) -> List[GraphEdge]:
        """Get all edges as GraphEdge objects."""
        edges = []
        for source, target in self._graph.edges:
            data = self._graph.edges[source, target]
            edge = GraphEdge(
                source=source,
                target=target,
                relation=EdgeType(data.get("relation", "related_to")),
                weight=data.get("weight", 1.0),
            )
            edges.append(edge)
        return edges
    
    def _load_from_output(self, output: GraphOutput) -> nx.DiGraph:
        """Load graph from GraphOutput object."""
        graph = nx.DiGraph()
        
        for node in output.nodes:
            graph.add_node(
                node.id,
                label=node.label,
                type=node.type.value,
                properties=node.properties,
                section=node.source_section,
            )
        
        for edge in output.edges:
            graph.add_edge(
                edge.source,
                edge.target,
                relation=edge.relation.value,
                weight=edge.weight,
            )
        
        return graph


# Convenience function
def build_contract_graph(
    text: str,
    section_label: Optional[str] = None,
) -> GraphOutput:
    """
    Build graph with default settings.
    
    Convenience function for simple use cases.
    """
    builder = KnowledgeGraphBuilder()
    return builder.build_from_text(text, section_label, use_llm=False)
