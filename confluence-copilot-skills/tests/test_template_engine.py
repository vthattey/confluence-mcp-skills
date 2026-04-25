"""Unit tests for the template engine — no network calls required."""

import json
import os
import tempfile

import pytest

from src.confluence_skills.template_engine import Template, TemplateRegistry


SAMPLE_VARIABLES = [
    {"name": "title",       "description": "Page title",   "required": True,  "default": ""},
    {"name": "author",      "description": "Author name",  "required": False, "default": "Unknown"},
    {"name": "api_version", "description": "API version",  "required": False, "default": "1.0"},
]

SAMPLE_BODY = "<h1>{{ title }}</h1><p>Author: {{ author }}</p><p>v{{ api_version }}</p>"


# ---------------------------------------------------------------------------
# Template.render
# ---------------------------------------------------------------------------

class TestTemplateRender:
    def _make_template(self) -> Template:
        return Template(
            name="test",
            description="Test template",
            variables=SAMPLE_VARIABLES,
            body=SAMPLE_BODY,
        )

    def test_render_all_variables_supplied(self):
        t = self._make_template()
        result = t.render({"title": "My Page", "author": "Jane", "api_version": "2.0"})
        assert "<h1>My Page</h1>" in result
        assert "Author: Jane" in result
        assert "v2.0" in result

    def test_render_uses_default_for_missing_optional(self):
        t = self._make_template()
        result = t.render({"title": "My Page"})
        assert "Author: Unknown" in result
        assert "v1.0" in result

    def test_render_raises_on_missing_required(self):
        from jinja2 import UndefinedError
        t = self._make_template()
        # Override body to use a truly undeclared variable to trigger StrictUndefined
        t.body = "<h1>{{ title }}</h1>{{ undefined_var }}"
        with pytest.raises(UndefinedError):
            t.render({"title": "X"})


# ---------------------------------------------------------------------------
# Template.missing_required
# ---------------------------------------------------------------------------

class TestMissingRequired:
    def test_returns_empty_when_all_required_present(self):
        t = Template(name="t", description="", variables=SAMPLE_VARIABLES, body="")
        assert t.missing_required({"title": "X"}) == []

    def test_returns_missing_required_names(self):
        t = Template(name="t", description="", variables=SAMPLE_VARIABLES, body="")
        assert t.missing_required({}) == ["title"]


# ---------------------------------------------------------------------------
# Template save / load round-trip
# ---------------------------------------------------------------------------

class TestTemplatePersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        t = Template(
            name="Round Trip Test",
            description="desc",
            variables=SAMPLE_VARIABLES,
            body=SAMPLE_BODY,
            source_page_id="12345",
        )
        path = t.save(str(tmp_path))
        assert os.path.isfile(path)

        loaded = Template.load(path)
        assert loaded.name == t.name
        assert loaded.description == t.description
        assert loaded.body == t.body
        assert loaded.source_page_id == "12345"
        assert len(loaded.variables) == len(t.variables)

    def test_save_sanitises_file_name(self, tmp_path):
        t = Template(name="My Template: V2!", description="", variables=[], body="x")
        path = t.save(str(tmp_path))
        assert "my_template__v2_" in path


# ---------------------------------------------------------------------------
# TemplateRegistry
# ---------------------------------------------------------------------------

class TestTemplateRegistry:
    def test_list_returns_saved_template_names(self, tmp_path):
        t1 = Template(name="alpha", description="", variables=[], body="a")
        t2 = Template(name="beta",  description="", variables=[], body="b")
        t1.save(str(tmp_path))
        t2.save(str(tmp_path))

        registry = TemplateRegistry(str(tmp_path))
        names = registry.list()
        assert "alpha" in names
        assert "beta" in names

    def test_get_returns_correct_template(self, tmp_path):
        t = Template(name="gamma", description="d", variables=[], body="g")
        t.save(str(tmp_path))

        registry = TemplateRegistry(str(tmp_path))
        loaded = registry.get("gamma")
        assert loaded.body == "g"

    def test_get_raises_for_unknown_template(self, tmp_path):
        registry = TemplateRegistry(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            registry.get("nonexistent")
