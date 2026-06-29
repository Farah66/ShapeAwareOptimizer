from pathlib import Path
import csv
import statistics

from query_parser import QueryParser
from shex_analyzer import ShExAnalyzer
from constraint_extractor import ConstraintExtractor
from rule_selector import RuleSelector
from query_rewriter import QueryRewriter
from executor import Executor

import pandas as pd
import matplotlib.pyplot as plt


WARMUP_RUNS = 2
MEASURE_RUNS = 10

QUERY_DIR = Path("../queries")
SCHEMA_FILE = Path("../schemas/person.shex")
RESULTS_DIR = Path("../results")
RESULTS_DIR.mkdir(exist_ok=True)

CSV_FILE = RESULTS_DIR / "benchmark_results.csv"

ENDPOINT = "http://localhost:3030/test/query"


def classify_query(query_name):
    if query_name == "q1_orcid_type_injection.rq":
        return "Supported case: ORCID predicate allows Person type injection."
    if query_name == "q2_already_typed.rq":
        return "No-op case: query already contains rdf:type."
    if query_name == "q3_label_no_rewrite.rq":
        return "No-op case: label query does not match a supported rule."
    if query_name == "q4_optional_label.rq":
        return "Future case: OPTIONAL query shape."
    if query_name == "q5_publication_creator.rq":
        return "Future case: publication relation query."
    if query_name == "q6_authorship_relates.rq":
        return "Future case: authorship relation query."
    if query_name == "q7_redundant_pattern.rq":
        return "Supported case if redundant pattern removal is implemented."
    if query_name == "q8_filter_pushdown.rq":
        return "Future case unless filter pushdown is implemented."
    if query_name == "q8_union_person_publication.rq":
        return "Future case: UNION query shape."
    if query_name == "q9_optional_simplification.rq":
        return "Future case: OPTIONAL simplification."
    if query_name == "q10_filter_person_name.rq":
        return "Supported if ORCID type injection applies; FILTER is preserved."
    if query_name == "q11_publication_year_filter.rq":
        return "Future case: publication filter query."
    if query_name == "q12_nested_optional.rq":
        return "Future case: nested OPTIONAL."
    if query_name == "q13_multiple_joins.rq":
        return "Future case unless join reordering is implemented."
    if query_name == "q14_duplicate_patterns.rq":
        return "Supported if syntactic duplicate-pattern removal is implemented."
    if query_name == "q15_broad_person_query.rq":
        return "No-op case: broad person query without safe type-injection predicate."
    if query_name == "person_query.rq":
        return "Baseline person query."
    if query_name == "person_detail_query.rq":
        return "Entity-heavy person detail query."

    return "Unclassified benchmark query."


def stable_execute(executor, query):
    for _ in range(WARMUP_RUNS):
        executor.execute(query)

    runtimes = []
    last_output = None

    for _ in range(MEASURE_RUNS):
        output = executor.execute(query)
        runtimes.append(output["runtime"])
        last_output = output

    median_runtime = statistics.median(runtimes)

    last_output["runtime"] = median_runtime
    last_output["all_runtimes"] = runtimes

    return last_output


def run_single_query(query_file, shex_shapes, executor):
    query_name = query_file.name

    with open(query_file, "r", encoding="utf-8") as f:
        original_query = f.read()

    parser = QueryParser(str(query_file))
    parsed_query = parser.parse()

    constraint_extractor = ConstraintExtractor(parsed_query, shex_shapes)
    constraint_mappings = constraint_extractor.extract()

    rule_selector = RuleSelector(
        parsed_query,
        constraint_mappings,
        query_name,
        executor
    )

    selected_rules, decision_reason = rule_selector.select_rules_with_reason()

    rewriter = QueryRewriter(
        parsed_query,
        constraint_mappings,
        selected_rules
    )

    optimized_query = rewriter.generate_query()

    original_output = stable_execute(executor, original_query)
    optimized_output = stable_execute(executor, optimized_query)

    original_time = original_output["runtime"]
    optimized_time = optimized_output["runtime"]

    if original_time > 0:
        gain = ((original_time - optimized_time) / original_time) * 100
    else:
        gain = 0.0

    equivalent = executor.are_equivalent(original_output, optimized_output)

    applied_rules = [rule["rule"] for rule in selected_rules]

    return {
        "query": query_name,
        "rules": ", ".join(applied_rules) if applied_rules else "None",
        "original_time": original_time,
        "optimized_time": optimized_time,
        "gain_percent": gain,
        "equivalent": equivalent,
        "classification": classify_query(query_name),
        "decision_reason": decision_reason,
        "optimized_query": optimized_query,
        "original_runtimes": original_output.get("all_runtimes", []),
        "optimized_runtimes": optimized_output.get("all_runtimes", []),
    }


