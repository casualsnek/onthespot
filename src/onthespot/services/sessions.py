# TODO: Replace "Any" Type with more specific types
import os
import time
from threading import Lock
from typing import Any, Callable, Optional, Dict, Set, List
from .configuration import ConfigurationService
from otslib.core.user import SpotifyUser


class SessionsService:
    """
    A service for managing and distributing sessions in a round-robin fashion.
    Provides thread-safe session access and rotation capabilities.
    """

    class SessionDistributor:
        """
        A context manager that distributes sessions in a round-robin fashion,
        ensuring thread-safe access and proper session cleanup.
        """

        _last_used_index = -1

        def __init__(self, sessions: Dict[str, Any], in_use: Set[str], lock: Lock):
            """
            Initialize the SessionDistributor.

            Args:
                sessions: Dictionary of all available sessions (uuid -> session info)
                in_use: Set of UUIDs currently in use (shared with SessionsService)
                lock: Threading lock for synchronization
            """
            self.__sessions = sessions
            self.__in_use = in_use
            self.__lock = lock
            self.__current_uuid: Optional[str] = None

        def __enter__(self) -> SpotifyUser:
            """
            Context manager entry point. Blocks until an available session is found.

            Returns:
                The next available session object

            Note:
                This method will block indefinitely until a session becomes available.
            """
            session_list = list(self.__sessions.keys())
            if not session_list:
                raise RuntimeError("No sessions available")

            attempts = 0
            max_attempts = len(session_list) * 2

            while attempts < max_attempts:
                with self.__lock:
                    current_list = list(self.__sessions.keys())
                    if not current_list:
                        raise RuntimeError("No sessions available")

                    # Update class-level index
                    SessionsService.SessionDistributor._last_used_index = (
                                                                  SessionsService.SessionDistributor._last_used_index + 1) % len(
                        current_list)
                    current_uuid = current_list[SessionsService.SessionDistributor._last_used_index]

                    if current_uuid not in self.__in_use:
                        self.__current_uuid = current_uuid
                        self.__in_use.add(current_uuid)
                        return self.__sessions[current_uuid]["session"]

                attempts += 1
                time.sleep(0.1)

            raise RuntimeError("Could not acquire a session after multiple attempts")

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            """Context manager exit point. Releases the current session."""
            if self.__current_uuid:
                with self.__lock:
                    self.__in_use.discard(self.__current_uuid)
                self.__current_uuid = None

    def __init__(self, config_service: ConfigurationService):
        """
        Initialize the SessionsService.

        Args:
            config_service: Configuration service instance for managing preferences
        """
        self.__sessions: Dict[str, Any] = {}
        self.__on_added_handlers: List[Callable] = []
        self.__on_removed_handlers: List[Callable] = []
        self.__parsing_account_uuid = config_service.get("preferred_parsing_account")
        self.__config = config_service
        self.__sessions_in_use: Set[str] = set()
        self.__sessions_lock = Lock()  # For thread-safe operations

        # Register config change handler for preferred account
        self.__config.on_change(
            "preferred_parsing_account",
            lambda key, old_value, new_value: self.set_parsing_session(new_value))

    def add_session(self, account_uuid: str, username: str, session_path: str) -> None:
        """
        Add a new session to the service.

        Args:
            account_uuid: Unique identifier for the account
            username: Display name for the account
            session_path: Path to the session file

        Raises:
            FileNotFoundError: If the session file doesn't exist
        """
        if not os.path.isfile(session_path):
            raise FileNotFoundError(
                f"Session file '{session_path}' not found for user "
                f"'{username}' with uuid '{account_uuid}'"
            )

        loaded_session: Any = None  # TODO: Implement actual session loading

        with self.__sessions_lock:
            self.__sessions[account_uuid] = {
                "username": username,
                "session_path": session_path,
                "session": loaded_session
            }

        # Notify handlers
        for handler in self.__on_added_handlers:
            handler(account_uuid, username, session_path, loaded_session)

    def remove_session(self, account_uuid: str) -> None:
        """
        Remove a session from the service.

        Args:
            account_uuid: UUID of the session to remove

        Note:
            Will block if the session is currently in use.
        """
        # TODO: Use lmttfy and throw it into another thread
        # Wait until session is no longer in use
        while True:
            with self.__sessions_lock:
                if account_uuid not in self.__sessions_in_use:
                    if account_uuid in self.__sessions:
                        del self.__sessions[account_uuid]
                    break
            time.sleep(0.1)

        # Notify handlers
        for handler in self.__on_removed_handlers:
            handler(account_uuid)

    def rotated_session(self) -> SessionDistributor:
        """
        Get a session distributor for round-robin session access.

        Returns:
            A SessionDistributor context manager

        Example:
            with session_service.rotated_session() as session:
                session.do_something()
        """
        while len(self.__sessions_in_use) >= self.__config.get("max_concurrent_sessions_use"):
            time.sleep(0.2)
        return self.SessionDistributor(
            self.__sessions,
            self.__sessions_in_use,
            self.__sessions_lock
        )

    def save_to_config(self) -> None:
        """Save all sessions to the configuration service."""
        account_config_part = {}
        for account_uuid in self.__sessions:
            account_config_part[account_uuid] = {
                "username": self.__sessions[account_uuid]["username"],
                "session_path": self.__sessions[account_uuid]["session_path"]
            }

        with self.__sessions_lock:
            self.__config.set("accounts", account_config_part)
            self.__config.save()

    def set_parsing_session(self, account_uuid: str) -> None:
        """
        Set the preferred session for parsing operations.

        Args:
            account_uuid: UUID of the preferred session

        Raises:
            RuntimeError: If the session doesn't exist
        """
        with self.__sessions_lock:
            if account_uuid not in self.__sessions:
                raise RuntimeError(
                    f"Saved session by uuid '{account_uuid}' not found"
                )
            self.__parsing_account_uuid = account_uuid

    def get_parsing_session(self) -> SpotifyUser:
        """
        Get the preferred parsing session.

        SpotifyUser Instance of Parsing Account

        Raises:
            RuntimeError: If no sessions are available
        """
        if not self.__sessions:
            raise RuntimeError("No saved sessions loaded")
        if self.__parsing_account_uuid is None or self.__parsing_account_uuid not in self.__sessions:
            # Return first available session if preferred isn't set
            return self.__sessions[next(iter(self.__sessions))]["session"]
        return self.__sessions[self.__parsing_account_uuid]["session"]

    def on_add(self, handler: Callable) -> None:
        """Register a handler for session addition events."""
        if handler not in self.__on_added_handlers:
            self.__on_added_handlers.append(handler)

    def on_remove(self, handler: Callable) -> None:
        """Register a handler for session removal events."""
        if handler not in self.__on_removed_handlers:
            self.__on_removed_handlers.append(handler)

    def remove_on_add(self, handler: Callable) -> None:
        """Unregister a session addition handler."""
        if handler in self.__on_added_handlers:
            self.__on_added_handlers.remove(handler)

    def remove_on_remove(self, handler: Callable) -> None:
        """Unregister a session removal handler."""
        if handler in self.__on_removed_handlers:
            self.__on_removed_handlers.remove(handler)