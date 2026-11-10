"""Subagent/delegate runs stay out of ``search_messages`` unless opted back in.

A list that hides delegate runs (``sessions.show_subagents`` off: the sidebar's
default) must not resurface them through the FTS content lane. Both shapes are
covered: the dedicated ``source='subagent'`` rows and desktop-sourced runs that
only carry the ``_delegate_from`` model_config marker.
"""

from hermes_state import SessionDB


def _seed(db):
    db.create_session("run_subagent", source="subagent")
    db.create_session(
        "run_desktop_delegate", source="desktop",
        model_config={"_delegate_from": "parent_session"},
    )
    db.create_session("human_chat", source="desktop")
    db.append_message("run_subagent", "user", "signature audit findings")
    db.append_message("run_desktop_delegate", "user", "signature audit findings")
    db.append_message("human_chat", "user", "signature audit findings")


def test_search_messages_hides_delegate_runs_by_default(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        _seed(db)
        hits = {m["session_id"] for m in db.search_messages("signature")}
        assert hits == {"human_chat"}

        scoped = {m["session_id"] for m in db.search_messages("signature", source_filter=["desktop"])}
        assert scoped == {"human_chat"}
    finally:
        db.close()


def test_search_messages_include_subagents_readmits_them(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        _seed(db)
        hits = {
            m["session_id"]
            for m in db.search_messages("signature", include_subagents=True)
        }
        assert hits == {"run_subagent", "run_desktop_delegate", "human_chat"}
    finally:
        db.close()