def save_results_to_csv(results):
    fieldnames = [
        "query",
        "rules",
        "original_time",
        "optimized_time",
        "gain_percent",
        "equivalent",
        "classification",
        "decision_reason",
        "optimized_query",
        "original_runtimes",
        "optimized_runtimes",
    ]

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def shorten_query_name(query_name):
    name = query_name.replace(".rq", "")

    replacements = {
        "person_detail_query": "Person Detail",
        "person_query": "Person",
        "q1_orcid_type_injection": "Q1",
        "q2_already_typed": "Q2",
        "q3_label_no_rewrite": "Q3",
        "q4_optional_label": "Q4",
        "q5_publication_creator": "Q5",
        "q6_authorship_relates": "Q6",
        "q7_redundant_pattern": "Q7",
        "q8_filter_pushdown": "Q8",
        "q8_union_person_publication": "Q8-UNION",
        "q9_optional_simplification": "Q9",
        "q10_filter_person_name": "Q10",
        "q11_publication_year_filter": "Q11",
        "q12_nested_optional": "Q12",
        "q13_multiple_joins": "Q13",
        "q14_duplicate_patterns": "Q14",
        "q15_broad_person_query": "Q15",
    }

    return replacements.get(name, name)


def generate_graphs():
    df = pd.read_csv(CSV_FILE)

    query_labels = [shorten_query_name(q) for q in df["query"]]
    x = range(len(df))

    # --------------------------------------------------
    # Graph 1: Original vs Optimized Runtime - Line Chart
    # --------------------------------------------------
    plt.figure(figsize=(14, 6))

    plt.plot(
        x,
        df["original_time"],
        marker="o",
        linewidth=2,
        label="Original Query"
    )

    plt.plot(
        x,
        df["optimized_time"],
        marker="o",
        linewidth=2,
        label="Optimized Query"
    )

    plt.title("Original vs Optimized Query Execution Time")
    plt.xlabel("Benchmark Queries")
    plt.ylabel("Execution Time (seconds)")
    plt.xticks(x, query_labels, rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()

    plt.savefig(RESULTS_DIR / "execution_time_comparison_line.png", dpi=300)
    plt.close()

    # --------------------------------------------------
    # Graph 2: Performance Gain - Line Chart
    # --------------------------------------------------
    plt.figure(figsize=(14, 6))

    plt.plot(
        x,
        df["gain_percent"],
        marker="o",
        linewidth=2
    )

    plt.axhline(0, linewidth=1)
    plt.title("Performance Gain After Query Rewriting")
    plt.xlabel("Benchmark Queries")
    plt.ylabel("Gain (%)")
    plt.xticks(x, query_labels, rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    plt.savefig(RESULTS_DIR / "gain_percentage_line.png", dpi=300)
    plt.close()

    # --------------------------------------------------
    # Graph 3: Original vs Optimized Runtime - Grouped Bar
    # --------------------------------------------------
    width = 0.35

    plt.figure(figsize=(14, 6))

    plt.bar(
        [i - width / 2 for i in x],
        df["original_time"],
        width=width,
        label="Original Query"
    )

    plt.bar(
        [i + width / 2 for i in x],
        df["optimized_time"],
        width=width,
        label="Optimized Query"
    )

    plt.title("Original vs Optimized Query Runtime")
    plt.xlabel("Benchmark Queries")
    plt.ylabel("Execution Time (seconds)")
    plt.xticks(x, query_labels, rotation=45, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()

    plt.savefig(RESULTS_DIR / "execution_time_comparison_bar.png", dpi=300)
    plt.close()

    print("\nGraphs saved to:")
    print(RESULTS_DIR / "execution_time_comparison_line.png")
    print(RESULTS_DIR / "gain_percentage_line.png")
    print(RESULTS_DIR / "execution_time_comparison_bar.png")


def main():
    query_files = sorted(QUERY_DIR.glob("*.rq"))

    if not query_files:
        print("No query files found in ../queries")
        return

    shex_analyzer = ShExAnalyzer(str(SCHEMA_FILE))
    shex_shapes = shex_analyzer.analyze()

    executor = Executor(ENDPOINT)
    results = []

    print("\n=== Evaluation Summary ===\n")
    print(f"Warm-up runs: {WARMUP_RUNS}")
    print(f"Measured runs: {MEASURE_RUNS}")
    print("Reported runtime: median\n")

    print(
        f"{'Query':35} {'Rule':60} {'Orig(s)':10} {'Opt(s)':10} "
        f"{'Gain %':10} {'Eq.':6}"
    )
    print("-" * 145)

    for query_file in query_files:
        result = run_single_query(query_file, shex_shapes, executor)
        results.append(result)

        print(
            f"{result['query']:35} "
            f"{result['rules']:60} "
            f"{result['original_time']:<10.6f} "
            f"{result['optimized_time']:<10.6f} "
            f"{result['gain_percent']:<10.2f} "
            f"{str(result['equivalent']):6}"
        )

    save_results_to_csv(results)

    print(f"\nCSV result saved to: {CSV_FILE}")

    generate_graphs()


if __name__ == "__main__":
    main()