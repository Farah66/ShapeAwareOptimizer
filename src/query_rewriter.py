from query_parser import QueryParser
from shex_analyzer import ShExAnalyzer
from constraint_extractor import ConstraintExtractor
from rule_selector import RuleSelector


class QueryRewriter:
    def __init__(self, parsed_query, constraint_mappings, selected_rules):
        self.parsed_query = parsed_query
        self.constraint_mappings = constraint_mappings
        self.selected_rules = selected_rules

    def normalize_predicate(self, predicate):
        if predicate == "a":
            return "rdf:type"
        return predicate

    def has_rule(self, rule_name):
        return any(
            rule["rule"] == rule_name
            for rule in self.selected_rules
        )

    def remove_duplicate_triples(self, triples):
        unique_triples = []

        for triple in triples:
            if triple not in unique_triples:
                unique_triples.append(triple)

        return unique_triples

    def reorder_joins(self, triples):
        def triple_score(triple):
            s, p, o = triple
            p = self.normalize_predicate(p)

            if p == "rdf:type":
                return 0

            if p == "vivo:orcidId":
                return 1

            if not o.startswith("?"):
                return 2

            return 3

        return sorted(triples, key=triple_score)

    def rewrite_required_triples(self):
        rewritten_triples = []

        for mapping in self.constraint_mappings:
            s, p, o = mapping["triple_pattern"]
            p = self.normalize_predicate(p)
            rewritten_triples.append((s, p, o))

        for rule in self.selected_rules:
            if rule["rule"] == "TYPE_CONSTRAINT_INJECTION":
                injected_triple = (
                    rule["subject"],
                    "rdf:type",
                    rule["type"]
                )

                if injected_triple not in rewritten_triples:
                    rewritten_triples.insert(0, injected_triple)

        rewritten_triples = self.remove_duplicate_triples(
            rewritten_triples
        )

        if self.has_rule("JOIN_REORDERING"):
            rewritten_triples = self.reorder_joins(
                rewritten_triples
            )

        return rewritten_triples

    def rewrite_optional_triples(self):
        optional_triples = self.parsed_query.get("optional_triples", [])

        normalized_optional_triples = [
            (s, self.normalize_predicate(p), o)
            for s, p, o in optional_triples
        ]

        normalized_optional_triples = self.remove_duplicate_triples(
            normalized_optional_triples
        )

        if self.has_rule("OPTIONAL_SIMPLIFICATION"):
            required_triples = self.rewrite_required_triples()

            normalized_optional_triples = [
                triple
                for triple in normalized_optional_triples
                if triple not in required_triples
            ]

        return normalized_optional_triples

    def rewrite_filters(self):
        return self.parsed_query.get("filters", [])

    def generate_query(self):
        required_triples = self.rewrite_required_triples()
        optional_triples = self.rewrite_optional_triples()
        filters = self.rewrite_filters()

        variables = " ".join(self.parsed_query["variables"])

        query = (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX foaf: <http://xmlns.com/foaf/0.1/>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX vivo: <http://vivoweb.org/ontology/core#>\n"
            "PREFIX kdsf: <http://kerndatensatz-forschung.de/owl/Basis#>\n"
            "PREFIX dc: <http://purl.org/dc/elements/1.1/>\n\n"
        )

        query += f"SELECT {variables}\nWHERE {{\n"

        for s, p, o in required_triples:
            query += f"    {s} {p} {o} .\n"

        if self.has_rule("FILTER_PUSHDOWN"):
            for filter_expr in filters:
                query += f"    {filter_expr}\n"

        for s, p, o in optional_triples:
            query += "    OPTIONAL {\n"
            query += f"        {s} {p} {o} .\n"
            query += "    }\n"

        if not self.has_rule("FILTER_PUSHDOWN"):
            for filter_expr in filters:
                query += f"    {filter_expr}\n"

        query += "}\n"

        return query


if __name__ == "__main__":
    parser = QueryParser("../queries/q9_optional_simplification.rq")
    parsed_query = parser.parse()

    analyzer = ShExAnalyzer("../schemas/person.shex")
    shex_constraints = analyzer.analyze()

    extractor = ConstraintExtractor(parsed_query, shex_constraints)
    mappings = extractor.extract()

    selector = RuleSelector(parsed_query, mappings)
    selected_rules = selector.select_rules()

    rewriter = QueryRewriter(parsed_query, mappings, selected_rules)
    optimized_query = rewriter.generate_query()

    print("\n=== Selected Rules ===\n")
    print(selected_rules)

    print("\n=== Rewritten Query ===\n")
    print(optimized_query)