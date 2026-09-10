def validate_input(query: str, user_id: str) -> str:
    """
    Validate incoming user requests.
    Raises ValueError if input is invalid or obviously suspicious.
    """
    if not query or not query.strip():
        raise ValueError("Input query cannot be empty.")
        
    if not user_id:
        raise ValueError("User identity is required.")
        
    if len(query) > 1000:
        raise ValueError("Input query exceeds maximum length of 1000 characters.")
        
    # Basic prompt injection indicators (primitive defense layer)
    suspicious_phrases = [
        "ignore previous instructions",
        "system prompt",
        "you are a helpful assistant",
        "bypass security"
    ]
    
    query_lower = query.lower()
    for phrase in suspicious_phrases:
        if phrase in query_lower:
            raise ValueError(f"Input rejected due to policy violation (code: INP-SEC-01).")
            
    return query.strip()

