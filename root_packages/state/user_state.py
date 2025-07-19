from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from root_packages.api import UserPreferences, Place


@dataclass
class ConversationMessage:
    role: str  # 'user' или 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class UserSession:
    user_id: int
    preferences: UserPreferences = field(default_factory=UserPreferences)
    conversation_history: List[ConversationMessage] = field(default_factory=list)
    current_location: Optional[Dict[str, float]] = None
    last_search_results: List[Place] = field(default_factory=list)
    state: str = "initial"  # initial, collecting_preferences, searching, refining
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class UserStateManager:
    def __init__(self):
        self.sessions: Dict[int, UserSession] = {}

    def get_or_create_session(self, user_id: int) -> UserSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id=user_id)
        return self.sessions[user_id]

    def update_session(self, user_id: int, **kwargs) -> None:
        session = self.get_or_create_session(user_id)
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        session.updated_at = datetime.now()

    def add_message(self, user_id: int, role: str, content: str) -> None:
        session = self.get_or_create_session(user_id)
        message = ConversationMessage(role=role, content=content)
        session.conversation_history.append(message)
        session.updated_at = datetime.now()

    def get_conversation_history(self, user_id: int, limit: Optional[int] = None) -> List[Dict]:
        session = self.get_or_create_session(user_id)
        history = session.conversation_history
        
        if limit:
            history = history[-limit:]
            
        return [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]

    def update_preferences(self, user_id: int, preferences: UserPreferences) -> None:
        session = self.get_or_create_session(user_id)
        session.preferences = preferences
        session.updated_at = datetime.now()

    def set_location(self, user_id: int, latitude: float, longitude: float) -> None:
        session = self.get_or_create_session(user_id)
        session.current_location = {"lat": latitude, "lon": longitude}
        session.updated_at = datetime.now()

    def update_search_results(self, user_id: int, places: List[Place]) -> None:
        session = self.get_or_create_session(user_id)
        session.last_search_results = places
        session.updated_at = datetime.now()

    def clear_session(self, user_id: int) -> None:
        if user_id in self.sessions:
            del self.sessions[user_id]

    def get_session_state(self, user_id: int) -> str:
        session = self.get_or_create_session(user_id)
        return session.state

    def set_session_state(self, user_id: int, state: str) -> None:
        session = self.get_or_create_session(user_id)
        session.state = state
        session.updated_at = datetime.now()


# Глобальный менеджер состояний
state_manager = UserStateManager() 