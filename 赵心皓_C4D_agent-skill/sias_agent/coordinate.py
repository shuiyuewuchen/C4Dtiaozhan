# -*- coding: utf-8 -*-
"""
坐标转换工具：WGS-84(GPS/模型输出) <-> GCJ-02(高德/腾讯地图火星坐标)。

为什么需要它：
  大模型给出的经纬度是 WGS-84（GPS 原始坐标），而国内高德/腾讯底图使用
  GCJ-02“火星坐标”，两者在中国大陆存在约 300~600 米的系统性偏移。
  若直接把 WGS-84 坐标画到高德底图上，标记点会“飘”。本模块负责转换。

算法为国内通用的公开 BD-09/GCJ-02 近似公式，仅用于校园周边点位的可视化对齐。
"""
import math

_A = 6378245.0          # 长半轴
_EE = 0.00669342162296594323  # 偏心率平方
_PI = 3.1415926535897932384626


def _out_of_china(lon: float, lat: float) -> bool:
    """粗略判断是否在国外（国外不做 GCJ-02 加密偏移）。"""
    return not (73.66 < lon < 135.05 and 3.86 < lat < 53.55)


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * _PI) + 40.0 * math.sin(y / 3.0 * _PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * _PI) + 320.0 * math.sin(y * _PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * _PI) + 40.0 * math.sin(x / 3.0 * _PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * _PI) + 300.0 * math.sin(x / 30.0 * _PI)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lon: float, lat: float):
    """WGS-84 -> GCJ-02，返回 (gcj_lon, gcj_lat)。"""
    if _out_of_china(lon, lat):
        return lon, lat
    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * _PI
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * _PI)
    dlon = (dlon * 180.0) / (_A / sqrtmagic * math.cos(radlat) * _PI)
    return lon + dlon, lat + dlat
