.PHONY: install, package, upload

package:
	rm -rf dist/*; \
	source .venv/bin/activate; \
	python3 -m build; \

upload:
	source .venv/bin/activate; \
	python3 -m twine upload --repository testpypi dist/*

install:
	test -d .venv || python3 -m venv .venv; \
	source .venv/bin/activate; \
	python3 -m pip install -e .
