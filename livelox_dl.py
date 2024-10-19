import requests
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import argparse

# Define the Point and LatLon classes
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class LatLon:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

# Define the SpheroidProjection class
class SpheroidProjection:
    def __init__(self):
        self.pi = math.pi
        self._180 = 180.0
        self.rad = 6378137.0
        self.originShift = self.pi * self.rad
        self.pi_180 = self.pi / self._180

    def LatLonToMeters(self, latlon):
        x = latlon.lon * self.rad * self.pi_180
        y = math.log(math.tan((90 + latlon.lat) * self.pi_180 / 2)) * self.rad
        return Point(x, y)

# Matrix and transformation functions
def adj(m):
    m = np.array(m).flatten()
    return [
        m[4]*m[8] - m[5]*m[7], m[2]*m[7] - m[1]*m[8], m[1]*m[5] - m[2]*m[4],
        m[5]*m[6] - m[3]*m[8], m[0]*m[8] - m[2]*m[6], m[2]*m[3] - m[0]*m[5],
        m[3]*m[7] - m[4]*m[6], m[1]*m[6] - m[0]*m[7], m[0]*m[4] - m[1]*m[3],
    ]

def multmm(a, b):
    a = np.array(a).reshape(3, 3)
    b = np.array(b).reshape(3, 3)
    c = np.dot(a, b)
    return c.flatten()

def multmv(m, v):
    m = np.array(m).reshape(3, 3)
    v = np.array(v)
    result = np.dot(m, v)
    return result

def basisToPoints(x1, y1, x2, y2, x3, y3, x4, y4):
    m = [
        x1, x2, x3,
        y1, y2, y3,
        1,  1,  1
    ]
    v = multmv(adj(m), [x4, y4, 1])
    m = np.array(m).reshape(3, 3)
    diag_v = np.diag(v)
    m = np.dot(m, diag_v)
    return m.flatten()

def general2DProjection(
    x1s, y1s, x1d, y1d,
    x2s, y2s, x2d, y2d,
    x3s, y3s, x3d, y3d,
    x4s, y4s, x4d, y4d
):
    s = basisToPoints(x1s, y1s, x2s, y2s, x3s, y3s, x4s, y4s)
    d = basisToPoints(x1d, y1d, x2d, y2d, x3d, y3d, x4d, y4d)
    return multmm(d, adj(s))

def project(m, x, y):
    v = multmv(m, [x, y, 1])
    return [v[0] / v[2], v[1] / v[2]]

def cornerCalTransform(width, height, top_left_latlon, top_right_latlon, bottom_right_latlon, bottom_left_latlon):
    proj = SpheroidProjection()
    top_left_meters = proj.LatLonToMeters(top_left_latlon)
    top_right_meters = proj.LatLonToMeters(top_right_latlon)
    bottom_right_meters = proj.LatLonToMeters(bottom_right_latlon)
    bottom_left_meters = proj.LatLonToMeters(bottom_left_latlon)
    matrix3d = general2DProjection(
        top_left_meters.x, top_left_meters.y, 0, 0,
        top_right_meters.x, top_right_meters.y, width, 0,
        bottom_right_meters.x, bottom_right_meters.y, width, height,
        bottom_left_meters.x, bottom_left_meters.y, 0, height
    )
    def transform(latlon):
        meters = proj.LatLonToMeters(latlon)
        xy = project(matrix3d, meters.x, meters.y)
        return Point(xy[0], xy[1])
    return transform

