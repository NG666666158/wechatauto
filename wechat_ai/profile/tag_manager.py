from __future__ import annotations


class TagManager:
    @staticmethod
    def normalize(tags: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            value = tag.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized
