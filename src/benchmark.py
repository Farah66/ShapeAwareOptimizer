from pathlib import Path
import csv

from query_parser import QueryParser
from shex_analyzer import ShExAnalyzer
from constraint_extractor import ConstraintExtractor
from rule_selector import RuleSelector
from query_rewriter import QueryRewriter
from executor import Executor


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

    return "Unclassified benchmark query."


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

    original_output = executor.execute(original_query)
    optimized_output = executor.execute(optimized_query)

    original_time = original_output["runtime"]
    optimized_time = optimized_output["runtime"]

    if original_time > 0:
        gain = ((original_time - optimized_time) / original_time) * 100
    else:
        gain = 0.0

    equivalent = executor.are_equivalent(original_output, optimized_output)

    applied_rules = [
        rule["rule"]
        for rule in selected_rules
    ]

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
    }


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

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
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
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nCSV result saved to: {CSV_FILE}")


if __name__ == "__main__":
    main()