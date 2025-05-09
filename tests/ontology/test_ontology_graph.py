"""
Unit tests for OntologyGraph proof‑of‑concept.

Run with::

    pytest -q tests/ontology
"""

import pytest

from src.Ontology.graph import OntologyGraph, Node, Edge

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def make_basic_graph() -> OntologyGraph:
  """Root ➜ A ➜ B hierarchy used by several tests."""
  g = OntologyGraph()
  g.add_node(Node("root", "Root problem", "problem"))
  g.add_node(Node("A", "Concept A"))
  g.add_node(Node("B", "Primitive B", "primitive"))
  g.add_edge("root", "decomposes_to", "A")
  g.add_edge("A", "decomposes_to", "B")
  return g

# --------------------------------------------------------------------------- #
# Construction & mutation                                                     #
# --------------------------------------------------------------------------- #

def test_add_node_and_len():
  g = OntologyGraph()
  g.add_node(Node("x", "Foo"))
  assert len(g) == 1
  assert "x" in g

def test_duplicate_node_raises():
  g = OntologyGraph()
  g.add_node(Node("dup", "Foo"))
  with pytest.raises(ValueError):
    g.add_node(Node("dup", "Bar"))

def test_add_edge_and_query():
  g = OntologyGraph()
  g.add_node(Node("s", "Source"))
  g.add_node(Node("t", "Target"))
  g.add_edge("s", "decomposes_to", "t")

  edges = g.query(src="s", rel="decomposes_to")
  assert edges == [Edge("s", "decomposes_to", "t")]

def test_decomposes_cycle_rejected():
  g = OntologyGraph()
  g.add_node(Node("X", "X"))
  g.add_node(Node("Y", "Y"))
  g.add_edge("X", "decomposes_to", "Y")
  # Attempting to re‑link Y ➜ X should raise
  with pytest.raises(ValueError):
    g.add_edge("Y", "decomposes_to", "X")

def test_remove_subtree():
  g = make_basic_graph()
  g.remove_subtree("A")
  assert "A" not in g
  assert "B" not in g
  # root remains
  assert "root" in g
  assert len(g) == 1

# --------------------------------------------------------------------------- #
# Search & query                                                              #
# --------------------------------------------------------------------------- #

def test_search_by_label_and_meta():
  g = OntologyGraph()
  g.add_node(Node("n1", "QuickSort", meta={ "algo": "sort"}))
  g.add_node(Node("n2", "Merge Sort"))
  hits = g.search("quick")
  assert hits == ["n1"]
  hits_meta = g.search("sort")
  assert set(hits_meta) == { "n1", "n2"}

def test_query_wildcards():
  g = make_basic_graph()
  all_edges = g.query()
  assert len(all_edges) == 2  # root->A, A->B
  # wildcard src, filter by dst
  to_b = g.query(dst="B")
  assert to_b == [Edge("A", "decomposes_to", "B")]

# --------------------------------------------------------------------------- #
# Traversal                                                                   #
# --------------------------------------------------------------------------- #

def test_walk_dfs_and_bfs():
  g = make_basic_graph()
  dfs_order = list(g.walk("root", order="dfs"))
  bfs_order = list(g.walk("root", order="bfs"))
  # DFS preorder visits parent before children
  assert dfs_order[0] == "root"
  # BFS visits root then its children level‑wise
  assert bfs_order[0] == "root"
  assert set(dfs_order) == set(bfs_order) == { "root", "A", "B"}

def test_to_paths():
  g = make_basic_graph()
  paths = g.to_paths("root")
  assert paths == [["root", "A", "B"]]

# --------------------------------------------------------------------------- #
# Validation helpers                                                          #
# --------------------------------------------------------------------------- #

def test_detect_cycles_false():
  g = make_basic_graph()
  assert g.detect_cycles() is False
