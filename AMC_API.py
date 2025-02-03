import requests
import json
import serpapi
import os

def google_request(amc_name):
    api_key = os.getenv("GOOG_API_KEY")
    print("API Key is set" if api_key else "API Key not found")
    params = {
        "q": amc_name,
        "location": "Evanston, Illinois, United States",
        "hl": "en",
        "gl": "us",
        "api_key": api_key
    }
    search = serpapi.search(params)

    results = search.as_dict()
    showtimes = results["showtimes"]
    #extract only first 7 dictionaries
    showtimes = [showtime for showtime in showtimes[:14]]
    #extract all movie titles
    # for day_info in showtimes:
    #     day = day_info.get('day', 'No day provided')
    #     print(f"Day: {day}")
    #
    #     # Print each movie showing on this day
    #     movies = day_info.get('movies', [])
    #     for movie in movies:
    #         print(f" - {movie['name']}")
    #append results to a json file with correct indent
    with open(f'showtime_{amc_name}.json', 'w') as file:
        json.dump(showtimes, file, indent=4)


def main():
    #movie_request()
    google_request('AMC Evanston 12')
    google_request('AMC Village Crossing 18')
    google_request('AMC River East 21')

if __name__ == "__main__":
    main()