# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import os
import urllib2
import requests
import json
import datetime
from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from apiclient.discovery import build
from google.cloud import vision
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.http import HttpResponseRedirect


headers = {'content-type': 'application/json'}
qpx_url = "https://www.googleapis.com/qpxExpress/v1/trips/search?key=AIzaSyB2TJ_9zyPVDg-PTZBi47rpg3nDJkROeRY"

def index(request):
    if request.method == 'POST' and request.FILES['files[]']:
        #save a local copy of image uploaded
        myfile = request.FILES['files[]']
        vision_client = vision.Client()
        content = myfile.read()
        image = vision_client.image(content=content)

        # Performs label detection on the image file
        annotations = image.detect_web()

        # #make request to get latitude and longitude from geocoder api
        location = annotations.web_entities[0].description
        parsed_location = location.replace(" ", "+")
        parsed_location = parsed_location.replace("&", "%26")
        geo_key = "AIzaSyC7g32qKCo5Czjqz4E3aKLhE0vYBVUJPls"
        geo_url = "https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s" % (parsed_location, geo_key)
        response = urllib2.urlopen(geo_url)
        jsongeocode = response.read()
        parsedjson = json.loads(jsongeocode)

        #save the boundaries of the location
        ne_latitude = parsedjson["results"][0]["geometry"]["viewport"]["northeast"]["lat"]
        sw_latitude = parsedjson["results"][0]["geometry"]["viewport"]["southwest"]["lat"]
        ne_longitude = parsedjson["results"][0]["geometry"]["viewport"]["northeast"]["lng"]
        sw_longitude = parsedjson["results"][0]["geometry"]["viewport"]["southwest"]["lng"]

        #find lat and long between the two boundary lat and long
        avg_lat = (ne_latitude + sw_latitude)/2
        avg_lng = (ne_longitude + sw_longitude)/2

        
        #Get lat and long from user location
        freegeoip = "http://freegeoip.net/json"
        geo_r = requests.get(freegeoip)
        geo_json = geo_r.json()

        #Reverse Geocoding call to get accurate city
        base = "http://maps.googleapis.com/maps/api/geocode/json?"
        params = "latlng={lat},{lon}&sensor={sen}".format(
            lat=avg_lat,
            lon=avg_lng,
            sen='true'
        )
        reversegeo_url = "{base}{params}".format(base=base, params=params)
        rev_response = requests.get(reversegeo_url)
        rev_json = rev_response.json()
        form_address = rev_json['results'][0]['formatted_address']
        city = ""

        #If the city is in the USA then parse form_address to get city
        city = ""
        if form_address.find('USA') != -1:
            array = form_address.split(",")
            city = array[1]
            city = city[1:]

        #Search list of iata codes
        destination = ""
        iata_json=open(os.path.abspath("") + '/personal/static/personal/cities.json').read()
        iata_data = json.loads(iata_json)
        for x in iata_data['response']:
            if city == x['name']:
                destination = x['code']
                break


        #Get IATA Code of Origin
        origin_url = "http://iatageo.com/getCode/" + str(geo_json["latitude"]) +"/" + str(geo_json["longitude"])
        origin_response = requests.get(origin_url)
        origin_json = origin_response.json()
        origin = origin_json["code"]

        #If a destination was already found, then there is no need for IATAGEO call
        if destination == "":
            #Get IATA Code of Destination
            destination_url = "http://iatageo.com/getCode/" + str(avg_lat) +"/" + str(avg_lng)
            destination_response = requests.get(destination_url)
            destination_json = destination_response.json()
            destination = destination_json["code"]

        #Set default date to 7 days from now
        date = datetime.datetime.now() + datetime.timedelta(days=7)
        date = date.strftime("%Y-%m-%d")
        maxnumresults = 5

        #Requst Body for Flights
        qpx_body = {
            "request": {
                "passengers": {
                  "kind": "qpxexpress#passengerCounts",
                  "adultCount": 1,
                },
                "slice": [
                  {
                    "kind": "qpxexpress#sliceInput",
                    "origin": origin,
                    "destination": destination,
                    "date": date,
                  }
                ],
                "refundable": "false",
                "solutions": maxnumresults
            }
        }
        qpx_response = requests.post(qpx_url, data=json.dumps(qpx_body), headers=headers)
        data = qpx_response.json()

        #Check to see if flights were found 
        if 'tripOption' not in data["trips"]:
            error_context = {'avg_lat': avg_lat, 'avg_lng': avg_lng, 'location': location}
            error = render_to_string('personal/error.html', error_context)
            return HttpResponse(error)
 
        #Parse through flights returned and create a list of flight objects
        flights = []
        forcount = 0
        for x in data['trips']['tripOption']:
            airline_code = x['slice'][0]['segment'][0]['flight']['carrier']
            sabre_airline_url ="https://api.test.sabre.com/v1/lists/utilities/airlines?airlinecode=" + airline_code
            request_airline = requests.get(sabre_airline_url, headers={"Authorization": "Bearer T1RLAQJ98oL0fCqCFcp4DEyDi9oRk4hlFhBqmyxPxpAlalR/qLZ8QD2hAACwMPxEhsUlykBDor02gdtwfUP4uJW5jgexNbetElhMdqTPuiI8rYL4k4htQv5qIoupRWaz7g8Il2ier47L8ECh9PMU2zFQzpDa6BrGSQ6LMYbg4BslXnIhwxcQBqTaEoiQPX23IfJLJBJJAgi49ODS5Lr9msjHAd0LtvTpG6VnV3sIwnd4z4NNL1gPhFMuwTNCKH0Pqvtl+GM93UWFCMRLdv1VHG1fcJZmmO6XxaTXjG8*"}).json()
            airline = request_airline['AirlineInfo'][0]['AirlineName']
            price = x['saleTotal']
            price = price.replace("USD", "$")
            departure_time = x['slice'][0]['segment'][0]['leg'][0]['departureTime']
            arrival_time = x['slice'][0]['segment'][len(x['slice'][0]['segment'])-1]['leg'][0]['arrivalTime']
            newFlight = {'price': price, 'airline': airline, 'origin': origin, 'dest': destination, 'ddate': departure_time, 'adate': arrival_time}   
            flights.append(newFlight)
            forcount = forcount + 1
            if forcount >= maxnumresults:
                break

        #make call to get lodging options
        lodging_url = "https://maps.googleapis.com/maps/api/place/radarsearch/json?location="
        lodging_url = lodging_url + str(avg_lat) + "," + str(avg_lng) + "&radius=5000&type=lodging&key=AIzaSyB2TJ_9zyPVDg-PTZBi47rpg3nDJkROeRY"
        lodging_places = requests.get(lodging_url, headers=headers).json()

        #Parse through lodging options returned and create a list of lodging objects
        lodging = []
        forcount = 0
        for x in lodging_places['results']:
            lodging_places_id = x['place_id']
            lodging_places_id_url = "https://maps.googleapis.com/maps/api/place/details/json?placeid=" + lodging_places_id + "&key=AIzaSyB2TJ_9zyPVDg-PTZBi47rpg3nDJkROeRY"
            lodging_response = requests.get(lodging_places_id_url).json()
            lodging_name = lodging_response['result']['name']
            lodging_address =  lodging_response['result']['formatted_address']
            lodging_number = lodging_response['result']['international_phone_number']
            lodging_rating = lodging_response['result']['rating']
            newRoom = {'name': lodging_name, 'address': lodging_address, 'number': lodging_number, 'rating': lodging_rating}
            lodging.append(newRoom)
            forcount = forcount + 1
            if forcount >= maxnumresults:
                break

        #make call to get cars options      
        cars_url = "https://maps.googleapis.com/maps/api/place/radarsearch/json?location="
        cars_url = cars_url + str(avg_lat) + "," + str(avg_lng) + "&radius=5000&type=car_rental&key=AIzaSyB2TJ_9zyPVDg-PTZBi47rpg3nDJkROeRY"
        cars_places = requests.get(cars_url, headers=headers).json()

        #Parse through cars options returned and create a list of cars objects
        cars = []
        forcount = 0
        for x in cars_places['results']:
            car_places_id = x['place_id']
            car_places_id_url = "https://maps.googleapis.com/maps/api/place/details/json?placeid=" + car_places_id + "&key=AIzaSyB2TJ_9zyPVDg-PTZBi47rpg3nDJkROeRY"
            car_response = requests.get(car_places_id_url).json()
            car_name = car_response['result']['name']
            car_address =  car_response['result']['formatted_address']
            car_number = car_response['result']['international_phone_number']

            #if car rental rating could not be found, put N/A
            if 'rating' in car_response['result']:
                car_rating = car_response['result']['rating']
            else:
                car_rating = "N/A"
            newCar = {'name': car_name, 'address': car_address, 'number': car_number, 'rating': car_rating}
            cars.append(newCar)
            forcount = forcount + 1
            if forcount >= maxnumresults:
                break

        #create redirecting urls for buttons
        hotel_url = "https://www.google.com/maps/search/hotels+" +  parsed_location
        car_url = "https://www.google.com/maps/search/car+rental+" + parsed_location
        booking_url = "https://www.google.com/flights/#search;f=" + origin + ";t=" + destination + ";d=" + date + ";tt=o;q=purchase+flight+ticket"
        
        #create context file for rendering with jinja
        context = {'flights' : flights, 'lodging': lodging, 'cars': cars, 'booking_url': booking_url, 'hotel_url': hotel_url, 'car_url': car_url, 'avg_lat': avg_lat, 'avg_lng': avg_lng, 'location': location}
        html = render_to_string('personal/home.html', context)
        return HttpResponse(html)

    return render(request, 'personal/header.html')

def contact(request):
    return render(request, 'personal/header.html')

       