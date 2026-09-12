import math

import cv2
import numpy as np

WHITE = (235, 235, 235)
GRAY = (150, 150, 150)
GREEN = (80, 220, 90)
YELLOW = (80, 220, 230)
ORANGE = (70, 150, 240)
RED = (90, 90, 235)


def _text(img, lines, x, y, scale=0.5, gap=18, color=WHITE, outline=True):
    for i, line in enumerate(lines):
        yy = y + i * gap
        if outline:
            cv2.putText(img, line, (x + 1, yy + 1), cv2.FONT_HERSHEY_SIMPLEX,
                        scale, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(img, line, (x, yy), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, color, 1, cv2.LINE_AA)


def _reticle(img, x, y, r, color, thickness=2):
    c = (int(x), int(y))
    cv2.circle(img, c, r, color, thickness, cv2.LINE_AA)
    cv2.line(img, (int(x) - r - 8, int(y)), (int(x) + r + 8, int(y)), color, thickness, cv2.LINE_AA)
    cv2.line(img, (int(x), int(y) - r - 8), (int(x), int(y) + r + 8), color, thickness, cv2.LINE_AA)


def _sparkline(img, data, x, y, w, h):
    valid = [d for d in data if d is not None]
    if not valid:
        return
    top = max(max(valid) * 1.2, 1e-3)
    pts = []
    n = len(valid)
    for i, val in enumerate(valid):
        px = x + int(round(w * (i / max(n - 1, 1))))
        py = y + h - int(round(h * (val / top)))
        pts.append((px, py))
    if len(pts) > 1:
        cv2.polylines(img, [np.array(pts, np.int32)], False, GREEN, 1, cv2.LINE_AA)


def draw(frame, cfg, camera, metrics, controller, det_kalman, det_raw, show_hud=True):
    out = frame.copy()
    mode = "VIRTUAL" if cfg.mode == "virtual" else "WEBCAM"
    status_color = RED
    label = "LOST"
    if controller.state == "SEARCH":
        status_color = ORANGE
        label = "SEARCHING"
    elif controller.state == "TRACK":
        status_color = YELLOW if not metrics.is_locked else GREEN
        label = "TRACKING" if not metrics.is_locked else "LOCKED"
    if not cfg.autotrack:
        label = "MANUAL"
        status_color = GRAY

    if show_hud:
        _text(out, [
            "FSOC Coarse Tracker - " + mode,
            "State: " + label,
            "FPS %d  Frame %.1f ms  Vision %.1f ms" % (int(metrics.fps), metrics.frame_ms, metrics.vision_ms),
            "Detections %.0f%%" % metrics.det_rate(),
        ], 12, 20, color=status_color)
        _text(out, [
            "PAN %+6.2f deg   TILT %+6.2f deg" % (camera.pan, camera.tilt),
            "FOV %.1f deg  %dx%d" % (camera.fov_h_deg, camera.width, camera.height),
        ], 12, 20 + 4 * 18, color=WHITE)
        err = metrics.last_err()
        if err is not None:
            _text(out, [
                "Pointing err %.3f deg" % err,
                "Lock thresh %.2f deg" % cfg.lock_threshold_deg,
            ], 12, camera.height - 84, color=GREEN if metrics.is_locked else YELLOW)
        meas = metrics.err_meas_deg[-1] if metrics.err_meas_deg else None
        if meas is not None:
            _text(out, ["Measured off-boresight %.3f deg" % meas], 12, camera.height - 32, color=WHITE)
        _sparkline(out, list(metrics.err_deg), 320, camera.height - 74, 240, 56)
        _text(out, ["err deg"], 322, camera.height - 80, scale=0.4, color=GRAY)

    cx = camera.width / 2.0
    cy = camera.height / 2.0
    cv2.line(out, (int(cx - 10), int(cy)), (int(cx + 10), int(cy)), (60, 60, 60), 1)
    cv2.line(out, (int(cx), int(cy - 10)), (int(cx), int(cy + 10)), (60, 60, 60), 1)
    cv2.circle(out, (int(cx), int(cy)), 12, (60, 60, 60), 1, cv2.LINE_AA)

    if controller.state == "SEARCH":
        r = 24 + int(10 * math.sin(metrics.frames * 0.6))
        _reticle(out, cx, cy, r, ORANGE, 2)
        _text(out, ["ACQUIRING..."], max(0, int(cx) - 55), int(cy) - r - 12, scale=0.5, color=ORANGE)
    elif det_kalman is not None:
        color = GREEN if metrics.is_locked else YELLOW
        if metrics.is_locked:
            _reticle(out, det_kalman[0], det_kalman[1], 14, GREEN, 2)
        else:
            _reticle(out, det_kalman[0], det_kalman[1], 14, YELLOW, 2)
        _line(out, (cx, cy), (det_kalman[0], det_kalman[1]), color)
    else:
        _reticle(out, cx, cy, 14, RED, 1)
    if det_raw is not None:
        cv2.circle(out, (int(det_raw[0]), int(det_raw[1])), 4, (255, 120, 60), -1, cv2.LINE_AA)
    return out


def _line(img, p1, p2, color):
    cv2.line(img, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 1, cv2.LINE_AA)