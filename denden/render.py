import math

import cairo
from gi.repository import Gdk, GdkPixbuf, GLib

from .config import CAPTURE_SIZE

PLACEHOLDER_GRAY = 0.15


def paint_bubble(cr, size, frame, mirror):
    _clear(cr)
    _clip_to_circle(cr, size)
    if frame:
        _set_frame_source(cr, size, frame, mirror)
    else:
        cr.set_source_rgb(PLACEHOLDER_GRAY, PLACEHOLDER_GRAY, PLACEHOLDER_GRAY)
    cr.paint()


def _clear(cr):
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_rgba(0, 0, 0, 0)
    cr.paint()
    cr.set_operator(cairo.OPERATOR_OVER)


def _clip_to_circle(cr, size):
    radius = size / 2
    cr.arc(radius, radius, radius, 0, 2 * math.pi)
    cr.clip()


def _set_frame_source(cr, size, frame, mirror):
    pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(frame), GdkPixbuf.Colorspace.RGB,
                                             False, 8, CAPTURE_SIZE, CAPTURE_SIZE, CAPTURE_SIZE * 3)
    if mirror:
        cr.translate(size, 0)
        cr.scale(-1, 1)
    cr.scale(size / CAPTURE_SIZE, size / CAPTURE_SIZE)
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
