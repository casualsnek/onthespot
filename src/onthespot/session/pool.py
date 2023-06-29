from ..session.login import get_librespot_session


def fill_pool(pool_list: list, session_part: dict, pg_notify = None):
    total_sessions: int = len(session_part)
    current_count: int = 0
    for account in session_part:
        current_count += 1
        pg_notify(total_sessions, current_count, f'Creating session for ')
        pool_list.append(get_librespot_session())
        pg_notify(total_sessions, current_count, f'Session created for  ')