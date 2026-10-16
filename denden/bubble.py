from gi.repository import Gdk, GLib, Gtk

from .camera import Camera
from .config import (APP_NAME, BUBBLE_SIZE, HOVER_OPACITY, MAX_BUBBLE_SIZE,
                     MIN_BUBBLE_SIZE, RESIZE_STEP, SCREEN_MARGIN)
from .render import paint_bubble
from .shape import circle_region
from .system import work_area

EVENTS = (Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
          | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK
          | Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
SCROLL_STEPS = {Gdk.ScrollDirection.UP: RESIZE_STEP, Gdk.ScrollDirection.DOWN: -RESIZE_STEP}


class Bubble(Gtk.Window):
    def __init__(self, on_record, on_menu):
        super().__init__(type=Gtk.WindowType.POPUP, title=APP_NAME)
        self._on_record = on_record
        self._on_menu = on_menu
        self.size = BUBBLE_SIZE
        self.mirror = True
        self._frame = None
        self._camera = None
        self._drag_offset = None
        self._use_transparent_visual()
        self._connect_events()
        self._apply_size()
        self._move_to_bottom_right()

    @property
    def camera_on(self):
        return self._camera is not None

    @property
    def dragging(self):
        return self._drag_offset is not None

    def show_camera(self):
        if not self.camera_on:
            self._camera = Camera(self._receive_frame)
            self.show_all()

    def hide_camera(self):
        if self.camera_on:
            self.hide()
            self._camera.stop()
            self._camera = self._frame = None

    def toggle_camera(self):
        self.hide_camera() if self.camera_on else self.show_camera()

    def toggle_mirror(self):
        self.mirror = not self.mirror
        self.queue_draw()

    def keep_on_top(self):
        window = self.get_window()
        if window and self.camera_on and not self.dragging:
            window.raise_()

    def _use_transparent_visual(self):
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

    def _connect_events(self):
        self.add_events(EVENTS)
        self.connect("draw", self._draw)
        self.connect("button-press-event", self._press)
        self.connect("button-release-event", self._release)
        self.connect("motion-notify-event", self._motion)
        self.connect("scroll-event", self._scroll)
        self.connect("enter-notify-event", self._enter)
        self.connect("leave-notify-event", self._leave)

    def _move_to_bottom_right(self):
        x, y, width, height = work_area()
        self.move(x + width - self.size - SCREEN_MARGIN, y + height - self.size - SCREEN_MARGIN)

    def _apply_size(self):
        self.set_size_request(self.size, self.size)
        self.resize(self.size, self.size)
        self.shape_combine_region(circle_region(self.size))
        self.queue_draw()

    def _resize_from_center(self, new_size):
        x, y = self.get_position()
        shift = (new_size - self.size) // 2
        self.size = new_size
        self.move(x - shift, y - shift)
        self._apply_size()

    def _set_opacity(self, opacity):
        Gtk.Widget.set_opacity(self, opacity)

    def _receive_frame(self, frame):
        self._frame = frame
        GLib.idle_add(self.queue_draw)

    def _draw(self, _widget, cr):
        paint_bubble(cr, self.size, self._frame, self.mirror)
        return True

    def _press(self, _widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            self._start_drag(event)
        elif event.button == Gdk.BUTTON_MIDDLE:
            self._on_record()
        elif event.button == Gdk.BUTTON_SECONDARY:
            self._on_menu(event)
        return True

    def _start_drag(self, event):
        x, y = self.get_position()
        self._drag_offset = (event.x_root - x, event.y_root - y)
        self._set_opacity(1.0)

    def _release(self, _widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            self._drag_offset = None
        return True

    def _motion(self, _widget, event):
        if self.dragging:
            offset_x, offset_y = self._drag_offset
            self.move(int(event.x_root - offset_x), int(event.y_root - offset_y))
        return True

    def _scroll(self, _widget, event):
        new_size = max(MIN_BUBBLE_SIZE, min(MAX_BUBBLE_SIZE, self.size + _scroll_step(event)))
        if new_size != self.size:
            self._resize_from_center(new_size)
        return True

    def _enter(self, *_):
        self._set_opacity(HOVER_OPACITY)

    def _leave(self, *_):
        if not self.dragging:
            self._set_opacity(1.0)


def _scroll_step(event):
    if event.direction == Gdk.ScrollDirection.SMOOTH:
        return -RESIZE_STEP if event.delta_y > 0 else RESIZE_STEP
    return SCROLL_STEPS.get(event.direction, 0)
