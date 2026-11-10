"""Dashboard shutdown must not claim a human pressed Stop."""

import threading
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize("user_stopped", [False, True])
def test_shutdown_retains_system_issuer_and_preserves_an_existing_user_stop(monkeypatch, user_stopped):
    from tui_gateway import server
    from run_agent import AIAgent
    from agent.interrupt_control import interrupted_during_api_call_reason
    from tools.interrupt import set_interrupt

    agent = object.__new__(AIAgent)
    agent._interrupt_requested = False
    agent._interrupt_message = None
    agent._tool_interrupt_reason = None
    agent._hard_interrupt_requested = threading.Event()
    agent._execution_thread_id = None
    agent._interrupt_thread_signal_pending = False
    agent._active_children = []
    agent._active_children_lock = threading.Lock()
    agent.quiet_mode = True
    session = {"agent": agent, "session_key": "shutdown-test", "running": True,
               "history_lock": threading.RLock(), "_run_thread": threading.current_thread()}
    hook = MagicMock()
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", hook)
    monkeypatch.setattr(server, "_sessions", {"s": session})
    monkeypatch.setattr(server, "_clear_pending", lambda *a: None)
    monkeypatch.setattr("tools.environments.base.kill_live_foreground_processes", lambda **kw: None)
    try:
        if user_stopped:
            agent.hard_interrupt()
        server._stop_turns_before_exit(budget_s=0)
        expected = "interrupted_during_api_call" + ("" if user_stopped else "(gateway_shutdown)")
        assert interrupted_during_api_call_reason(agent) == expected
        assert agent._hard_interrupt_requested.is_set()
    finally:
        set_interrupt(False)
