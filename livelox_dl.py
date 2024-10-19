import requests
import sys
import json

def get_map(url: str):
    print("-- Livelox-dl --")
    print(f"Fetching map from: {url}")
    try:
        class_id = url.split("classId=")[1].split("&")[0]
        print(f"Found class_id: {class_id}")
    except:
        print(f"ERROR: could not find class_id. The URL must include classId=xxxxxx")
        sys.exit(1)
    print()
    print("Fetching map from the livelox server:")
    print(f"request.post('https://www.livelox.com/Data/ClassInfo')")
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Requested-With": "XMLHttpRequest"
        }
    data = {
                "classIds":[class_id],
                "courseIds":None,
                "relayLegs":[],
                "relayLegGroupIds":[],
                "includeMap":True,
                "includeCourses":True,
                "skipStoreInCache":False
    }
    res = requests.post("https://www.livelox.com/Data/ClassInfo", headers=headers, json=data)
    data = res.json()

    try:
        event_data = data["general"]
        blob_url = event_data["classBlobUrl"]
        print("ClassInfo fetched")
        try:
            print(f"Event name: {event_data['event']['name']}")
        except:
            print("Event name: unknown")
        print(f"Blob url: {blob_url}")
    except:
        print("Error: No blob url found in ClassInfo")
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }
    res = requests.get(blob_url, headers=headers)
    try:
        blob_data = res.json()
        map_data = blob_data["map"]
        map_url = map_data["url"]
        map_bound = map_data["boundingQuadrilateral"]["vertices"]
        map_resolution = map_data["resolution"]
        map_name = map_data["name"]
        image_format = map_data["imageFormat"].lower()
    except:
        print("Error: Could not parse livelox blob data")
        sys.exit(1)

    print(f"Map URL: {map_url}")
    print(f"Map Name: {map_name}")
        
    # Download the map file
    print(f"Downloading map from {map_url}")
    map_res = requests.get(map_url)

    # Save the map to a file (assuming it's an image)
    file_name = f"{map_name}.{image_format}"  # or other extension like .png based on the map type
    with open(file_name, "wb") as map_file:
        map_file.write(map_res.content)
    print(f"Map saved as {file_name}")



get_map("https://www.livelox.com/Viewer/Lillomarka-Nord-Sor/Herrer-15km?classId=862192&tab=player")