def draw_route(img, orig_bounds, routes, res, event_name):
    canvas_width = round(img.width / res)
    canvas_height = round(img.height / res)
    
    # Resize the image directly
    img_resized = img.resize((canvas_width, canvas_height), resample=Image.LANCZOS)
    canvas = img_resized.convert('RGBA')
    
    # Convert bounds to LatLon objects
    bounds = [LatLon(p['latitude'], p['longitude']) for p in orig_bounds]
    
    # Create a second canvas to draw the route
    canvas2 = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
    draw2 = ImageDraw.Draw(canvas2)
    
    # Create the transform function
    transform = cornerCalTransform(
        canvas_width,
        canvas_height,
        bounds[3],
        bounds[2],
        bounds[1],
        bounds[0]
    )
    
    weight = 6
    circle_size = 30
    stroke_color = (160, 32, 240)  # RGB for purple
    text_color = (160, 32, 240)    # Black color for high contrast

    # Load a font for numbering controls
    try:
        font_size = 60  # Increased font size for better visibility
        font = ImageFont.truetype("/usr/share/fonts/arial.ttf", font_size)
        event_name_size = 60*3  # Increased font size for better visibility
        event_name_font = ImageFont.truetype("/usr/share/fonts/arial.ttf", event_name_size)
    except IOError:
        # If the font is not found, use the default font
        font = ImageFont.load_default()
    
    # For each route (could be multiple)
    for route in routes:
        # Transform the route control points
        route_pts = []
        for p in route:
            lat = p['control']['position']['latitude']
            lon = p['control']['position']['longitude']
            loc = LatLon(lat, lon)
            pt = transform(loc)
            route_pts.append(pt)
        
        # Precompute angles and trigonometric functions
        angles = []
        cos_sin_angles = []
        for i in range(len(route_pts) - 1):
            delta_x = route_pts[i+1].x - route_pts[i].x
            delta_y = route_pts[i+1].y - route_pts[i].y
            angle = math.atan2(delta_y, delta_x)
            angles.append(angle)
            cos_sin_angles.append((math.cos(angle), math.sin(angle)))

        # Draw lines between the controls
        for i, (pt_a, pt_b) in enumerate(zip(route_pts[:-1], route_pts[1:])):
            cos_angle, sin_angle = cos_sin_angles[i]
            # Adjust the line to not start and end inside the circle
            x_a = pt_a.x + circle_size * cos_angle
            y_a = pt_a.y + circle_size * sin_angle
            x_b = pt_b.x - circle_size * cos_angle
            y_b = pt_b.y - circle_size * sin_angle
            draw2.line([(x_a, y_a), (x_b, y_b)], fill=stroke_color, width=weight)
        
        # Draw the start triangle, circles, and numbers
        for i, pt in enumerate(route_pts):
            x = pt.x
            y = pt.y
            r = circle_size

            if i == 0:
                # Draw the start triangle
                if len(route_pts) > 1:
                    angle = angles[0]
                else:
                    angle = 0
                cos_angle = math.cos(angle)
                sin_angle = math.sin(angle)
                cos_angle_p2pi3 = math.cos(angle + 2 * math.pi / 3)
                sin_angle_p2pi3 = math.sin(angle + 2 * math.pi / 3)
                cos_angle_m2pi3 = math.cos(angle - 2 * math.pi / 3)
                sin_angle_m2pi3 = math.sin(angle - 2 * math.pi / 3)
                x1 = x + r * cos_angle
                y1 = y + r * sin_angle
                x2 = x + r * cos_angle_p2pi3
                y2 = y + r * sin_angle_p2pi3
                x3 = x + r * cos_angle_m2pi3
                y3 = y + r * sin_angle_m2pi3
                draw2.polygon([(x1, y1), (x2, y2), (x3, y3)], outline=stroke_color, fill=None, width=weight)
            else:
                # Draw the circle
                bbox = [x - r, y - r, x + r, y + r]
                draw2.ellipse(bbox, outline=stroke_color, width=weight)
                # For the last control, draw an additional inner circle
                if i == len(route_pts) -1:
                    r_inner = circle_size - 10
                    bbox_inner = [x - r_inner, y - r_inner, x + r_inner, y + r_inner]
                    draw2.ellipse(bbox_inner, outline=stroke_color, width=weight)
                else:
                    # Draw the control number
                    text = str(i)
                    # Get the bounding box of the text
                    bbox = draw2.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    # Position the text centered over the control symbol
                    text_x = 2*circle_size + x - text_width / 2
                    text_y = y - text_height / 2
                    draw2.text((text_x, text_y), text, fill=text_color, font=font)
    # Draw the event name
    # Get the bounding box of the text
    # if event_name:
    #     bbox = draw2.textbbox((0, 0), event_name, font=event_name_font)
    #     text_width = bbox[2] - bbox[0]
    #     text_height = bbox[3] - bbox[1]
    #     # Position the text centered over the control symbol
    #     text_x = canvas_width - text_width - 300
    #     text_y = 300
    #     draw2.text((text_x, text_y), event_name, fill=text_color, font=event_name_font)

    # Ensure both images are in 'RGBA' mode
    canvas = canvas.convert('RGBA')
    canvas2 = canvas2.convert('RGBA')
    
    # Overlay the route on the original image
    canvas = Image.alpha_composite(canvas, canvas2)
    return canvas, bounds

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
    print("Fetching map from the Livelox server:")
    print(f"request.post('https://www.livelox.com/Data/ClassInfo')")
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }
    data = {
        "classIds": [class_id],
        "courseIds": None,
        "relayLegs": [],
        "relayLegGroupIds": [],
        "includeMap": True,
        "includeCourses": True,
        "skipStoreInCache": False
    }
    res = requests.post("https://www.livelox.com/Data/ClassInfo", headers=headers, json=data)
    data = res.json()

    try:
        event_data = data["general"]
        blob_url = event_data["classBlobUrl"]
        event_name = ""
        print("ClassInfo fetched")
        try:
            event_name = event_data['event']['name']
            print(f"Event name: {event_name}")
        except:
            print("Event name: unknown")
        print(f"Blob URL: {blob_url}")
    except:
        print("Error: No blob URL found in ClassInfo")
        sys.exit(1)

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
        print("Error: Could not parse Livelox blob data")
        sys.exit(1)

    print(f"Map URL: {map_url}")
    print(f"Map Name: {map_name}")
        
    # Download the map file
    print(f"Downloading map from {map_url}")
    map_res = requests.get(map_url)

    # Save the map to a file
    file_name = f"{map_name}.{image_format}"
    with open(file_name, "wb") as map_file:
        map_file.write(map_res.content)
    print(f"Map saved as {file_name}")

    print(f"Drawing route on map")
    # Load the map image
    img = Image.open(file_name)

    # Extract the routes
    routes = [c['controls'] for c in blob_data['courses']]

    # Draw the route on the map
    canvas, bounds = draw_route(img, map_bound, routes, map_resolution, event_name)

    # Save the final image
    output_file = f"{map_name}_route.png"
    canvas.save(output_file)
    print(f"Route map saved as {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Download map from Livelox.')
    parser.add_argument('url', help='The Livelox URL of the event')
    args = parser.parse_args()
    get_map(args.url)

if __name__ == '__main__':
    main()
