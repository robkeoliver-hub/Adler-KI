"""Volatile demo-session lifecycle; no accounts, I/O or portal authentication.

Callers own the registry lock. Revocation clears the existing history list so
in-flight references cannot repopulate a detached session without revalidation.
Python does not guarantee physical zeroing of freed request/string memory.
"""


def discard_session(registry, sid):
    state = registry.pop(sid, None)
    if state is not None:
        state['history'].clear()
        state['revoked'] = True


def expire_sessions(registry, now):
    for sid, state in list(registry.items()):
        if state['expires'] <= now:
            discard_session(registry, sid)


def is_current_session(registry, sid, state, principal, now):
    if registry.get(sid) is not state:
        return False
    if (state.get('revoked') or state['expires'] <= now
            or state['principal'] != principal):
        discard_session(registry, sid)
        return False
    return True


def cleanup_delay(registry, now):
    """Sleep no longer than the next expiry (30 s only if no nearer deadline)."""
    return max(0, min([30] + [state['expires'] - now for state in registry.values()]))
