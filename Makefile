VERSION = 1.0.0
PREFIX ?= $(HOME)/.local
SHARE = $(DESTDIR)$(PREFIX)/share

.PHONY: install uninstall deb test

test:
	python3 denden.py --selftest

install:
	install -Dm755 denden.py $(SHARE)/denden/denden.py
	install -Dm644 icons/denden.svg $(SHARE)/denden/icons/denden.svg
	install -Dm644 icons/denden-rec.svg $(SHARE)/denden/icons/denden-rec.svg
	install -Dm644 icons/denden-tray.svg $(SHARE)/denden/icons/denden-tray.svg
	install -Dm644 icons/denden.svg $(SHARE)/icons/hicolor/scalable/apps/denden.svg
	install -Dm644 denden.desktop $(SHARE)/applications/denden.desktop
	install -d $(DESTDIR)$(PREFIX)/bin
	ln -sf ../share/denden/denden.py $(DESTDIR)$(PREFIX)/bin/denden
	-[ -z "$(DESTDIR)" ] && gtk-update-icon-cache -qtf $(SHARE)/icons/hicolor 2>/dev/null; true

uninstall:
	rm -rf $(SHARE)/denden $(DESTDIR)$(PREFIX)/bin/denden \
		$(SHARE)/icons/hicolor/scalable/apps/denden.svg $(SHARE)/applications/denden.desktop

# sudo apt install ./denden_$(VERSION)_all.deb
deb:
	rm -rf build && $(MAKE) install PREFIX=/usr DESTDIR=build/pkg
	install -d build/pkg/DEBIAN
	printf '%s\n' \
		'Package: denden' \
		'Version: $(VERSION)' \
		'Architecture: all' \
		'Maintainer: Diego Horvatti <d.horvattid@gmail.com>' \
		'Depends: python3, python3-gi, python3-gi-cairo, python3-cairo, gir1.2-gtk-3.0, ffmpeg' \
		'Recommends: libnotify-bin, i965-va-driver | intel-media-va-driver' \
		'Section: video' \
		'Priority: optional' \
		'Description: Câmera redonda flutuante e gravador de tela para X11/i3' \
		> build/pkg/DEBIAN/control
	dpkg-deb --root-owner-group --build build/pkg denden_$(VERSION)_all.deb
