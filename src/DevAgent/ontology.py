from __future__ import annotations
from .core import *
from enum import Enum
from typing import Any, Set
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# HDD Stages and Gates                                                        #
# --------------------------------------------------------------------------- #

class Stage(Enum):
  INTENT = "intent"
  DOMAIN = "domain"
  ABSTRACTION = "abstraction"
  EXEC = "exec"
  PRIMITIVE = "primitive"

class Gate(Enum):
  DOMAIN_MODEL = "G1"
  ABSTRACTION_SELECTION = "G2"
  EXECUTABLE_STRUCTURING = "G3"
  PRIMITIVE_REALISATION = "G4"

# --------------------------------------------------------------------------- #
# Ontology graph – proof‑of‑concept                                           #
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class Node:

  """
    A node in the ontology graph.

    Parameters
    ----------
    id:
      Globally‑unique identifier (hashable).
    label:
      Human‑readable semantic description.
    stage:
      HDD Stage (intent/domain/abstraction/exec/primitive)
    gates_passed:
      Set of Gate enums this node has passed.
    meta:
      Arbitrary key‑value annotations (JSON‑serialisable).
    """

  id: str
  label: str
  stage: Stage
  gates_passed: Set[Gate] = field(default_factory=set)
  meta: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class Edge:

  """
    A directed relationship between two nodes.

    Parameters
    ----------
    src:
      Source node identifier.
    rel:
      Relationship predicate (e.g. ``"decomposes_to"``, ``"is_a"``).
    dst:
      Destination node identifier.
    """

  src: str
  rel: str
  dst: str

