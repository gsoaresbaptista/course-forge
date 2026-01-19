"""Shared utility functions for course-forge."""

import re


def to_roman(num: int) -> str:
    """Convert integer to Roman numeral."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    for i, v in enumerate(val):
        while num >= v:
            roman_num += syms[i]
            num -= v
    return roman_num


def strip_leading_number(name: str) -> str:
    """Remove leading numbers and separators, preserving original capitalization."""
    cleaned = re.sub(r"^[\d]+[-_.\s]*", "", name)
    return cleaned.replace("-", " ").replace("_", " ") if cleaned else name
