import { MousePointer, Layers, Pencil } from 'lucide-react';

const MODES = [
    { id: 'input', label: 'Input', icon: MousePointer },
    { id: 'display', label: 'Display', icon: Layers },
    { id: 'drawing', label: 'Draw', icon: Pencil }
];

/**
 * Mode switching buttons for input/display/drawing modes.
 */
function ModeIndicator({ mode, setMode }) {
    return (
        <div className="mode-controls">
            {MODES.map(({ id, label, icon: Icon }) => (
                <button
                    key={id}
                    className={`mode-controls__btn ${mode === id ? 'mode-controls__btn--active' : ''}`}
                    onClick={() => setMode(id)}
                >
                    <Icon size={14} style={{ marginRight: '4px' }} />
                    {label}
                </button>
            ))}
        </div>
    );
}

export default ModeIndicator;
