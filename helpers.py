from PIL import Image, ImageDraw
import math

# Define the LatLon class
class LatLon:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

# Define the cornerCalTransform function
def cornerCalTransform(width, height, p1, p2, p3, p4):
    # Assume p1, p2, p3, p4 are the four corners of the map image
    # and that we need to map lat/lon to x/y coordinates on the image.

    # For simplicity, we'll use linear interpolation between the corner points.

    # Get the bounds
    min_lat = min(p.latitude for p in [p1, p2, p3, p4])
    max_lat = max(p.latitude for p in [p1, p2, p3, p4])
    min_lon = min(p.longitude for p in [p1, p2, p3, p4])
    max_lon = max(p.longitude for p in [p1, p2, p3, p4])

    def transform(loc):
        # Normalize the latitudes and longitudes
        x_norm = (loc.longitude - min_lon) / (max_lon - min_lon)
        y_norm = (max_lat - loc.latitude) / (max_lat - min_lat)  # Inverted y-axis for images

        # Scale to the image dimensions
        x = x_norm * width
        y = y_norm * height

        return {'x': x, 'y': y}

    return transform

def drawRoute(img, origBounds, routes, res):
    # Create a canvas with scaled dimensions
    canvas_width = round(img.width / res)
    canvas_height = round(img.height / res)
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    draw = ImageDraw.Draw(canvas)

    # Map bounds into LatLon objects
    bounds = [LatLon(p['latitude'], p['longitude']) for p in origBounds]

    # Draw the image onto the canvas
    img_resized = img.resize((canvas_width, canvas_height), Image.ANTIALIAS)
    canvas.paste(img_resized, (0, 0))

    weight = 6  # Line width

    # Create a second canvas for drawing the routes
    canvas2 = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
    draw2 = ImageDraw.Draw(canvas2)

    # Get the transformation function
    transform = cornerCalTransform(
        canvas_width,
        canvas_height,
        bounds[3],
        bounds[2],
        bounds[1],
        bounds[0]
    )

    circle_size = 30
    stroke_color = 'purple'

    # For each route, draw the path
    for route in routes:
        # Transform route points to canvas coordinates
        routePts = []
        for p in route:
            loc = LatLon(
                p['control']['position']['latitude'],
                p['control']['position']['longitude']
            )
            pt = transform(loc)
            routePts.append(pt)

        for i in range(len(route) - 1):
            # Avoid division by zero
            if routePts[i]['x'] == routePts[i+1]['x']:
                routePts[i]['x'] -= 0.0001

            StartFromA = routePts[i]['x'] < routePts[i+1]['x']
            ptA = routePts[i] if StartFromA else routePts[i+1]
            ptB = routePts[i+1] if StartFromA else routePts[i]
            angle = math.atan((ptB['y'] - ptA['y']) / (ptB['x'] - ptA['x']))

            if i == 0:
                ptS = ptA if StartFromA else ptB
                direction = -1 if StartFromA else 1

                x1 = round(ptS['x'] - direction * circle_size * math.cos(angle))
                y1 = round(ptS['y'] - direction * circle_size * math.sin(angle))
                x2 = round(ptS['x'] - direction * circle_size * math.cos(angle + 2 * math.pi / 3))
                y2 = round(ptS['y'] - direction * circle_size * math.sin(angle + 2 * math.pi / 3))
                x3 = round(ptS['x'] - direction * circle_size * math.cos(angle - 2 * math.pi / 3))
                y3 = round(ptS['y'] - direction * circle_size * math.sin(angle - 2 * math.pi / 3))

                # Draw the starting triangle
                draw2.polygon([(x1, y1), (x2, y2), (x3, y3)], outline=stroke_color)

            # Draw the route line
            x_start = round(ptA['x'] + circle_size * math.cos(angle))
            y_start = round(ptA['y'] + circle_size * math.sin(angle))
            x_end = round(ptB['x'] - circle_size * math.cos(angle))
            y_end = round(ptB['y'] - circle_size * math.sin(angle))
            draw2.line([(x_start, y_start), (x_end, y_end)], fill=stroke_color, width=weight)

            # Draw circle at control point
            x_circle_center = routePts[i+1]['x']
            y_circle_center = routePts[i+1]['y']
            radius = circle_size
            bbox = [
                x_circle_center - radius,
                y_circle_center - radius,
                x_circle_center + radius,
                y_circle_center + radius
            ]
            draw2.ellipse(bbox, outline=stroke_color, width=weight)

            # Draw the final smaller circle
            if i == len(route) - 2:
                small_radius = circle_size - 10
                bbox = [
                    x_circle_center - small_radius,
                    y_circle_center - small_radius,
                    x_circle_center + small_radius,
                    y_circle_center + small_radius
                ]
                draw2.ellipse(bbox, outline=stroke_color, width=weight)

    # Adjust transparency and overlay the route canvas onto the main canvas
    canvas2.putalpha(int(0.7 * 255))  # Set global alpha to 0.7
    canvas.paste(canvas2, (0, 0), canvas2)

    return canvas, bounds

# Example usage:

# Load your map image (replace 'map_image.jpg' with your image file)
img = Image.open('kart.jpeg')

# Define the original bounds (replace with your actual bounds data)
origBounds = [
    {'latitude': 59.0, 'longitude': 10.0},  # Point 1
    {'latitude': 59.0, 'longitude': 11.0},  # Point 2
    {'latitude': 60.0, 'longitude': 11.0},  # Point 3
    {'latitude': 60.0, 'longitude': 10.0},  # Point 4
]

# Define the routes (replace with your actual routes data)
routes = [
    [
        {'control': {'position': {'latitude': 59.1, 'longitude': 10.1}}},
        {'control': {'position': {'latitude': 59.2, 'longitude': 10.2}}},
        {'control': {'position': {'latitude': 59.3, 'longitude': 10.3}}},
    ]
]

# Resolution factor
res = 1.0

# Call the drawRoute function
canvas, bounds = drawRoute(img, origBounds, routes, res)

# Save the resulting image
canvas.save('output_map_with_routes.png')
