"""
Smoke‑tests for the Ontology CLI entry‑point (``python -m Ontology``).

The test drives the `graph` sub‑commands in sequence:

1. `init`  – create an empty JSON graph file.
2. `info`  – verify 0 nodes / 0 edges.
3. `add-node` – add two nodes.
4. `add-edge` – link them with `decomposes_to`.
5. `info`  – verify 2 nodes / 1 edge.
6. `dump`  – parse JSON and assert structure.

Run with::

    pytest -q tests/ontology/test_ontology_cli.py
"""
from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path
import copy

def _run_cli(tmp_dir: Path, *args: str, input_text: str = "") -> str:
  """
    Invoke the ontology CLI with *args* (after ``python -m Ontology``).

    On non‑zero exit it raises AssertionError printing stdout/stderr.
    Returns decoded stdout otherwise.
    """
  cmd = [sys.executable, "-m", "Ontology", *args]
  proc = subprocess.run(
    cmd,
    input=input_text.encode(),
    cwd=tmp_dir,
    env=os.environ,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )
  if proc.returncode != 0:
    raise AssertionError(f"CLI failed ({proc.returncode}):\n"
                         f"STDOUT:\n{proc.stdout.decode()}\n"
                         f"STDERR:\n{proc.stderr.decode()}")
  return proc.stdout.decode()

def test_cli_roundtrip(tmp_path: Path) -> None:
  """End‑to‑end check of all graph sub‑commands."""
  graph_a = tmp_path / "graph_a.json"
  graph_b = tmp_path / "graph_b.json"

  # helper to swap
  def swap():
    nonlocal graph_a, graph_b
    graph_a, graph_b = graph_b, graph_a

  # 1. init
  _run_cli(tmp_path, "graph", "init", str(graph_a))
  assert graph_a.exists()

  # 2. info (empty)
  out = _run_cli(tmp_path, "graph", "info", f"-f={graph_a.as_posix()}", "-")
  assert "nodes=0" in out and "edges=0" in out

  # 3. add nodes
  _run_cli(
    tmp_path,
    "graph",
    "add-node",
    f"-f={graph_a.as_posix()}",
    graph_b.as_posix(),
    "root",
    "Root",
    "problem",
  )
  swap()
  _run_cli(
    tmp_path,
    "graph",
    "add-node",
    f"-f={graph_a.as_posix()}",
    graph_b.as_posix(),
    "child",
    "Child",
    "concept",
  )
  swap()

  # 4. add edge
  _run_cli(
    tmp_path,
    "graph",
    "add-edge",
    f"-f={graph_a.as_posix()}",
    graph_b.as_posix(),
    "root",
    "decomposes_to",
    "child",
  )
  swap()

  # 5. info (populated)
  out = _run_cli(tmp_path, "graph", "info", f"-f={graph_a.as_posix()}", "-")
  assert "nodes=2" in out and "edges=1" in out

  # 6. dump & validate
  dumped = _run_cli(tmp_path, "graph", "dump", f"-f={graph_a.as_posix()}", "-")
  data = json.loads(dumped)
  assert {n["id"] for n in data["nodes"]} == {"root", "child"}
  assert data["edges"] == [{"src": "root", "rel": "decomposes_to", "dst": "child"}]
