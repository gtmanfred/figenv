tests:
	coverage run -m test

syntax:
	black -S --diff .

coverage:
	coverage report
	coverage xml
