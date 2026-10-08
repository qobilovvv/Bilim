from fastapi import Header


async def get_accept_language(accept_language: str | None = Header(None)) -> str:
    candidates = []
    for index, item in enumerate((accept_language or "").split(",")):
        parts = item.strip().split(";")
        lang = parts[0].strip().split("-")[0].lower()
        quality = 1.0
        for parameter in parts[1:]:
            if parameter.strip().startswith("q="):
                try:
                    quality = float(parameter.strip()[2:])
                except ValueError:
                    quality = 0
        if lang in {"uz", "ru", "en"} and 0 < quality <= 1:
            candidates.append((-quality, index, lang))
    return min(candidates)[2] if candidates else "uz"
