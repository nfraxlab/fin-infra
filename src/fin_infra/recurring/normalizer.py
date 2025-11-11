"""
Merchant name normalization for recurring transaction detection.

This module provides:
- Text normalization pipeline (lowercase, remove special chars, etc.)
- Fuzzy matching for merchant name variants
- Canonical merchant name grouping
"""

from __future__ import annotations

import re
from functools import lru_cache

try:
    from rapidfuzz import fuzz, process

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


def normalize_merchant(raw_name: str) -> str:
    """
    Normalize merchant name for grouping.

    Pipeline:
    1. Lowercase: "NETFLIX.COM" → "netflix.com"
    2. Remove domain suffixes: "netflix.com" → "netflix"
    3. Remove special chars: "netflix*subscription" → "netflix subscription"
    4. Remove store/transaction numbers: "starbucks #12345" → "starbucks"
    5. Remove legal entities: "netflix inc" → "netflix"
    6. Strip whitespace: "  netflix  " → "netflix"

    Args:
        raw_name: Original merchant name

    Returns:
        Normalized merchant name

    Examples:
        >>> normalize_merchant("NETFLIX.COM")
        'netflix'
        >>> normalize_merchant("Starbucks #12345")
        'starbucks'
        >>> normalize_merchant("Shell Oil Inc")
        'shell oil'
    """
    # 1. Lowercase
    name = raw_name.lower()

    # 2. Remove common domain suffixes
    name = re.sub(r"\.(com|net|org|io|co|us|uk)$", "", name)
    name = re.sub(r"\.(com|net|org|io|co|us|uk)[/\s]", " ", name)

    # 3. Remove special characters (keep alphanumeric and spaces)
    name = re.sub(r"[^a-z0-9\s]", " ", name)

    # 4. Remove store/transaction numbers (4+ digits with optional #)
    name = re.sub(r"\s*#?\d{4,}", "", name)

    # 5. Remove legal entity suffixes
    name = re.sub(r"\b(inc|llc|corp|ltd|co|limited|corporation)\b", "", name)

    # 6. Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()

    return name


@lru_cache(maxsize=1024)
def _cached_normalize(merchant: str) -> str:
    """Cached version of normalize_merchant for performance."""
    return normalize_merchant(merchant)


class FuzzyMatcher:
    """
    Fuzzy matching for merchant name variants.

    Uses RapidFuzz for efficient fuzzy string matching with token_sort_ratio scorer
    (handles word order differences and partial matches).
    """

    def __init__(self, similarity_threshold: float = 80.0):
        """
        Initialize fuzzy matcher.

        Args:
            similarity_threshold: Minimum similarity score (0-100) to consider a match
                                  Default 80.0 (80% similarity)

        Raises:
            ImportError: If rapidfuzz is not installed
        """
        if not RAPIDFUZZ_AVAILABLE:
            raise ImportError(
                "rapidfuzz is required for fuzzy matching. " "Install with: pip install rapidfuzz"
            )
        self.similarity_threshold = similarity_threshold

    def find_similar(
        self, target: str, candidates: list[str], limit: int = 5
    ) -> list[tuple[str, float]]:
        """
        Find similar merchant names using fuzzy matching.

        Args:
            target: Target merchant name to match
            candidates: List of candidate merchant names
            limit: Maximum number of matches to return

        Returns:
            List of (merchant_name, similarity_score) tuples, sorted by similarity
            Only returns matches above similarity_threshold

        Examples:
            >>> matcher = FuzzyMatcher(threshold=80)
            >>> matcher.find_similar("netflix", ["netflix.com", "netflix inc", "hulu"])
            [('netflix.com', 89.0), ('netflix inc', 87.0)]
        """
        if not candidates:
            return []

        # Normalize target
        norm_target = normalize_merchant(target)

        # Use RapidFuzz process.extract for efficient matching
        matches = process.extract(
            norm_target,
            [normalize_merchant(c) for c in candidates],
            scorer=fuzz.token_sort_ratio,
            limit=limit,
        )

        # Filter by threshold and return original names
        results = []
        for match_text, score, idx in matches:
            if score >= self.similarity_threshold:
                results.append((candidates[idx], float(score)))

        return results

    def is_same_merchant(self, name1: str, name2: str) -> bool:
        """
        Check if two merchant names represent the same merchant.

        Uses fuzzy similarity with token_sort_ratio scorer.

        Args:
            name1: First merchant name
            name2: Second merchant name

        Returns:
            True if similarity >= threshold

        Examples:
            >>> matcher = FuzzyMatcher(threshold=80)
            >>> matcher.is_same_merchant("NETFLIX.COM", "Netflix Inc")
            True
            >>> matcher.is_same_merchant("Netflix", "Hulu")
            False
        """
        norm1 = normalize_merchant(name1)
        norm2 = normalize_merchant(name2)

        similarity = fuzz.token_sort_ratio(norm1, norm2)
        return similarity >= self.similarity_threshold

    def group_merchants(self, merchants: list[str]) -> dict[str, list[str]]:
        """
        Group similar merchant names together.

        Returns a dictionary mapping canonical (first) merchant name to list of variants.

        Args:
            merchants: List of merchant names to group

        Returns:
            Dict of {canonical_name: [variant1, variant2, ...]}

        Examples:
            >>> matcher = FuzzyMatcher(threshold=85)
            >>> matcher.group_merchants([
            ...     "NETFLIX.COM",
            ...     "Netflix Inc",
            ...     "Netflix",
            ...     "Hulu",
            ... ])
            {'NETFLIX.COM': ['NETFLIX.COM', 'Netflix Inc', 'Netflix'], 'Hulu': ['Hulu']}
        """
        if not merchants:
            return {}

        groups: dict[str, list[str]] = {}
        processed = set()

        for merchant in merchants:
            if merchant in processed:
                continue

            # Find all similar merchants
            similar = self.find_similar(merchant, merchants, limit=len(merchants))

            # Use first merchant as canonical name
            canonical = merchant
            group = [merchant]
            processed.add(merchant)

            # Add similar merchants to group
            for similar_merchant, _ in similar:
                if similar_merchant != merchant and similar_merchant not in processed:
                    group.append(similar_merchant)
                    processed.add(similar_merchant)

            groups[canonical] = group

        return groups


