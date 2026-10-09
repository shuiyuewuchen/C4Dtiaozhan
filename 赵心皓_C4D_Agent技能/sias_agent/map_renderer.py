# -*- coding: utf-8 -*-
"""
把“本地模型生成的地点列表”渲染成一个自包含、可交互的 Leaflet HTML 地图。

特性：
  - 可缩放、可拖拽、点击标记弹出详情（名称/类别/坐标/简介/天气）
  - 多底图切换：CartoDB(默认,WGS-84) / OpenStreetMap / 高德(GCJ-02, 已做坐标纠偏)
  - 按类别着色的圆形标记，SIAS 主校区用特殊图标
  - 全部数据内嵌在 HTML 里，双击即可在浏览器打开
"""
import json
import os

from . import config
from .coordinate import wgs84_to_gcj02

CATEGORY_COLOR = {
    "campus": "#d62728",
    "food": "#ff7f0e",
    "scenic": "#2ca02c",
    "transport": "#1f77b4",
    "shopping": "#9467bd",
    "sports": "#17becf",
    "other": "#7f7f7f",
}


def _validate_locations(locations: list) -> list:
    """清洗并兜底：坐标缺失/离谱时吸附到 SIAS 中心附近，保证地图可用。"""
    cleaned = []
    for i, loc in enumerate(locations):
        try:
            lat = float(loc.get("latitude", loc.get("lat")))
            lon = float(loc.get("longitude", loc.get("lon", loc.get("lng"))))
        except (TypeError, ValueError):
            lat, lon = config.SIAS_LAT, config.SIAS_LON
        # 离谱坐标兜底：拉回 SIAS 中心附近（轻微随机偏移，避免全部重叠）
        if not (34.25 < lat < 34.55 and 113.55 < lon < 113.95):
            lat = config.SIAS_LAT + (i * 0.0015)
            lon = config.SIAS_LON + (i * 0.0015)
        cleaned.append({
            "name": str(loc.get("name", f"地点{i+1}")),
            "name_zh": str(loc.get("name_zh", loc.get("name", f"地点{i+1}"))),
            "category": str(loc.get("category", "other")),
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "description": str(loc.get("description", "")),
            "weather": loc.get("weather", ""),
        })
    return cleaned


def render_map(locations: list, out_path: str, title: str = "SIAS University 周边地图",
               model_label: str = "") -> str:
    locs = _validate_locations(locations)

    # 为高德层准备 GCJ-02 坐标（WGS-84 原始坐标用于 CartoDB/OSM）
    for l in locs:
        gj_lon, gj_lat = wgs84_to_gcj02(l["lon"], l["lat"])
        l["gcj_lat"] = round(gj_lat, 5)
        l["gcj_lon"] = round(gj_lon, 5)

    data_js = json.dumps(locs, ensure_ascii=False)
    center = [config.SIAS_LAT, config.SIAS_LON]
    gj_center = wgs84_to_gcj02(config.SIAS_LON, config.SIAS_LAT)

    html = _HTML_TEMPLATE.replace("__DATA__", data_js) \
        .replace("__TITLE__", title) \
        .replace("__MODEL_LABEL__", model_label) \
        .replace("__CENTER__", json.dumps(center)) \
        .replace("__GCJ_CENTER__", json.dumps([gj_center[1], gj_center[0]])) \
        .replace("__ZOOM__", str(config.MAP_DEFAULT_ZOOM)) \
        .replace("__COLORS__", json.dumps(CATEGORY_COLOR, ensure_ascii=False))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>__TITLE__</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body{margin:0;height:100%;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}
  #map{position:absolute;inset:0;}
  #banner{position:absolute;top:10px;left:50%;transform:translateX(-50%);z-index:1000;
    background:rgba(255,255,255,.92);padding:8px 14px;border-radius:8px;
    box-shadow:0 2px 8px rgba(0,0,0,.2);font-size:13px;line-height:1.5;max-width:90%;}
  #banner b{color:#b3242b;}
  .leaflet-popup-content{font-size:13px;line-height:1.6;}
  .cat{display:inline-block;padding:1px 7px;border-radius:10px;color:#fff;font-size:11px;}
</style>
</head>
<body>
<div id="banner"><b>__TITLE__</b><br/>
<span style="color:#555">地点数据由本地模型生成 · __MODEL_LABEL__ · 点击标记查看详情，右上角切换底图</span></div>
<div id="map"></div>
<script>
const DATA = __DATA__;
const COLORS = __COLORS__;
const map = L.map('map').setView(__CENTER__, __ZOOM__);

// 底图（WGS-84）
const carto = L.tileLayer('https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{
  maxZoom:20, attribution:'&copy; OpenStreetMap &copy; CARTO'});
const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
  maxZoom:19, attribution:'&copy; OpenStreetMap'});
// 高德底图（GCJ-02），中心与标记均用纠偏后的坐标
const gcjGroup = L.layerGroup();
const amap = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',{
  subdomains:['1','2','3','4'], maxZoom:20, attribution:'&copy; 高德地图'});
amap.addTo(gcjGroup);

carto.addTo(map);

function markerIcon(color, campus){
  return L.divIcon({className:'', html:
    '<div style="width:'+(campus?22:14)+'px;height:'+(campus?22:14)+'px;border-radius:50% 50% 50% 0;'+
    'transform:rotate(-45deg);background:'+color+';border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);"></div>',
    iconSize:[campus?22:14,campus?22:14], iconAnchor:[campus?11:7,campus?11:7]});
}

DATA.forEach(d=>{
  const color = COLORS[d.category] || COLORS.other;
  const campus = (d.category==='campus');
  const popup = `<b>${d.name_zh}</b> <span class="cat" style="background:${color}">${d.category}</span><br/>
    <span style="color:#888">${d.name}</span><br/>
    📍 ${d.lat.toFixed(4)}, ${d.lon.toFixed(4)} (WGS-84)<br/>
    ${d.description||''}${d.weather?('<br/>🌤 '+d.weather):''}`;
  // WGS-84 层
  L.marker([d.lat,d.lon],{icon:markerIcon(color,campus)}).bindPopup(popup).bindTooltip(d.name_zh).addTo(carto);
  L.marker([d.lat,d.lon],{icon:markerIcon(color,campus)}).bindPopup(popup).bindTooltip(d.name_zh).addTo(osm);
  // GCJ-02 层（高德）
  L.marker([d.gcj_lat,d.gcj_lon],{icon:markerIcon(color,campus)}).bindPopup(popup).bindTooltip(d.name_zh).addTo(gcjGroup);
});

L.control.layers({
  "CartoDB (WGS-84)": carto,
  "OpenStreetMap (WGS-84)": osm,
  "高德地图 (GCJ-02)": gcjGroup
}, {}, {collapsed:false}).addTo(map);
</script>
</body>
</html>
"""
