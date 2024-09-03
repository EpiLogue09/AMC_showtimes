import requests
import json
import serpapi

def google_request(amc_name):
    with open('serp_api_key.txt', 'r') as file:
        serp_api_key = file.read().strip()

    print(serp_api_key)
    params = {
        "q": amc_name,
        "location": "Atlanta, Georgia, United States",
        "hl": "en",
        "gl": "us",
        "api_key": serp_api_key
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
    google_request('AMC Phipps Plaza 14')
    google_request('AMC North Point Mall 12')
    google_request('Regal Atlantic Station')

if __name__ == "__main__":
    main()