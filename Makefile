tests:
	poetry run coverage run -m test

syntax:
	poetry run black --diff .

coverage:
	poetry run coverage report
	poetry run coverage xml
