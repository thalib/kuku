def mark_active_nav(groups: list[dict], page_url: str) -> list[dict]:
    groups = [dict(g) for g in groups]
    for g in groups:
        original = list(g.get("links", []))
        g["links"] = [{**lk, "active": lk["url"] == page_url} for lk in original]
    return groups
