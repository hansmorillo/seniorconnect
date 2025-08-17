# security_utils.py
from bleach import clean, linkify
from markdown import markdown

def sanitize_input(input_text, allow_links=False):
    """Sanitize user input to prevent XSS"""
    if not input_text:
        return input_text
        
    # Basic HTML escaping 
    cleaned = clean(
        input_text,
        tags=[],  # No HTML tags allowed by default
        attributes={},
        protocols=[],
        strip=True,
        strip_comments=True
    )
    
    # Optionally allow safe links
    if allow_links:
        cleaned = linkify(cleaned)
        
    return cleaned

def sanitize_markdown(input_text):
    """For content that needs markdown formatting"""
    if not input_text:
        return input_text
        
    # Convert markdown to HTML
    html = markdown(input_text)
    
    # Sanitize the HTML output 
    return clean(
        html,
        tags=['p', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'a'],
        attributes={'a': ['href', 'title', 'target']},
        # styles=[] parameter removed - this was causing the error
        protocols=['http', 'https'],
        strip=True
    )