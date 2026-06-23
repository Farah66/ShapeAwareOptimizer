import time
from SPARQLWrapper import SPARQLWrapper, JSON


class QueryExecutor:
    def __init__(self, endpoint="http://localhost:3030/ds/query"):
        self.endpoint = endpoint

    def execute(self, query):
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)

        start = time.perf_counter()
        results = sparql.query().convert()
        end = time.perf_counter()

        runtime = end - start

        return {
            "runtime": runtime,
            "results": results,
            "normalized_results": self.normalize_results(results)
        }

    def normalize_results(self, results):
        """
        Converts SPARQL JSON results into hashable rows.
        This allows semantic equivalence checking with set().
        """

        bindings = results.get("results", {}).get("bindings", [])

        normalized = []

        for binding in bindings:
            row = tuple(
                sorted(
                    (
                        variable,
                        value_data.get("value", "")
                    )
                    for variable, value_data in binding.items()
                )
            )

            normalized.append(row)

        return normalized

    def are_equivalent(self, original_output, optimized_output):
        """
        Compares original and optimized query results.
        """

        original_results = original_output.get("normalized_results", [])
        optimized_results = optimized_output.get("normalized_results", [])

        return set(original_results) == set(optimized_results)

    def estimate_type_selectivity(self, class_uri):
        total_query = """
        SELECT (COUNT(DISTINCT ?s) AS ?count)
        WHERE {
            ?s a ?type .
        }
        """

        class_query = f"""
        SELECT (COUNT(DISTINCT ?s) AS ?count)
        WHERE {{
            ?s a <{class_uri}> .
        }}
        """

        total_result = self.execute(total_query)
        class_result = self.execute(class_query)

        total = int(
            total_result["results"]["results"]["bindings"][0]["count"]["value"]
        )

        typed = int(
            class_result["results"]["results"]["bindings"][0]["count"]["value"]
        )

        if total == 0:
            return 1.0

        return typed / total


# Compatibility alias
# This allows benchmark.py to use either:
# from executor import QueryExecutor
# or:
# from executor import Executor
class Executor(QueryExecutor):
    pass