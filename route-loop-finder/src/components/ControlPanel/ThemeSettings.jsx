import React from 'react';
import './ControlPanel.css'; // Reusing control panel styles

export default function ThemeSettings({ primaryColor, setPrimaryColor }) {
    const handleColorChange = (e) => {
        setPrimaryColor(e.target.value);
    };

    return (
        <div className="control-panel__section">
            <div className="control-panel__section-title">Appearance</div>
            <div className="settings-grid">
                <label className="setting-item full-width">
                    <span>Theme Color (Hue)</span>
                    <input
                        type="range"
                        min="0"
                        max="360"
                        value={primaryColor}
                        onChange={handleColorChange}
                        style={{ width: '100%' }}
                    />
                    <div style={{
                        marginTop: '8px',
                        height: '12px',
                        borderRadius: '6px',
                        background: `hsl(${primaryColor}, 65%, 50%)`,
                        transition: 'background 0.1s ease'
                    }} />
                </label>
            </div>
        </div>
    );
}
