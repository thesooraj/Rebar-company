"""
face_recognition_module.py — The Rebar Company
Handles face enrollment and recognition for clock-in/out.
"""

import os
import pickle
import numpy as np
from datetime import datetime

import database as db

# ── Where face data is stored ──────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FACE_DATA_DIR = os.path.join(BASE_DIR, "database", "faces")
os.makedirs(FACE_DATA_DIR, exist_ok=True)


def _import_libs():
    """Lazy import so app still starts if libs aren't installed."""
    try:
        import face_recognition
        import cv2
        return face_recognition, cv2
    except ImportError as e:
        raise RuntimeError(f"Face recognition libraries not installed: {e}")


# ────────────────────────────────────────────────────────────
# ENROLMENT
# ────────────────────────────────────────────────────────────

def enroll_face_from_image(employee_id: int, image_bytes: bytes, label: str = "") -> bool:
    """
    Enrol a face from an uploaded image (JPEG/PNG bytes).
    Returns True on success, raises RuntimeError on failure.
    """
    face_recognition, cv2 = _import_libs()
    import numpy as np

    # Decode image
    nparr  = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise RuntimeError("Could not decode image.")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # Find faces
    encodings = face_recognition.face_encodings(img_rgb)
    if not encodings:
        raise RuntimeError("No face detected in the image. Please try again with a clearer photo.")
    if len(encodings) > 1:
        raise RuntimeError("Multiple faces detected. Please upload a photo with only one person.")

    encoding = encodings[0]
    blob     = pickle.dumps(encoding)

    # Save to DB
    conn = db.get_connection()
    try:
        conn.execute(
            """INSERT INTO face_encodings (employee_id, encoding_blob, label)
               VALUES (?, ?, ?)""",
            (employee_id, blob, label)
        )
        conn.execute(
            "UPDATE employees SET face_enrolled = 1 WHERE id = ?",
            (employee_id,)
        )
        conn.commit()
    finally:
        conn.close()

    return True


def get_all_encodings() -> list:
    """
    Return list of (employee_id, encoding) tuples for all enrolled faces.
    """
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """SELECT fe.employee_id, fe.encoding_blob, e.full_name, e.employee_code
               FROM face_encodings fe
               JOIN employees e ON e.id = fe.employee_id
               WHERE e.is_active = 1"""
        ).fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        try:
            encoding = pickle.loads(row["encoding_blob"])
            result.append({
                "employee_id":   row["employee_id"],
                "full_name":     row["full_name"],
                "employee_code": row["employee_code"],
                "encoding":      encoding,
            })
        except Exception:
            continue
    return result


# ────────────────────────────────────────────────────────────
# RECOGNITION
# ────────────────────────────────────────────────────────────

def recognize_face_from_image(image_bytes: bytes, threshold: float = 0.50):
    """
    Identify a face from image bytes.
    Returns matched employee dict or None.
    """
    face_recognition, cv2 = _import_libs()

    nparr   = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return None, "Could not decode image."

    img_rgb   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(img_rgb)

    if not encodings:
        return None, "No face detected."

    unknown_encoding = encodings[0]
    known            = get_all_encodings()

    if not known:
        return None, "No faces enrolled yet."

    known_encodings = [k["encoding"] for k in known]
    distances       = face_recognition.face_distance(known_encodings, unknown_encoding)
    best_idx        = int(np.argmin(distances))
    best_distance   = distances[best_idx]

    if best_distance <= threshold:
        return known[best_idx], None
    else:
        return None, f"Face not recognised (confidence: {1 - best_distance:.0%})"


def delete_face_encodings(employee_id: int) -> None:
    """Remove all face encodings for an employee."""
    conn = db.get_connection()
    try:
        conn.execute(
            "DELETE FROM face_encodings WHERE employee_id = ?", (employee_id,)
        )
        conn.execute(
            "UPDATE employees SET face_enrolled = 0 WHERE id = ?", (employee_id,)
        )
        conn.commit()
    finally:
        conn.close()