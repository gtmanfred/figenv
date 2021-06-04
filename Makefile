tests:
	coverage run -m test

syntax:
	black --diff --check .

coverage:
	coverage report
	coverage xml
