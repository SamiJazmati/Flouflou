unittest:
	@python -m unittest discover -s tests

lint:
	@isort *.py **/*.py
	@black --skip-string-normalization *.py **/*.py
	@flake8 --ignore=E501,W503,BLK100 --per-file-ignores=**/__init__.py:F401 *.py **/*.py
