# Shape-Aware Optimizer

## Overview

This repository contains the prototype implementation developed for the Master's thesis:

**Shape-Aware Optimization of Read Queries in Semantic Web Applications**

The goal of this work is to improve SPARQL query performance by exploiting structural knowledge contained in Shape Expressions (ShEx) schemas. The optimizer analyzes SPARQL queries, extracts schema constraints, selects applicable optimization rules, rewrites the query, and evaluates the impact on execution performance while preserving semantic equivalence.

---

## Architecture

The prototype consists of the following components:

### Query Parser

Parses SPARQL queries and extracts:

* Variables
* Triple patterns
* OPTIONAL patterns
* FILTER expressions

### ShEx Analyzer

Parses ShEx schemas and extracts shape constraints that can be used during optimization.

### Constraint Extractor

Maps SPARQL triple patterns to corresponding ShEx constraints.

### Rule Selector

Determines which optimization rules can be safely applied based on:

* Query structure
* ShEx constraints
* Predicate semantics
* Type selectivity estimation

### Query Rewriter

Generates optimized SPARQL queries using the selected optimization rules.

### Query Executor

Executes original and optimized queries against Apache Jena Fuseki and collects runtime statistics.

### Benchmark Framework

Evaluates optimization effectiveness using a benchmark suite of SPARQL queries and verifies semantic equivalence.

---

## Implemented Optimization Rules

### TYPE_CONSTRAINT_INJECTION

Injects explicit type constraints when a predicate is known to belong to a specific entity type.

Example:

```sparql
?person vivo:orcidId ?orcid .
```

becomes

```sparql
?person rdf:type foaf:Person .
?person vivo:orcidId ?orcid .
```

---

### JOIN_REORDERING

Reorders triple patterns to place more selective patterns earlier in query execution.

---

### FILTER_PUSHDOWN

Moves FILTER expressions closer to the relevant triple patterns to reduce intermediate results.

---

### OPTIONAL_SIMPLIFICATION

Removes redundant OPTIONAL patterns that are already guaranteed by required patterns.

---

### REDUNDANT_PATTERN_REMOVAL

Detects and removes duplicate triple patterns.

---

## Project Structure

```text
ShapeAwareOptimizer/
│
├── data/
│
├── queries/
│   ├── q1_orcid_type_injection.rq
│   ├── q2_already_typed.rq
│   ├── ...
│
├── results/
│   └── benchmark_results.csv
│
├── schemas/
│   └── person.shex
│
├── src/
│   ├── benchmark.py
│   ├── query_parser.py
│   ├── shex_analyzer.py
│   ├── constraint_extractor.py
│   ├── rule_selector.py
│   ├── query_rewriter.py
│   └── executor.py
│
├── requirements.txt
└── README.md
```

---

## Benchmark Evaluation

The benchmark framework evaluates:

* Original query runtime
* Optimized query runtime
* Performance gain/loss
* Semantic equivalence
* Applied optimization rules
* Rule-selection reasoning

Results are exported to:

```text
results/benchmark_results.csv
```

---

## Experimental Environment

* Python 3.x
* Apache Jena Fuseki
* RDF Dataset: person-57811.ttl
* ShEx Schema: person.shex
* SPARQLWrapper

Fuseki endpoint:

```text
http://localhost:3030/test/query
```

---

## Running the Benchmark

Navigate to:

```bash
cd src
```

Run:

```bash
python benchmark.py
```

Output:

* Console benchmark summary
* CSV benchmark report

---

## Current Status

Implemented:

* Query parsing
* ShEx analysis
* Constraint extraction
* Rule selection
* Query rewriting
* Benchmark evaluation
* Semantic equivalence validation

Future work:

* Additional ShEx-guided rewrite rules
* Cost-based rule selection
* Cardinality-aware optimization
* UNION optimization
* Advanced OPTIONAL rewriting

---

## Thesis Context

This prototype was developed as part of research on:

**Shape-Aware Optimization of Read Queries in Semantic Web Applications**

The research investigates how schema knowledge captured in ShEx can be used to guide safe and effective SPARQL query rewriting for improved query performance while preserving result correctness.

