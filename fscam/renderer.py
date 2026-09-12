import numpy as np
import cv2

_SKY = (14, 18, 28)
_GROUND_DEEP = (6, 9, 16)
_GROUND_NEAR = (60, 68, 88)
_AIRGLOW = (52, 66, 96)


def make_beacon_patch(sigma_px):
    sigma = max(0.8, float(sigma_px))
    ksize = int(round(6.0 * sigma))
    ksize = ksize + 1 if ksize % 2 == 0 else ksize
    ax = np.arange(ksize) - ksize // 2
    X, Y = np.meshgrid(ax, ax)
    d2 = X.astype(np.float32) ** 2 + Y.astype(np.float32) ** 2
    core = np.exp(-d2 / (2.0 * sigma ** 2)).astype(np.float32)
    glow = np.exp(-d2 / (2.0 * (sigma * 3.0) ** 2)).astype(np.float32)
    return core, glow


def _background(scene, camera, pan, tilt):
    h, w = camera.height, camera.width
    img = np.full((h, w, 3), _SKY, dtype=np.uint8)
    world_el = camera.world_el_map(pan, tilt)
    ground = world_el < scene.horizon_deg
    if ground.any():
        t = np.clip((scene.horizon_deg - world_el) / 5.0, 0.0, 1.0)
        g = np.zeros((h, w, 3), dtype=np.float32)
        for c in range(3):
            g[:, :, c] = _GROUND_DEEP[c] + t * (_GROUND_NEAR[c] - _GROUND_DEEP[c])
        g *= ground[:, :, None]
        img = np.where(ground[:, :, None], g.astype(np.uint8), img)
    glow = (world_el > scene.horizon_deg) & (world_el < scene.horizon_deg + 5.0)
    if glow.any():
        t = np.clip((scene.horizon_deg + 5.0 - world_el) / 5.0, 0.0, 1.0)
        g = np.zeros((h, w, 3), dtype=np.float32)
        for c in range(3):
            g[:, :, c] = _SKY[c] + t * (_AIRGLOW[c] - _SKY[c])
        g *= glow[:, :, None]
        img = np.where(glow[:, :, None] & (g.astype(np.uint8) > img), g.astype(np.uint8), img)
    return img


def _draw_stars(scene, camera, img, pan, tilt):
    u, v, depth = camera.project_many(scene.star_az, scene.star_el, pan, tilt)
    front = depth > 0.001
    u = u[front]
    v = v[front]
    mag = scene.star_mag[front]
    inside = (u >= 0) & (u < camera.width) & (v >= 0) & (v < camera.height)
    u = np.clip(u[inside].round(), 0, camera.width - 1).astype(np.int32)
    v = np.clip(v[inside].round(), 0, camera.height - 1).astype(np.int32)
    mag = mag[inside]
    brightness = 255.0 * np.power(2.4, -mag)
    bright_mask = brightness > 2.0
    if bright_mask.any():
        bu = u[bright_mask]
        bv = v[bright_mask]
        bb = brightness[bright_mask].astype(np.uint8)
        star_col = np.array([0.0, 0.05, 0.10])
        base = np.zeros((camera.height, camera.width, 3), dtype=np.float32)
        base[bv, bu] = bb[:, None] * star_col[None, :]
        img[:] = np.maximum(img.astype(np.float32), base).astype(np.uint8)
        for i in range(bu.size):
            if bb[i] > 40.0:
                cv2.circle(img, (int(bu[i]), int(bv[i])), 2, (48, 58, 96), 1, cv2.LINE_AA)


def _draw_sun(scene, camera, img, pan, tilt):
    px = camera.project_world(scene.sun_az, scene.sun_el, pan, tilt)
    if px is None:
        return
    s = 36
    cv2.circle(img, (int(px[0]), int(px[1])), s * 3, (52, 72, 130), -1, cv2.LINE_AA)
    cv2.circle(img, (int(px[0]), int(px[1])), s * 2, (150, 190, 255), -1, cv2.LINE_AA)
    cv2.circle(img, (int(px[0]), int(px[1])), s, (255, 255, 255), -1, cv2.LINE_AA)


def _add_patch(img, patch, color, peak, cx, cy):
    h, w = img.shape[:2]
    k = patch.shape[0]
    x0 = int(round(cx - patch.shape[1] / 2.0))
    y0 = int(round(cy - patch.shape[0] / 2.0))
    x1 = x0 + k
    y1 = y0 + k
    slx0 = max(0, x0)
    sly0 = max(0, y0)
    slx1 = min(w, x1)
    sly1 = min(h, y1)
    if slx1 <= slx0 or sly1 <= sly0:
        return
    px0, py0 = slx0 - x0, sly0 - y0
    px1, py1 = px0 + (slx1 - slx0), py0 + (sly1 - sly0)
    sub = patch[py0:py1, px0:px1]
    roi = img[sly0:sly1, slx0:slx1].astype(np.float32)
    add = peak * sub[:, :, None] * np.array(color, dtype=np.float32)
    roi += add
    img[sly0:sly1, slx0:slx1] = np.clip(roi, 0, 255).astype(np.uint8)


def render(scene, camera, patches, t, vib=(0.0, 0.0), turb=(0.0, 0.0)):
    pan = camera.pan + vib[0]
    tilt = camera.tilt + vib[1]
    img = _background(scene, camera, pan, tilt)
    _draw_stars(scene, camera, img, pan, tilt)
    if scene.sun_enabled:
        _draw_sun(scene, camera, img, pan, tilt)
    az, el = scene.beacon(t)
    px = camera.project_world(az, el, pan, tilt)
    if px is not None:
        bx = px[0] + turb[0]
        by = px[1] + turb[1]
        core, glow = patches
        _add_patch(img, glow, (120, 60, 255), 0.55, bx, by)
        _add_patch(img, core, (120, 70, 255), 0.85, bx, by)
    return img