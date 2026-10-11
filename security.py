import sqlparse

def validate_read_only_sql(sql_query: str) -> str:
    """
    Enterprise Security Guardrail:
    Parses the generated SQL query using AST tokenization to guarantee 
    it is strictly a read-only SELECT operation.
    """
    if not sql_query or not isinstance(sql_query, str):
        raise ValueError("Invalid query format received.")

    cleaned_query = sql_query.strip()
    parsed_statements = sqlparse.parse(cleaned_query)
    
    if not parsed_statements:
        raise ValueError("Empty SQL query detected.")
    
    if len(parsed_statements) > 1:
        raise SecurityError("Multiple SQL statements detected. Execution blocked.")

    stmt = parsed_statements[0]
    query_type = stmt.get_type().upper()

    # Enterprise Rule: Only SELECT queries are permitted at the database level
    if query_type != "SELECT":
        raise SecurityError(
            f"Security Violation: Generated query type '{query_type}' is unauthorized. "
            "Only read-only SELECT statements are allowed."
        )

    return cleaned_query

class SecurityError(Exception):
    """Custom exception raised when SQL security guardrails are breached."""
    pass