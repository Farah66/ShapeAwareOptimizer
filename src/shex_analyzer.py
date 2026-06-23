import re


class ShExAnalyzer:

    def __init__(self, schema_path):
        self.schema_path = schema_path

    def get_type_from_value_set(self, value):
        match = re.search(r"\[([^\]]+)\]", value)
        if match:
            return match.group(1).strip()
        return None

    def analyze(self):
        with open(self.schema_path, "r", encoding="utf-8") as f:
            content = f.read()

        shapes = []

        shape_pattern = r"<(\w+)>\s*\{(.*?)\}"
        shape_matches = re.findall(shape_pattern, content, re.DOTALL)

        for shape_name, shape_body in shape_matches:
            constraints = []

            lines = shape_body.split(";")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()

                if len(parts) < 2:
                    continue

                predicate = parts[0]
                value = parts[1]
                cardinality = parts[2] if len(parts) > 2 else "1"

                expected_type = None

                if predicate in ["rdf:type", "a"]:
                    expected_type = self.get_type_from_value_set(line)

                constraints.append({
                    "shape": shape_name,
                    "predicate": predicate,
                    "value": value,
                    "cardinality": cardinality,
                    "expected_type": expected_type
                })

            shapes.append({
                "shape": shape_name,
                "constraints": constraints
            })

        return shapes


if __name__ == "__main__":
    analyzer = ShExAnalyzer("../schemas/person.shex")
    shapes = analyzer.analyze()

    print("\n=== Extracted ShEx Shapes ===\n")

    for shape in shapes:
        print("Shape:", shape["shape"])
        for constraint in shape["constraints"]:
            print(" ", constraint)