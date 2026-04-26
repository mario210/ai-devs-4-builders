import requests
import math
import time
import json
import os
from dotenv import load_dotenv
from ai.agent import AGENTS_API_KEY

# Load environment variables
load_dotenv()

# Tools for task 2 - findhim

# --- Constants ---
hub_data_url = os.environ.get("HUB_DATA_BASE_URL")
LOCATIONS_URL = f"{hub_data_url}/{AGENTS_API_KEY}/findhim_locations.json"
CITY_COORDINATES_URL = "https://nominatim.openstreetmap.org/search"
PERSON_COORDINATES_URL = os.environ.get("HUB_API_LOCATION_URL")
ACCESS_LEVEL_URL = os.environ.get("HUB_API_ACCESSLEVEL_URL")

PEOPLE_PAYLOAD = {
    "answer": [
        {
            "name": "Cezary",
            "surname": "Żurek",
            "gender": "M",
            "born": 1987,
            "city": "Grudziądz",
            "tags": ["transport", "praca z ludźmi"],
        },
        {
            "name": "Jacek",
            "surname": "Nowak",
            "gender": "M",
            "born": 1991,
            "city": "Grudziądz",
            "tags": ["transport"],
        },
        {
            "name": "Oskar",
            "surname": "Sieradzki",
            "gender": "M",
            "born": 1993,
            "city": "Grudziądz",
            "tags": ["transport", "praca z ludźmi"],
        },
        {
            "name": "Wojciech",
            "surname": "Bielik",
            "gender": "M",
            "born": 1986,
            "city": "Grudziądz",
            "tags": ["transport"],
        },
        {
            "name": "Wacław",
            "surname": "Jasiński",
            "gender": "M",
            "born": 1986,
            "city": "Grudziądz",
            "tags": ["transport"],
        },
        {
            "name": "Marek",
            "surname": "Zieliński",
            "gender": "M",
            "born": 1991,
            "city": "Grudziądz",
            "tags": ["transport"],
        },
    ]
}

# --- Helper Functions ---


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_locations_data():
    try:
        response = requests.get(LOCATIONS_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching locations data: {e}")
    return None


def get_city_coordinates(city_name):
    print(f"Getting coordinates for city: {city_name}...")
    params = {"q": city_name, "format": "json", "countrycodes": "pl", "limit": 1}
    headers = {"User-Agent": "findhim_search/1.0"}
    try:
        response = requests.get(CITY_COORDINATES_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return [(lat, lon)]
    except Exception as e:
        print(f"Error getting coordinates for '{city_name}': {e}")
    return []


def get_person_coordinates(name: str, surname: str):
    payload = {
        "apikey": AGENTS_API_KEY,
        "name": name.strip(),
        "surname": surname.strip(),
    }
    try:
        response = requests.post(PERSON_COORDINATES_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        results = []
        if isinstance(data, list):
            for item in data:
                if "latitude" in item and "longitude" in item:
                    results.append((item["latitude"], item["longitude"]))
        return results
    except Exception as e:
        print(f"Error getting person coordinates: {e}")
    return []


def _get_active_power_plant_locations():
    print("Fetching power plant locations...")
    locations_data = get_locations_data()
    if not locations_data or "power_plants" not in locations_data:
        return []

    power_plants = locations_data.get("power_plants", {})
    power_plant_locations = []

    for city, plant_info in power_plants.items():
        if not plant_info.get("is_active"):
            continue
        coords_list = get_city_coordinates(city)
        for coords in coords_list:
            power_plant_locations.append(
                {"city": city, "coords": coords, "code": plant_info.get("code")}
            )
        time.sleep(1)
    return power_plant_locations


def _find_min_distance_for_one_person(person, power_plant_locations):
    person_coords_list = get_person_coordinates(person["name"], person["surname"])
    time.sleep(0.5)

    if not person_coords_list:
        return float("inf"), None, None

    min_dist_person = float("inf")
    closest_city_person = None
    closest_plant_code = None

    for p_coords in person_coords_list:
        for plant in power_plant_locations:
            dist = haversine(
                p_coords[0], p_coords[1], plant["coords"][0], plant["coords"][1]
            )
            if dist < min_dist_person:
                min_dist_person = dist
                closest_city_person = plant["city"]
                closest_plant_code = plant["code"]

    return min_dist_person, closest_city_person, closest_plant_code


# --- Tool Functions ---


def find_closest_person_to_power_plant(name: str = None, surname: str = None):
    """Orchestrator to find the closest person to a power plant."""
    power_plant_locations = _get_active_power_plant_locations()
    if not power_plant_locations:
        return json.dumps({"error": "No power plant coordinates found."})

    if name and surname:
        people_to_process = [
            p
            for p in PEOPLE_PAYLOAD["answer"]
            if p["name"] == name and p["surname"] == surname
        ]
    else:
        people_to_process = PEOPLE_PAYLOAD["answer"]

    closest_person_details = None
    closest_plant_city = None
    closest_plant_code = None
    min_distance_overall = float("inf")

    print("\nProcessing people and calculating distances...")
    for person in people_to_process:
        distance, city, code = _find_min_distance_for_one_person(
            person, power_plant_locations
        )
        if distance < min_distance_overall:
            min_distance_overall = distance
            closest_person_details = person
            closest_plant_city = city
            closest_plant_code = code

    if closest_person_details:
        result = {
            "name": closest_person_details["name"],
            "surname": closest_person_details["surname"],
            "closest_power_plant_city": closest_plant_city,
            "closest_power_plant_code": closest_plant_code,
            "distance_km": f"{min_distance_overall:.2f}",
        }
        return json.dumps(result)
    else:
        return json.dumps({"error": "Could not determine closest person."})


def get_access_level_for_person(name: str, surname: str):
    """Fetches access level based on name/surname and internal birth year."""
    person_details = next(
        (
            p
            for p in PEOPLE_PAYLOAD["answer"]
            if p["name"] == name and p["surname"] == surname
        ),
        None,
    )
    if not person_details:
        return json.dumps({"error": f"Person {name} {surname} not found."})

    birth_year = person_details.get("born")
    payload = {
        "apikey": AGENTS_API_KEY,
        "name": name,
        "surname": surname,
        "birthYear": birth_year,
    }

    try:
        response = requests.post(ACCESS_LEVEL_URL, json=payload)
        response.raise_for_status()
        return json.dumps(
            {"person": f"{name} {surname}", "access_level": response.text.strip()}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- Tool Schemas & Maps ---

TOOLS_SEARCH = [
    {
        "type": "function",
        "function": {
            "name": "find_closest_person_to_power_plant",
            "description": "Zwraca dane osoby z listy, która przebywała najbliżej elektrowni. Nie podawaj żadnych argumentów, aby narzędzie przeszukało wszystkich użytkowników.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "surname": {"type": "string"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_access_level_for_person",
            "description": "Pobiera poziom dostępu dla określonej osoby na podstawie jej imienia i nazwiska.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "surname": {"type": "string"},
                },
                "required": ["name", "surname"],
            },
        },
    },
]

TOOLS_SEARCH_MAP = {
    "find_closest_person_to_power_plant": find_closest_person_to_power_plant,
    "get_access_level_for_person": get_access_level_for_person,
}
