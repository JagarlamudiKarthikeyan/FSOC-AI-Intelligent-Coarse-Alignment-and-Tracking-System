import numpy as np
import cv2


class BlobDetector:
    def __init__(self, min_area=4, max_area=900, rel_thresh=0.55, min_score=0.35):
        self.min_area = min_area
        self.max_area = max_area
        self.rel_thresh = rel_thresh
        self.min_score = min_score

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        m = int(gray.max())
        if m < 60:
            return None
        thr = m * self.rel_thresh
        _, mask = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        best = None
        for i in range(1, n):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if not (self.min_area <= area <= self.max_area):
                continue
            x = int(stats[i, cv2.CC_STAT_LEFT])
            y = int(stats[i, cv2.CC_STAT_TOP])
            w = int(stats[i, cv2.CC_STAT_WIDTH])
            h = int(stats[i, cv2.CC_STAT_HEIGHT])
            sub = gray[y:y + h, x:x + w]
            comp = (labels[y:y + h, x:x + w] == i)
            wgt = sub[comp].astype(np.float32)
            score = float(wgt.mean()) / 255.0
            if score < self.min_score:
                continue
            pts = np.nonzero(comp)
            u = float(np.sum((x + pts[1]) * wgt) / wgt.sum())
            v = float(np.sum((y + pts[0]) * wgt) / wgt.sum())
            if best is None or score > best[2]:
                best = (u, v, score, area)
        return best


class KalmanTracker:
    def __init__(self, width, height, max_lost=20, gate_px=90.0):
        self.w = width
        self.h = height
        self.max_lost = max_lost
        self.gate_px = gate_px
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.transitionMatrix = np.array(
            [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32
        )
        self.kf.measurementMatrix = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0]], np.float32
        )
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.02
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 5.0
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 100.0
        self.kf.statePost = np.array(
            [[width / 2.0], [height / 2.0], [0.0], [0.0]], np.float32
        )
        self.init = False
        self.lost = 0
        self.last = None

    def reset(self, cx=None, cy=None):
        if cx is not None:
            self.kf.statePost[0, 0] = cx
            self.kf.statePost[1, 0] = cy
        self.kf.statePost[2, 0] = 0.0
        self.kf.statePost[3, 0] = 0.0
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 100.0
        self.init = False
        self.lost = 0
        self.last = None

    def step(self, det):
        self.kf.predict()
        if det is not None:
            z = np.array([[det[0]], [det[1]]], np.float32)
            if self.init:
                px = float(self.kf.statePost[0, 0])
                py = float(self.kf.statePost[1, 0])
                if np.hypot(px - z[0, 0], py - z[1, 0]) < self.gate_px:
                    self.kf.correct(z)
                    self.lost = 0
            else:
                self.kf.correct(z)
                self.init = True
                self.lost = 0
        else:
            self.lost += 1
        if not self.init or self.lost > self.max_lost:
            return None
        u = float(np.clip(self.kf.statePost[0, 0], 0, self.w))
        v = float(np.clip(self.kf.statePost[1, 0], 0, self.h))
        self.last = (u, v)
        return (u, v)