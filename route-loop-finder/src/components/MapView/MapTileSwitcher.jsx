import React, { useState } from 'react';
import { Layers } from 'lucide-react';
import './MapView.css'; // We'll add styles here

export const MAP_STYLES = {
    google: {
        name: 'Google Maps',
        url: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attribution: '&copy; Google'
    },
    osmCycle: {
        name: 'OSM Cycle',
        url: 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    },
    esriTopo: {
        name: 'ESRI Topo',
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    },
    usgs: {
        name: 'USGS Topo',
        url: 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',
        attribution: 'Tiles courtesy of the <a href="https://usgs.gov/">U.S. Geological Survey</a>'
    },
    light: {
        name: 'Light (Carto)',
        url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
    },
    dark: {
        name: 'Dark (Carto)',
        url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
    },
    satellite: {
        name: 'Satellite',
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    }
};

function MapTileSwitcher({ currentStyle, onStyleChange }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div
            className="map-tile-switcher"
            onMouseEnter={() => setIsOpen(true)}
            onMouseLeave={() => setIsOpen(false)}
        >
            <div className="map-tile-switcher__button">
                <Layers size={20} />
            </div>

            {isOpen && (
                <div className="map-tile-switcher__menu">
                    {Object.entries(MAP_STYLES).map(([key, style]) => (
                        <div
                            key={key}
                            className={`map-tile-switcher__option ${currentStyle === key ? 'active' : ''}`}
                            onClick={() => {
                                onStyleChange(key);
                                setIsOpen(false);
                            }}
                        >
                            <div className={`map-tile-switcher__preview map-tile-switcher__preview--${key}`}></div>
                            <span>{style.name}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default MapTileSwitcher;
