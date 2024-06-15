import requests
import json
import serpapi

def movie_request():
    # Get API key from api_key.txt
    with open('api_key.txt', 'r') as file:
        api_key = file.read().strip()

    # Base URL for the AMC Theatres API
    base_url = 'https://api.amctheatres.com'

    # Endpoint for fetching now-playing movies
    endpoint = '/v2/movies/views/now-playing'
    # Construct the full URL
    url = f'{base_url}{endpoint}'
    # Headers including your API key
    headers = {
        'X-AMC-Vendor-Key': api_key
    }
    print(headers)
    # Make the GET request
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        # Handle errors
        print(f'Error: {response.status_code}')
        print(response.text)
        return

    # Parse the JSON response
    data = response.json()
    # Print the first 100 movie title
    print(data)

def google_request():
    #url = 'https://serpapi.com/search.json?q=eternals+theater&location=Austin,+Texas,+United+States&hl=en&gl=us'
    with open('serp_api_key.txt', 'r') as file:
        api_key = file.read().strip()
    params = {
        "q": "AMC Phipps Plaza 14",
        "location": "Atlanta, Georgia, United States",
        "hl": "en",
        "gl": "us",
        "api_key": api_key
    }
    search = serpapi.search(params)
    results = search.as_dict()
    showtimes = results["showtimes"]
    #extract only first 7 dictionaries
    showtimes = [showtime for showtime in showtimes[:7]]
    #append results to a json file with correct indent
    with open('showtimes.json', 'w') as file:
        json.dump(showtimes, file, indent=4)


def main():
    #movie_request()
    google_request()

if __name__ == "__main__":
    main()
