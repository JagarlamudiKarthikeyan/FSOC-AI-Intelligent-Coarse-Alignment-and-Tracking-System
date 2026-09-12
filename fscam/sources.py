import cv2

from . import renderer


class VirtualSource:
    def __init__(self, scene, camera, disturbances, cfg):
        self.scene = scene
        self.camera = camera
        self.disturbances = disturbances
        self.cfg = cfg
        self.patches = renderer.make_beacon_patch(cfg.beacon_sigma_px)

    def step(self, t):
        vib = self.disturbances.vibration()
        turb = self.disturbances.turbulence()
        frame = renderer.render(self.scene, self.camera, self.patches, t, vib, turb)
        frame = self.disturbances.apply(frame)
        return frame, self.scene.beacon(t)


class WebcamSource:
    def __init__(self, cfg):
        self.cfg = cfg
        self.cap = cv2.VideoCapture(cfg.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Cannot open camera index %d" % cfg.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)

    def open(self):
        return self.cap.isOpened()

    def step(self, t):
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame from camera")
        if frame.shape[1] != self.cfg.width or frame.shape[0] != self.cfg.height:
            frame = cv2.resize(frame, (self.cfg.width, self.cfg.height))
        if self.cfg.disturbances:
            frame = self.disturbances.apply(frame)
        return frame, None

    def set_disturbances(self, disturbances):
        self.disturbances = disturbances
        return self

    def release(self):
        self.cap.release()