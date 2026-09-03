import importlib
import os

import pytest


@pytest.fixture
def analytics_module(tmp_path, monkeypatch):
    """
    Reload app.analytics with ANALYTICS_DB_PATH pointed at a throwaway temp
    file, so each test gets a clean, isolated SQLite DB instead of sharing
    state with other tests or the real analytics.db.
    """
    db_path = tmp_path / "test_analytics.db"
    monkeypatch.setenv("ANALYTICS_DB_PATH", str(db_path))

    import app.analytics as analytics
    importlib.reload(analytics)  # pick up the new ANALYTICS_DB_PATH
    analytics.init_db()
    yield analytics


def test_empty_stats(analytics_module):
    stats = analytics_module.get_stats()
    assert stats["total_views"] == 0
    assert stats["total_decodes"] == 0
    assert stats["success_rate"] is None
    assert stats["last_event_at"] is None


def test_page_view_counted(analytics_module):
    analytics_module.record_event("page_view")
    analytics_module.record_event("page_view")
    stats = analytics_module.get_stats()
    assert stats["total_views"] == 2
    assert stats["total_decodes"] == 0


def test_decode_events_aggregate_by_layer_and_source(analytics_module):
    analytics_module.record_event("gui_decode", layer="NAS", success=True)
    analytics_module.record_event("gui_decode", layer="RRC", success=True)
    analytics_module.record_event("gui_decode", layer="NAS", success=False)
    analytics_module.record_event("api_decode", layer="NAS", success=True)

    stats = analytics_module.get_stats()
    assert stats["total_decodes"] == 4
    assert stats["decodes_by_layer"] == {"NAS": 3, "RRC": 1}
    assert stats["decodes_by_source"] == {"gui_decode": 3, "api_decode": 1}
    assert stats["success_count"] == 3
    assert stats["error_count"] == 1
    assert stats["success_rate"] == pytest.approx(0.75)


def test_last_event_at_is_set_after_recording(analytics_module):
    assert analytics_module.get_stats()["last_event_at"] is None
    analytics_module.record_event("page_view")
    assert analytics_module.get_stats()["last_event_at"] is not None


def test_reset_db_clears_events(analytics_module):
    analytics_module.record_event("page_view")
    assert analytics_module.get_stats()["total_views"] == 1
    analytics_module.reset_db()
    assert analytics_module.get_stats()["total_views"] == 0


def test_db_file_created_on_disk(analytics_module):
    analytics_module.record_event("page_view")
    assert os.path.exists(analytics_module.DB_PATH)
