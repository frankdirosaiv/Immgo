This web application uses the Django web framework for Python
To run this application on a local machine the collowing command line arguments were executed:

	pip install django

	pip install --upgrade google-api-python-client

	pip install --upgrade google-cloud

	pip install requests

*For google installs, Macs may need to APPEND pip installs with:

	--ignore installed six

For authentication, the following command line arguments were used:

	export GCLOUD_PROJECT=315Mashup

	export GOOGLE_APPLICATION_CREDENTIALS=<path to project>\team_project3\DjangoSite\mysite\apikey.json


Once Django is installed on you local machine with the proper authentication, find your way to the 'DjangoSite/mysite' directory
Within this directory should be 'manage.py'
In your terminal, run the following command to star the application

	python manage.py runserver

Then you can open up a browser and go to 127.0.0.1:8000 to see the Immgo website
To use the Immgo application, drag in a photo of a location you would like to travel to.
Some images provide more accurate results than others. 
After uploading your image, Immgo should show you your destination on a map, flights, hotels, and car rental options

To view the fully functioning site, go to:

	http://desolate-meadow-25184.herokuapp.com/

If there are any problems setting up our webapplication, you can contact our group members at the following numbers:

	Briana Martinez: 210-251-0255 (Mac User)
	Wyatt Payne: 972-999-6119 (Mac User)
	Frank DiRosa: 210-833-7489 (PC User)
