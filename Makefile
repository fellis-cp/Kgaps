VERSION := $(shell python3 -c "import json; print(json.load(open('metadata.json'))['KPlugin']['Version'])")

.PHONY: install uninstall reload test lint package clean

install:
	@bash install.sh

uninstall:
	@bash uninstall.sh

reload:
	@bash reload.sh

test:
	@python3 -m unittest discover -s tests -v

lint:
	@bash -n install.sh uninstall.sh reload.sh settings.sh
	@python3 -m py_compile kgaps_settings.py tests/test_kgaps.py
	@if command -v shellcheck >/dev/null 2>&1; then shellcheck install.sh uninstall.sh reload.sh settings.sh; fi

package:
	@rm -f kgaps-$(VERSION).kwinscript
	@zip -r kgaps-$(VERSION).kwinscript metadata.json contents/
	@echo "Created kgaps-$(VERSION).kwinscript"

clean:
	@rm -rf __pycache__ tests/__pycache__ *.kwinscript
