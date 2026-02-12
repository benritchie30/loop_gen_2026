import React, { useState } from 'react';
import { Layers } from 'lucide-react';
import './MapView.css'; // We'll add styles here

export const MAP_STYLES = {
    light: {
        name: 'Light',
        url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
    },
    dark: {
        name: 'Dark',
        url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
    },
    street: {
        name: 'Street',
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
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
