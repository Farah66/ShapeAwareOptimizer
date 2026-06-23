from executor import QueryExecutor

executor = QueryExecutor(
    "http://localhost:3030/test/query"
)

selectivity = executor.estimate_type_selectivity(
    "http://xmlns.com/foaf/0.1/Person"
)

print("\nSelectivity of foaf:Person:")
print(selectivity)