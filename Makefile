.PHONY: install, package, upload, clean, venv

clean:
	rm -rf .venv; \
	rm -rf dist/* ; \
	find -iname "*.pyc" -delete

package: clean venv
	. .venv/bin/activate; \
	python3 -m build; \

upload: clean package
	. .venv/bin/activate; \
	python3 -m twine upload --repository testpypi dist/*

venv:
	test -d .venv || python -m venv .venv; \
	. .venv/bin/activate; pip install -U build twine

install:
	test -d .venv || python3 -m venv .venv; \
	source .venv/bin/activate; \
	python3 -m pip install -e .