# Pre-defined merchant groupings (common subscriptions)
# Can be extended by users
# Note: All values should be in normalized form (lowercase, no special chars)
# Use these exact strings after normalize_merchant() is applied
KNOWN_MERCHANT_GROUPS = {
    "netflix": [
        "netflix",
        "nflx",
        "nflx subscription",
        "netflix subscription",
        "netflix streaming",
    ],
    "spotify": ["spotify", "spotify usa", "spotify premium", "spotifyusa"],
    "amazon": [
        "amazon",
        "amazon prime",
        "amzn mktp us",
        "prime video",
        "amazon web services",
        "aws",
    ],
    "starbucks": ["starbucks", "starbucks coffee", "sbux"],
    "apple": ["apple", "apple bill", "apple itunes", "apple music", "app store"],
    "google": ["google", "google youtube", "google storage", "google one", "googleplay"],
    "hulu": ["hulu", "hulu subscription", "hulu plus"],
    "disney": ["disney", "disneyplus", "disney plus"],
    "hbo": ["hbo", "hbo max", "hbomax", "hbo now"],
}


def get_canonical_merchant(raw_name: str, groups: dict[str, list[str]] | None = None) -> str:
    """
    Get canonical merchant name from known groups or normalization.

    Args:
        raw_name: Original merchant name
        groups: Optional custom merchant groups (default: KNOWN_MERCHANT_GROUPS)

    Returns:
        Canonical merchant name (lowercase normalized)

    Examples:
        >>> get_canonical_merchant("NETFLIX.COM")
        'netflix'
        >>> get_canonical_merchant("Starbucks #12345")
        'starbucks'
    """
    groups = groups or KNOWN_MERCHANT_GROUPS
    normalized = normalize_merchant(raw_name)

    # Check known groups
    for canonical, variants in groups.items():
        if normalized == canonical:
            return canonical
        # Check if normalized name contains any variant
        for variant in variants:
            if variant in normalized or normalized in variant:
                return canonical
            # Fuzzy match if RapidFuzz available
            if RAPIDFUZZ_AVAILABLE and fuzz.ratio(normalized, variant) > 85:
                return canonical

    # No match, return normalized name
    return normalized


def is_generic_merchant(merchant: str) -> bool:
    """
    Check if merchant name is generic (likely false positive).

    Generic merchants include: ATM withdrawals, generic "payment", "purchase", etc.

    Args:
        merchant: Merchant name (normalized or raw)

    Returns:
        True if merchant is generic

    Examples:
        >>> is_generic_merchant("atm withdrawal")
        True
        >>> is_generic_merchant("netflix")
        False
    """
    generic_keywords = [
        "atm",
        "withdrawal",
        "payment",
        "purchase",
        "debit",
        "transfer",
        "deposit",
        "cash",
        "check",
        "fee",
        "charge",
    ]

    merchant_lower = merchant.lower()
    return any(keyword in merchant_lower for keyword in generic_keywords)
