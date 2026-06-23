from executor import QueryExecutor

query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?person
WHERE {
    ?person rdf:type foaf:Person .
}
LIMIT 10
"""

executor = QueryExecutor(
    "http://localhost:3030/test/query"
    
)

result = executor.execute(query)

print("\nRuntime:")
print(result["runtime"])

print("\nResults:")
print(result["results"])

