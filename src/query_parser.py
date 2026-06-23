import re


class QueryParser:

    def __init__(self, query_path):
        self.query_path = query_path

    def extract_triples(self, text):
        triple_pattern = r"(\?\w+)\s+([^\s]+)\s+([^\s]+)\s*\."
        return re.findall(triple_pattern, text)

    def extract_filters(self, text):
        filters = []

        for line in text.splitlines():
            line = line.strip()

            if line.startswith("FILTER"):
                filters.append(line)

        return filters

    def remove_filter_lines(self, text):
        return "\n".join(
            line for line in text.splitlines()
            if not line.strip().startswith("FILTER")
        )

    def parse(self):
        with open(self.query_path, "r", encoding="utf-8") as f:
            query = f.read()

        variables = re.findall(r"\?[\w]+", query.split("WHERE")[0])

        triples = []
        optional_triples = []
        filters = []

        where_match = re.search(
            r"WHERE\s*\{(.*)\}",
            query,
            re.DOTALL
        )

        if where_match:
            body = where_match.group(1)

            filters.extend(self.extract_filters(body))

            optional_blocks = re.findall(
                r"OPTIONAL\s*\{(.*?)\}",
                body,
                re.DOTALL
            )

            for block in optional_blocks:
                optional_triples.extend(self.extract_triples(block))

            body_without_optional = re.sub(
                r"OPTIONAL\s*\{.*?\}",
                "",
                body,
                flags=re.DOTALL
            )

            body_without_filters = self.remove_filter_lines(
                body_without_optional
            )

            triples.extend(self.extract_triples(body_without_filters))

        return {
            "variables": variables,
            "triples": triples,
            "optional_triples": optional_triples,
            "filters": filters
        }


if __name__ == "__main__":

    parser = QueryParser("../queries/q8_filter_pushdown.rq")
    result = parser.parse()

    print("\n=== Parsed Query ===\n")

    print("Variables:")
    print(result["variables"])

    print("\nRequired Triple Patterns:")
    for triple in result["triples"]:
        print(triple)

    print("\nOptional Triple Patterns:")
    for triple in result["optional_triples"]:
        print(triple)

    print("\nFilters:")
    for filter_expr in result["filters"]:
        print(filter_expr)