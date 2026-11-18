import re
import base64
import logging
from typing import Dict, Any, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ProctorService:
    """Service for OpenCV face verification, object detection, and proctoring metrics."""

    _face_cascade = None
    _upperbody_cascade = None

    @classmethod
    def _get_cascades(cls):
        """Lazy load OpenCV Haar Cascades."""
        if cls._face_cascade is None:
            face_xml = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cls._face_cascade = cv2.CascadeClassifier(face_xml)
        if cls._upperbody_cascade is None:
            body_xml = cv2.data.haarcascades + "haarcascade_upperbody.xml"
            cls._upperbody_cascade = cv2.CascadeClassifier(body_xml)
        return cls._face_cascade, cls._upperbody_cascade

    @classmethod
    def analyze_frame_base64(cls, base64_image_data: str) -> Dict[str, Any]:
        """
        Analyze a webcam frame sent as base64 string.
        Detects face presence, multiple people, and bounding boxes.
        """
        try:
            # Strip data URL prefix if present (e.g. data:image/jpeg;base64,...)
            if "," in base64_image_data:
                base64_image_data = base64_image_data.split(",", 1)[1]

            image_bytes = base64.b64decode(base64_image_data)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is None:
                return {
                    "valid": False,
                    "error": "Failed to decode camera frame",
                    "faces_count": 0,
                    "status": "error",
                    "violation": False,
                }

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Histogram equalization for reliable detection in low lighting
            gray = cv2.equalizeHist(gray)

            face_cascade, body_cascade = cls._get_cascades()

            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(40, 40),
            )

            face_count = len(faces)
            boxes = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in faces]

            # Detect secondary bodies if multiple persons might be partially visible
            body_count = 0
            if body_cascade and not body_cascade.empty():
                bodies = body_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60))
                body_count = len(bodies)

            violation = False
            event_type = "verified"
            message = "Face verified. Normal single candidate frame."
            severity = "low"
            penalty = 0.0

            if face_count == 0:
                violation = True
                event_type = "no_face"
                message = "Candidate face not detected in frame. Please stay centered facing the camera."
                severity = "medium"
                penalty = 0.2
            elif face_count > 1:
                violation = True
                event_type = "multiple_faces"
                message = f"Integrity Violation: Multiple people ({face_count} faces) detected in camera frame!"
                severity = "high"
                penalty = 0.5
            elif body_count > 2 and face_count == 1:
                violation = True
                event_type = "unauthorized_person"
                message = "Potential second person detected nearby in camera background."
                severity = "medium"
                penalty = 0.3

            return {
                "valid": True,
                "faces_count": face_count,
                "bodies_count": body_count,
                "boxes": boxes,
                "status": event_type,
                "violation": violation,
                "severity": severity,
                "message": message,
                "penalty": penalty,
            }

        except Exception as e:
            logger.error(f"Error in OpenCV frame analysis: {e}", exc_info=True)
            return {
                "valid": False,
                "error": str(e),
                "faces_count": 0,
                "status": "error",
                "violation": False,
            }

    @classmethod
    def compute_integrity_and_penalties(cls, interview) -> Dict[str, Any]:
        """
        Calculate total proctoring deductions, tab-switch penalties, and net adjusted score.
        Formula:
          - Each tab switch deducts 0.5 points (5% reduction).
          - Other high-severity violations (multiple persons, cell phone) deduct 0.5 points each.
          - Final score = max(0.0, raw_score - total_penalties)
          - Integrity score = max(0.0, 100.0 - total_penalties * 10)
        """
        tab_switches = interview.tab_switch_count or 0
        violations = interview.violations_count or 0

        # Tab switch penalty: 0.5 points (5%) per switch
        tab_penalty = round(tab_switches * 0.5, 1)

        # Other violations penalty (e.g. multiple persons, prohibited devices)
        violation_penalty = round(violations * 0.5, 1)

        total_penalty = round(tab_penalty + violation_penalty, 1)

        raw_score = interview.raw_score if interview.raw_score else interview.total_score
        net_score = max(0.0, round(raw_score - total_penalty, 1))
        net_percentage = round(net_score * 10.0, 1)

        # Integrity rating percentage (starts at 100%)
        integrity_score = max(0.0, round(100.0 - (total_penalty * 10.0), 1))

        return {
            "raw_score": raw_score,
            "tab_switches": tab_switches,
            "violations": violations,
            "tab_penalty": tab_penalty,
            "violation_penalty": violation_penalty,
            "total_penalty": total_penalty,
            "penalty_percentage": round(total_penalty * 10.0, 1),
            "net_score": net_score,
            "net_percentage": net_percentage,
            "integrity_score": integrity_score,
        }
