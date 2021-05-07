tests:
	poetry run coverage run -m test

syntax:
	poetry run black --diff --check .

coverage:
	poetry run coverage report
	poetry run coverage xml