class OntologyGraph:

  """
    In‑memory ontology backed by :pyclass:`networkx.DiGraph`.

    Exposes four primary surfaces:

    * *Mutate*  – ``add_node``, ``add_edge``, ``remove_subtree``
    * *Search*  – ``search``
    * *Query*   – ``query``
    * *Walk*    – ``walk`` / ``to_paths``

    The ``decomposes_to`` relation is treated as *structural*: it must not form
    cycles. Other relations are unconstrained.
    """

  # ----------------------------------------------------------------------- #
  # Construction                                                            #
  # ----------------------------------------------------------------------- #
  def __init__(self) -> None:
    self._g: nx.MultiDiGraph = nx.MultiDiGraph()

  # relation‑specific view for structural checks/traversals
  def _decompose_view(self) -> nx.MultiDiGraph: # type: ignore[name-defined]
    """Subgraph containing only 'decomposes_to' edges."""
    edges = [(u, v, k) for u, v, k in self._g.edges(keys=True) if k == "decomposes_to"]
    return self._g.edge_subgraph(edges).copy()

  # ----------------------------------------------------------------------- #
  # Mutation                                                                #
  # ----------------------------------------------------------------------- #
  def add_node(self, node: Node) -> None:
    """Insert *node*; raise ``ValueError`` on duplicate id."""
    if node.id in self._g:
      raise ValueError(f"Node id clash: {node.id!r}")
    self._g.add_node(
      node.id,
      label=node.label,
      stage=node.stage,
      gates_passed=set(node.gates_passed),
      meta=dict(node.meta),
    )

  def add_edge(self, src: str, rel: str, dst: str) -> None:
    """
        Create a directed edge ``(src, rel, dst)``.

        Both *src* and *dst* must already exist.
        """
    if src not in self._g or dst not in self._g:
      raise KeyError("Both endpoints must exist before adding an edge.")
    self._g.add_edge(src, dst, key=rel)

    if rel == "decomposes_to" and not nx.is_directed_acyclic_graph(self._decompose_view()):
      self._g.remove_edge(src, dst, key=rel)
      raise ValueError("Adding this 'decomposes_to' edge would create a cycle.")

  # --------------------------------------------------------------------- #
  # Convenience relation helpers                                          #
  # --------------------------------------------------------------------- #
  def add_decomposition(self, parent: str, child: str) -> None:
    """
        Shorthand for ``add_edge(parent, "decomposes_to", child)``.
        Enforces the same cycle check semantics as :py:meth:`add_edge`.
        """
    self.add_edge(parent, "decomposes_to", child)

  def add_is_a(self, subclass: str, superclass: str) -> None:
    """
        Shorthand for ``add_edge(subclass, "is_a", superclass)``.
        """
    self.add_edge(subclass, "is_a", superclass)

  def add_dependency(self, source: str, target: str) -> None:
    """
        Shorthand for ``add_edge(source, "depends_on", target)``.
        """
    self.add_edge(source, "depends_on", target)

  def remove_subtree(self, root: str) -> None:
    """
        Delete *root* and all descendants reachable via ``decomposes_to`` edges.
        """
    if root not in self._g:
      raise KeyError(root)
    targets = nx.descendants(self._decompose_view(), root)
    self._g.remove_nodes_from(targets | {root})

  # Facade helpers reflecting HDD vocabulary --------------------------------

  def add_intent(self, id: str, label: str, **meta: Any) -> str:
    """Create an intent node at Stage.INTENT."""
    node = Node(id, label, Stage.INTENT, set(), meta)
    self.add_node(node)
    return id

  def add_domain_entity(self, id: str, label: str, parent_id: str, **meta: Any) -> str:
    """Create a domain-model node under the given intent or domain node."""
    node = Node(id, label, Stage.DOMAIN, set(), meta)
    self.add_node(node)
    self.add_decomposition(parent_id, id)
    return id

  def refine_to_abstraction(self, id: str, label: str, parent_id: str, **meta: Any) -> str:
    """Create an abstraction node under the given domain or abstraction node."""
    node = Node(id, label, Stage.ABSTRACTION, set(), meta)
    self.add_node(node)
    self.add_decomposition(parent_id, id)
    return id

  def structure_executable(self, id: str, label: str, parent_id: str, **meta: Any) -> str:
    """Create an executable-structure node under the given abstraction."""
    node = Node(id, label, Stage.EXEC, set(), meta)
    self.add_node(node)
    self.add_decomposition(parent_id, id)
    return id

  def realise_primitive(self, id: str, label: str, parent_id: str, **meta: Any) -> str:
    """Create a primitive-realisation node under the given executable-structure."""
    node = Node(id, label, Stage.PRIMITIVE, set(), meta)
    self.add_node(node)
    self.add_decomposition(parent_id, id)
    return id

  def mark_gate(self, node_id: str, gate: Gate) -> None:
    """Manually mark that a node has passed the given gate."""
    if node_id not in self._g:
      raise KeyError(f"Node {node_id!r} does not exist")
    self._g.nodes[node_id].setdefault("gates_passed", set()).add(gate)

  def require_gate(self, node_id: str, gate: Gate) -> None:
    """Assert that the given gate has been passed for this node."""
    data = self._g.nodes.get(node_id)
    if data is None or gate not in data.get("gates_passed", set()):
      raise ValueError(f"Node {node_id!r} has not passed gate {gate}")

  # ----------------------------------------------------------------------- #
  # Search & Query                                                          #
  # ----------------------------------------------------------------------- #
  def search(self, text: str) -> list[str]:
    """
        Fuzzy label/meta match (case‑insensitive). Returns matching node ids.
        """
    t = text.lower()
    hits: list[str] = []
    for nid, data in self._g.nodes(data=True):
      if t in data.get("label", "").lower():
        hits.append(nid)
        continue
      for v in data.get("meta", {}).values():
        if t in str(v).lower():
          hits.append(nid)
          break
    return hits

  def query(self, src: str | None = None, rel: str | None = None, dst: str | None = None) -> list[Edge]:
    """
        Structured triple pattern. ``None`` is a wildcard.
        """
    edges_iter = (self._g.out_edges(src, keys=True) if src is not None else self._g.edges(keys=True))
    return [Edge(u, k, v) for u, v, k in edges_iter if (dst is None or v == dst) and (rel is None or k == rel)]

  # ----------------------------------------------------------------------- #
  # Walks                                                                   #
  # ----------------------------------------------------------------------- #
  def walk(self, root: str, *, order: str = "dfs") -> Iterator[str]:
    """
        Traverse from *root* through **all** outgoing edges using NetworkX helpers.

        Parameters
        ----------
        root:
          Starting node id.
        order:
          ``"dfs"`` (depth‑first, preorder) or ``"bfs"`` (breadth‑first).
        """
    if root not in self._g:
      raise KeyError(root)
    if order == "dfs":
      yield from nx.dfs_tree(self._g, root).nodes()
    elif order == "bfs":
      # bfs_tree returns a graph view ordered in BFS; iterate its nodes
      yield from nx.bfs_tree(self._g, root).nodes()
    else:
      raise ValueError("order must be 'dfs' or 'bfs'")

  def to_paths(self, root: str) -> list[list[str]]:
    """
        Return all decomposition paths rooted at *root*.

        Only edges with ``rel == 'decomposes_to'`` are followed.
        """
    if root not in self._g:
      raise KeyError(root)
    paths, stack = [], [(root, [root])]
    while stack:
      nid, path = stack.pop()
      children = [succ for succ in self._g.successors(nid) if self._g.has_edge(nid, succ, key="decomposes_to")]
      if not children:
        paths.append(path)
      else:
        for c in children:
          stack.append((c, path + [c]))
    return paths

  # ----------------------------------------------------------------------- #
  # Validation helpers                                                      #
  # ----------------------------------------------------------------------- #
  def detect_cycles(self) -> bool:
    """Return ``True`` if any cycle exists in the whole graph."""
    return not nx.is_directed_acyclic_graph(self._decompose_view())

  # ----------------------------------------------------------------------- #
  # Convenience dunders                                                     #
  # ----------------------------------------------------------------------- #
  def __len__(self) -> int: # number of nodes
    return self._g.number_of_nodes()

  def __contains__(self, nid: str) -> bool:
    return nid in self._g

  # ----------------------------------------------------------------------- #
  # Serialisation / Deserialisation (SeDer)                                 #
  # ----------------------------------------------------------------------- #
  def to_dict(self) -> dict:
    """Return a JSON‑serialisable dict representing the graph."""
    nodes = [
      {
        "id": n,
        "label": data.get("label", ""),
        "stage": data.get("stage").value if data.get("stage") else None,
        "gates_passed": [g.value for g in data.get("gates_passed", set())],
        "meta": data.get("meta", {}),
      } for n, data in self._g.nodes(data=True)
    ]
    edges = [{
      "src": u,
      "rel": k,
      "dst": v,
    } for u, v, k in self._g.edges(keys=True)]
    return {"nodes": nodes, "edges": edges}

  @classmethod
  def from_dict(cls, payload: dict) -> "OntologyGraph":
    """Rebuild an OntologyGraph from a *payload* produced by :py:meth:`to_dict`."""
    g = cls()
    for n in payload.get("nodes", []):
      stage = Stage(n["stage"]) if "stage" in n else None
      gates_passed = set(Gate(g) for g in n.get("gates_passed", []))
      node = Node(n["id"], n["label"], stage, gates_passed, n.get("meta", {}))
      g.add_node(node)
    for e in payload.get("edges", []):
      g.add_edge(e["src"], e["rel"], e["dst"])
    return g

# Public module surface ---------------------------------------------------- #
__all__ = [
  "Node",
  "Edge",
  "OntologyGraph",
]
