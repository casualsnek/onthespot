from librespot.core import Session
import os
from src.onthespot.expections import InvalidCredentialException


def get_librespot_session(username: str, pass_phrase: str, saved_login_directory: str, uuid: str) -> \
        list[Session, bool, bool, str]:
    """
    Returns a librespot session instance from a saved session or creates a saved session from username and password
    :param username: Spotify username
    :param pass_phrase:
    :param saved_login_directory: Directory where session will be saved
    :param uuid: UUID for the account
    :return:
    """
    session_json_path = os.path.join(saved_login_directory, f"ots_login_{uuid}.json")
    os.makedirs(os.path.dirname(session_json_path), exist_ok=True)
    try:
        session = None
        config = Session.Configuration.Builder().set_stored_credential_file(session_json_path).build()
        if os.path.isfile(session_json_path):
            session = Session.Builder(conf=config).stored_file(session_json_path).create()
        else:
            if username.strip() == '' or pass_phrase == '':
                raise InvalidCredentialException('Either username or password was not supplied')
            session = Session.Builder(conf=config).user_pass(username, pass_phrase).create()
        return [session, True if session.get_user_attribute("type") == "premium" else False, True, uuid]
    except (RuntimeError, Session.SpotifyAuthenticationException):
        raise InvalidCredentialException('Invalid credentials. Session expired or invalid username / password')
