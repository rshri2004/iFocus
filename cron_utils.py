from datetime import timedelta
from collections import Counter
import numpy as np
from scipy.ndimage import gaussian_filter

def calculate_total_duration(data):
    """
    Calculate the total time spent based on focus data entries.
    The `data` parameter should be a list of FocusData objects.
    Assumes data is sorted by timestamp.
    """
    if len(data) < 2:
        return 0  # Not enough data to calculate duration

    # Sort the data by timestamp to ensure correct calculations
    sorted_data = sorted(data, key=lambda entry: entry.timestamp)

    total_duration = timedelta(0)
    for i in range(1, len(sorted_data)):
        # Add the time difference between consecutive entries
        total_duration += sorted_data[i].timestamp - sorted_data[i - 1].timestamp

    return total_duration.total_seconds()  # Return in seconds

def calculate_distraction_time(data):
    """
    Calculate the total distraction time from focus data.
    The `data` parameter should be a list of FocusData objects.
    """
    distraction_time = timedelta(0)
    previous_time = None

    for entry in data:
        if entry.outside:
            if previous_time:
                distraction_time += entry.timestamp - previous_time
        previous_time = entry.timestamp

    return distraction_time.total_seconds()  # Return in seconds


def calculate_focus_time(data, total_duration):
    """
    Calculate the total focus time from focus data.
    The `data` parameter should be a list of FocusData objects.
    """
    distraction_time = calculate_distraction_time(data)
    focus_time = total_duration - distraction_time
    return focus_time


def calculate_focus_distribution(data):
    """
    Calculate the focus distribution based on x and y coordinates.
    The `data` parameter should be a list of FocusData objects.
    Returns a dictionary summarizing the focus intensity in different regions.
    """
    total_points = len(data)
    if total_points == 0:
        return {"top_left": 0, "top_right": 0, "bottom_left": 0, "bottom_right": 0}

    # Divide the screen into quadrants
    top_left = sum(1 for entry in data if entry.x_coord < 0.5 and entry.y_coord > 0.5)
    top_right = sum(1 for entry in data if entry.x_coord >= 0.5 and entry.y_coord > 0.5)
    bottom_left = sum(1 for entry in data if entry.x_coord < 0.5 and entry.y_coord <= 0.5)
    bottom_right = sum(1 for entry in data if entry.x_coord >= 0.5 and entry.y_coord <= 0.5)

    return {
        "top_left": top_left / total_points,
        "top_right": top_right / total_points,
        "bottom_left": bottom_left / total_points,
        "bottom_right": bottom_right / total_points,
    }


def identify_focus_hotspots(data, grid_size=10):
    """
    Identify the areas with the highest concentration of focus points.
    The `data` parameter should be a list of FocusData objects.
    Returns the grid cell with the most focus points.
    """
    if not data:
        return None

    # Normalize x and y coordinates to grid_size
    focus_points = [(int(entry.x_coord * grid_size), int(entry.y_coord * grid_size)) for entry in data]

    # Count occurrences of focus points in each grid cell
    point_counts = Counter(focus_points)

    # Find the most focused grid cell
    hotspot, count = point_counts.most_common(1)[0]
    return {
        "hotspot": hotspot,
        "focus_intensity": count,
        "total_points": len(data),
        "hotspot_ratio": count / len(data),
    }


def calculate_focus_transitions(data, threshold=0.1):
    """
    Calculate the number of transitions between focus regions.
    The `data` parameter should be a list of FocusData objects.
    """
    if len(data) < 2:
        return 0

    transitions = 0
    previous_x, previous_y = data[0].x_coord, data[0].y_coord

    for entry in data[1:]:
        if abs(entry.x_coord - previous_x) > threshold or abs(entry.y_coord - previous_y) > threshold:
            transitions += 1
        previous_x, previous_y = entry.x_coord, entry.y_coord

    return transitions


def summarize_focus_behavior(data):
    """
    Summarize the focus behavior based on the focus data.
    Combines multiple metrics into a textual summary.
    The `data` parameter should be a list of FocusData objects.
    """
    total_duration = calculate_total_duration(data)
    distraction_time = calculate_distraction_time(data)
    focus_time = calculate_focus_time(data, total_duration)
    focus_distribution = calculate_focus_distribution(data)
    hotspots = identify_focus_hotspots(data)
    transitions = calculate_focus_transitions(data)

    try:
        summary = (
            f"Total duration: {total_duration} seconds.\n"
            f"Focus time: {focus_time:.2f} seconds ({(focus_time / total_duration) * 100:.2f}%).\n"
            f"Distraction time: {distraction_time:.2f} seconds ({(distraction_time / total_duration) * 100:.2f}%).\n"
            f"Focus distribution:\n"
            f"  - Top-left: {focus_distribution['top_left'] * 100:.2f}%\n"
            f"  - Top-right: {focus_distribution['top_right'] * 100:.2f}%\n"
            f"  - Bottom-left: {focus_distribution['bottom_left'] * 100:.2f}%\n"
            f"  - Bottom-right: {focus_distribution['bottom_right'] * 100:.2f}%\n"
        )
    except Exception as e:
        print(f"Error genearting summary: {str(e)}")
        print(f"Focus time: {focus_time:.2f} Total duration: {total_duration} seconds.")
        return None

    if hotspots:
        summary += (
            f"The most focused region (hotspot) is grid cell {hotspots['hotspot']} "
            f"with {hotspots['focus_intensity']} points ({hotspots['hotspot_ratio'] * 100:.2f}% of total points).\n"
        )

    summary += f"Number of focus transitions: {transitions}.\n"

    return summary
