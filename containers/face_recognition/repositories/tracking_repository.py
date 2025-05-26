from ship.core.base_repository import BaseRepository
from typing import Dict

class TrackingRepository(BaseRepository):
    """Repository for tracking-related operations"""

    def save_frame_data(self, frame_id: int, track_id: int, face_data: Dict,
                        is_visible: bool, person_type: str) -> bool:
        """Save frame tracking data"""
        return True