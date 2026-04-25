"""Unit tests for the read_template extraction logic — no network calls."""

import pytest

from src.confluence_skills.read_template import (
    DEFAULT_EXTRACTION_RULES,
    _apply_rules_to_body,
    _replace_pattern,
)


class TestReplacePattern:
    def test_replaces_first_match(self):
        result, was_replaced = _replace_pattern("foo 2026-01-01 bar", r"\d{4}-\d{2}-\d{2}", "{{ date }}")
        assert result == "foo {{ date }} bar"
        assert was_replaced is True

    def test_returns_original_when_no_match(self):
        result, was_replaced = _replace_pattern("no dates here", r"\d{4}-\d{2}-\d{2}", "{{ date }}")
        assert result == "no dates here"
        assert was_replaced is False


class TestApplyRulesToBody:
    BASE_HTML = (
        "<p>Release date: 2026-03-15</p>"
        "<p>Version: v2.1.0</p>"
        "<p>Written by Jane Doe</p>"
    )

    def test_detects_date_placeholder(self):
        body, detected = _apply_rules_to_body(self.BASE_HTML, DEFAULT_EXTRACTION_RULES)
        names = [d["name"] for d in detected]
        assert "date" in names

    def test_detects_version_placeholder(self):
        body, detected = _apply_rules_to_body(self.BASE_HTML, DEFAULT_EXTRACTION_RULES)
        names = [d["name"] for d in detected]
        assert "version" in names

    def test_body_contains_jinja_placeholders(self):
        body, _ = _apply_rules_to_body(self.BASE_HTML, DEFAULT_EXTRACTION_RULES)
        assert "{{ date }}" in body or "{{date}}" in body
        assert "{{ version }}" in body or "{{version}}" in body

    def test_no_detection_when_no_match(self):
        html = "<p>Static content only, no dates or versions.</p>"
        _, detected = _apply_rules_to_body(html, DEFAULT_EXTRACTION_RULES)
        assert detected == []

    def test_custom_rule_applied(self):
        extra_rules = [
            {
                "name": "env",
                "description": "Environment name",
                "pattern": r"\b(production|staging|development)\b",
                "required": False,
                "default": "production",
                "scope": "body",
            }
        ]
        html = "<p>Deployed to production environment.</p>"
        body, detected = _apply_rules_to_body(html, extra_rules)
        names = [d["name"] for d in detected]
        assert "env" in names
        assert "{{ env }}" in body
