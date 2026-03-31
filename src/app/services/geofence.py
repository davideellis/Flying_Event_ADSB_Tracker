from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_NM = 3440.065


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_r = radians(lat1)
    lat2_r = radians(lat2)

    a = sin(d_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_NM * c


def within_radius_nm(center_lat: float, center_lon: float, lat: float, lon: float, radius_nm: float) -> bool:
    return haversine_nm(center_lat, center_lon, lat, lon) <= radius_nm
