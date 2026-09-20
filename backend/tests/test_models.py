"""Tests that all enum values match the spec."""
from app.models import MediaType, MediaCategory, CartoonSubtype, WatchedStatus, MediaSource


def test_media_type_values():
    assert {e.value for e in MediaType} == {"movie", "cartoon", "series"}


def test_media_category_values():
    assert {e.value for e in MediaCategory} == {
        "kids_series", "adult_series", "family_movie", "adult_movie", "cartoon"
    }


def test_cartoon_subtype_values():
    assert {e.value for e in CartoonSubtype} == {
        "disney", "pixar", "soviet", "russian", "other"
    }


def test_watched_status_values():
    assert {e.value for e in WatchedStatus} == {
        "not_watched", "watching", "watched"
    }


def test_media_source_values():
    assert {e.value for e in MediaSource} == {
        "telegram_text", "telegram_screenshot", "web_ui"
    }
