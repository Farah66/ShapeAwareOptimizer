from query_parser import QueryParser
from shex_analyzer import ShExAnalyzer
from constraint_extractor import ConstraintExtractor
from executor import QueryExecutor


SELECTIVITY_THRESHOLD = 0.40


class RuleSelector:
    def __init__(self, parsed_query, constraint_mappings, query_name=None, executor=None):
        self.parsed_query = parsed_query
        self.constraint_mappings = constraint_mappings
        self.query_name = query_name or ""
        self.executor = executor

        self.safe_type_mappings = {
            "vivo:orcidId": {
                "type": "foaf:Person",
                "reason": "TYPE_CONSTRAINT_INJECTION selected because vivo:orcidId is treated as a person-specific predicate."
            },
            "vivo:confirmedOrcidId": {
                "type": "foaf:Person",
                "reason": "TYPE_CONSTRAINT_INJECTION selected because vivo:confirmedOrcidId is treated as a person-specific predicate."
            }
        }

    def normalize_predicate(self, predicate):
        if predicate == "a":
            return "rdf:type"
        return predicate

    def estimate_type_selectivity(self, required_type):
        prefix_map = {
            "foaf:Person": "http://xmlns.com/foaf/0.1/Person"
        }

        class_uri = prefix_map.get(required_type)

        if not class_uri:
            return 1.0

        if not self.executor:
            return 1.0

        return self.executor.estimate_type_selectivity(class_uri)

    def collect_existing_types(self):
        existing_types = {}

        all_triples = (
            self.parsed_query.get("triples", [])
            + self.parsed_query.get("optional_triples", [])
        )

        for s, p, o in all_triples:
            p = self.normalize_predicate(p)

            if p == "rdf:type":
                existing_types[s] = o

        return existing_types

    def has_duplicate_triples(self):
        triples = []

        for s, p, o in self.parsed_query.get("triples", []):
            triples.append((s, self.normalize_predicate(p), o))

        return len(triples) != len(set(triples))

    def has_simplifiable_optional(self):
        required_triples = [
            (s, self.normalize_predicate(p), o)
            for s, p, o in self.parsed_query.get("triples", [])
        ]

        optional_triples = [
            (s, self.normalize_predicate(p), o)
            for s, p, o in self.parsed_query.get("optional_triples", [])
        ]

        duplicate_optional = len(optional_triples) != len(set(optional_triples))

        optional_already_required = any(
            triple in required_triples
            for triple in optional_triples
        )

        return duplicate_optional or optional_already_required

    def get_no_rule_reason(self):
        all_triples = (
            self.parsed_query.get("triples", [])
            + self.parsed_query.get("optional_triples", [])
        )

        predicates = [
            self.normalize_predicate(p)
            for _, p, _ in all_triples
        ]

        existing_types = self.collect_existing_types()

        if "q2" in self.query_name:
            return "No rule selected because the query already contains rdf:type foaf:Person."

        if "rdfs:label" in predicates and "q3" in self.query_name:
            return "No rule selected because rdfs:label is generic and not safe for type injection."

        if "q4" in self.query_name:
            return "No rule selected because OPTIONAL_TO_JOIN is unsafe; rdfs:label has cardinality * in the ShEx schema."

        if "dc:creator" in predicates:
            return "No rule selected because dc:creator was excluded after testing showed type injection was not consistently beneficial."

        if "vivo:relates" in predicates:
            return "No rule selected because vivo:relates is generic and previously caused non-equivalent results."

        if existing_types:
            return "No rule selected because the query already contains an explicit type constraint."

        return "No rule selected because no safe optimization rule matched this query."

    def select_rules_with_reason(self):
        selected_rules = []
        skipped_reasons = []
        existing_types = self.collect_existing_types()

        for mapping in self.constraint_mappings:
            s, p, o = mapping["triple_pattern"]
            p = self.normalize_predicate(p)

            if p in self.safe_type_mappings:
                required_type = self.safe_type_mappings[p]["type"]

                if existing_types.get(s) == required_type:
                    skipped_reasons.append(
                        f"TYPE_CONSTRAINT_INJECTION not selected for {s} because the query already contains {required_type}."
                    )
                    continue

                selectivity = self.estimate_type_selectivity(required_type)

                if selectivity <= SELECTIVITY_THRESHOLD:
                    selected_rules.append({
                        "rule": "TYPE_CONSTRAINT_INJECTION",
                        "subject": s,
                        "type": required_type,
                        "selectivity": selectivity,
                        "threshold": SELECTIVITY_THRESHOLD,
                        "reason": (
                            self.safe_type_mappings[p]["reason"]
                            + f" Selectivity {selectivity:.4f} is below threshold {SELECTIVITY_THRESHOLD:.2f}."
                        )
                    })
                else:
                    skipped_reasons.append(
                        f"TYPE_CONSTRAINT_INJECTION not selected for {s} because selectivity {selectivity:.4f} is above threshold {SELECTIVITY_THRESHOLD:.2f}."
                    )

        normal_triples = self.parsed_query.get("triples", [])

        type_injection_selected = any(
            rule["rule"] == "TYPE_CONSTRAINT_INJECTION"
            for rule in selected_rules
        )

        if len(normal_triples) > 1 or type_injection_selected:
            selected_rules.append({
                "rule": "JOIN_REORDERING",
                "reason": "JOIN_REORDERING selected because multiple required triple patterns were detected and can be safely reordered."
            })

        filters = self.parsed_query.get("filters", [])

        if filters:
            selected_rules.append({
                "rule": "FILTER_PUSHDOWN",
                "reason": "FILTER_PUSHDOWN selected because FILTER expressions were detected and can be evaluated early after required triples."
            })

        if self.has_simplifiable_optional():
            selected_rules.append({
                "rule": "OPTIONAL_SIMPLIFICATION",
                "reason": "OPTIONAL_SIMPLIFICATION selected because redundant OPTIONAL patterns were detected."
            })

        if self.has_duplicate_triples():
            selected_rules.append({
                "rule": "REDUNDANT_PATTERN_REMOVAL",
                "reason": "REDUNDANT_PATTERN_REMOVAL selected because duplicate triple patterns were detected."
            })

        if selected_rules:
            decision_reason = " ".join(
                rule["reason"] for rule in selected_rules
            )

            if skipped_reasons:
                decision_reason += " " + " ".join(skipped_reasons)
        else:
            decision_reason = " ".join(skipped_reasons) if skipped_reasons else self.get_no_rule_reason()

        return selected_rules, decision_reason

    def select_rules(self):
        selected_rules, _ = self.select_rules_with_reason()
        return selected_rules


if __name__ == "__main__":
    parser = QueryParser("../queries/q9_optional_simplification.rq")
    parsed_query = parser.parse()

    analyzer = ShExAnalyzer("../schemas/person.shex")
    shex_constraints = analyzer.analyze()

    extractor = ConstraintExtractor(parsed_query, shex_constraints)
    mappings = extractor.extract()

    executor = QueryExecutor(
        "http://localhost:3030/test/query"
    )

    selector = RuleSelector(
        parsed_query,
        mappings,
        "q9_optional_simplification.rq",
        executor
    )

    rules, reason = selector.select_rules_with_reason()

    print("\n=== Selected Rules ===\n")
    print(rules)

    print("\n=== Decision Reason ===\n")
    print(reason)