from fastapi import Header

async def get_accept_language(accept_language: str | None = Header(None)) -> str:
    """
    Dependency to parse Accept-Language header and return the matched language.
    Defaults to 'uz'. Supported: 'uz', 'ru', 'en'.
    Example: 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7' -> 'ru'
    """
    if not accept_language:
        return "uz"
        
    # Standard Accept-Language parsing
    for item in accept_language.replace(" ", "").split(","):
        # Split language code from quality value (e.g. 'uz-UZ;q=0.9' -> 'uz-UZ')
        part = item.split(";")[0]
        # Split locale country code (e.g. 'uz-UZ' -> 'uz')
        lang = part.split("-")[0].lower()
        if lang in {"uz", "ru", "en"}:
            return lang
            
    return "uz"
