import numpy as np


def direction_from(az_deg, el_deg):
    az = np.radians(az_deg)
    el = np.radians(el_deg)
    return np.array([
        np.cos(el) * np.cos(az),
        np.cos(el) * np.sin(az),
        np.sin(el),
    ])


def angular_sep(az1, el1, az2, el2):
    v1 = direction_from(az1, el1)
    v2 = direction_from(az2, el2)
    dot = float(np.clip(np.dot(v1, v2), -1.0, 1.0))
    return float(np.degrees(np.arccos(dot)))


def _camera_basis(pan_deg, tilt_deg):
    p = np.radians(pan_deg)
    t = np.radians(tilt_deg)
    cp, sp = np.cos(p), np.sin(p)
    ct, st = np.cos(t), np.sin(t)
    w = np.array([ct * cp, ct * sp, st])
    r = np.array([-sp, cp, 0.0])
    up = np.array([-st * cp, -st * sp, ct])
    return w, r, up


class VirtualCamera:
    def __init__(self, width, height, fov_h_deg, pan_deg=0.0, tilt_deg=0.0,
                 pan_limits=(-90.0, 90.0), tilt_limits=(-30.0, 30.0)):
        self.width = int(width)
        self.height = int(height)
        self.fov_h_deg = float(fov_h_deg)
        self.pan = float(pan_deg)
        self.tilt = float(tilt_deg)
        self.pan_limits = pan_limits
        self.tilt_limits = tilt_limits
        self._recompute()

    def _recompute(self):
        self.f_px = (self.width / 2.0) / np.tan(np.radians(self.fov_h_deg) / 2.0)
        U, V = np.meshgrid(np.arange(self.width), np.arange(self.height))
        self._U = U
        self._V = V
        self._tan_az = (U - self.width / 2.0) / self.f_px
        self._tan_el = (self.height / 2.0 - V) / self.f_px

    def set_fov(self, fov_h_deg):
        self.fov_h_deg = float(fov_h_deg)
        self._recompute()

    def set_pose(self, pan, tilt):
        self.pan = float(np.clip(pan, *self.pan_limits))
        self.tilt = float(np.clip(tilt, *self.tilt_limits))

    def direction_in_cam(self, az_deg, el_deg, pan=None, tilt=None):
        pan = pan if pan is not None else self.pan
        tilt = tilt if tilt is not None else self.tilt
        d = direction_from(az_deg, el_deg)
        w, r, up = _camera_basis(pan, tilt)
        depth = float(np.dot(d, w))
        if depth <= 0.0:
            return None
        az_c = np.arctan2(float(np.dot(d, r)), depth)
        el_c = np.arctan2(float(np.dot(d, up)), depth)
        return (az_c, el_c)

    def pixel(self, az_c, el_c):
        u = self.width / 2.0 + self.f_px * np.tan(az_c)
        v = self.height / 2.0 - self.f_px * np.tan(el_c)
        return (float(u), float(v))

    def project_world(self, az_deg, el_deg, pan=None, tilt=None):
        dirn = self.direction_in_cam(az_deg, el_deg, pan, tilt)
        if dirn is None:
            return None
        u, v = self.pixel(*dirn)
        if 0.0 <= u <= self.width and 0.0 <= v <= self.height:
            return (u, v)
        return None

    def project_many(self, azs, els, pan=None, tilt=None):
        pan = pan if pan is not None else self.pan
        tilt = tilt if tilt is not None else self.tilt
        az = np.radians(azs)
        el = np.radians(els)
        d = np.stack([
            np.cos(el) * np.cos(az),
            np.cos(el) * np.sin(az),
            np.sin(el),
        ], axis=1)
        w, r, up = _camera_basis(pan, tilt)
        depth = d @ w
        az_c = np.arctan2(d @ r, depth)
        el_c = np.arctan2(d @ up, depth)
        u = self.width / 2.0 + self.f_px * np.tan(az_c)
        v = self.height / 2.0 - self.f_px * np.tan(el_c)
        return u, v, depth

    def pixel_to_angles(self, u, v):
        az_c = np.arctan((u - self.width / 2.0) / self.f_px)
        el_c = np.arctan((self.height / 2.0 - v) / self.f_px)
        return az_c, el_c

    def world_el_map(self, pan, tilt):
        return np.degrees(np.radians(tilt) + np.arctan(self._tan_el))