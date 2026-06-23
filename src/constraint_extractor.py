from query_parser import QueryParser
from shex_analyzer import ShExAnalyzer


class ConstraintExtractor:

    def __init__(self, parsed_query, shex_shapes):
        self.parsed_query = parsed_query
        self.shex_shapes = shex_shapes

    def normalize_predicate(self, predicate):
        if predicate == "a":
            return "rdf:type"
        return predicate

    def get_all_constraints(self):
        all_constraints = []

        for shape in self.shex_shapes:
            for constraint in shape["constraints"]:
                all_constraints.append(constraint)

        return all_constraints

    def extract(self):
        mappings = []

        all_constraints = self.get_all_constraints()

        triples = self.parsed_query.get("triples", [])

        for triple in triples:
            s, p, o = triple
            normalized_predicate = self.normalize_predicate(p)

            matched_constraint = None

            for constraint in all_constraints:
                constraint_predicate = self.normalize_predicate(
                    constraint["predicate"]
                )

                if constraint_predicate == normalized_predicate:
                    matched_constraint = constraint
                    break

            mappings.append({
                "triple_pattern": triple,
                "matched_constraint": matched_constraint
            })

        return mappings


if __name__ == "__main__":
    parser = QueryParser("../queries/q5_publication_creator.rq")
    parsed_query = parser.parse()

    analyzer = ShExAnalyzer("../schemas/person.shex")
    shex_shapes = analyzer.analyze()

    extractor = ConstraintExtractor(parsed_query, shex_shapes)
    mappings = extractor.extract()

    print("\n=== Constraint Mappings ===\n")

    for mapping in mappings:
        print(mapping)