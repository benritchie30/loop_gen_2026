import { useMapEvent } from 'react-leaflet';

/**
 * Handles map click events.
 * Only active in 'input' mode to allow pin placement.
 */
function MapClickHandler({ mode, onMapClick }) {
    useMapEvent('click', (e) => {
        if (mode === 'input' && onMapClick) {
            console.log(e.latlng.lat, e.latlng.lng);
            onMapClick({
                lat: e.latlng.lat,
                lng: e.latlng.lng
            });
        }
    });

    return null;
}

export default MapClickHandler;
