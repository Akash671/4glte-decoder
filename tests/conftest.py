"""
Shared pytest fixtures.

Sets ANALYTICS_DB_PATH to a temp file before any test module imports
app.analytics or app.api, so running the test suite never writes into the
project's real analytics.db.
"""

import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="pytest_analytics_")
os.environ["ANALYTICS_DB_PATH"] = os.path.join(_tmp_dir, "test_session_analytics.db")
