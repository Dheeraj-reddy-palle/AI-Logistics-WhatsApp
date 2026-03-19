import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchDrivers, fetchBookings } from '../services/api';
import { MapPin } from 'lucide-react';
import L from 'leaflet';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
let DefaultIcon = L.icon({
    iconUrl: icon, shadowUrl: iconShadow, iconSize: [25, 41], iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const DriverMap = () => {
    const [drivers, setDrivers] = useState([]);
    const [bookings, setBookings] = useState([]);

    useEffect(() => {
        const load = async () => { setDrivers(await fetchDrivers()); setBookings(await fetchBookings()); };
        load();
        const interval = setInterval(load, 5000);
        return () => clearInterval(interval);
    }, []);

    const center = [17.3850, 78.4867];

    return (
        <div className="glass-panel rounded-2xl overflow-hidden h-full flex flex-col relative border border-white/10 shadow-2xl">
            {/* Overlay Header */}
            <div className="absolute top-0 left-0 right-0 p-4 z-[1000] pointer-events-none flex justify-between items-start">
                <div className="bg-black/60 backdrop-blur-md border border-white/10 px-4 py-2 rounded-xl flex items-center gap-2 pointer-events-auto shadow-lg">
                    <MapPin className="w-5 h-5 text-indigo-400" />
                    <div>
                        <h2 className="text-sm font-bold text-white tracking-wide">Live Asset Tracking</h2>
                        <p className="text-[10px] text-indigo-300 font-mono">{drivers.length} Nodes Extracted</p>
                    </div>
                </div>
                
                <div className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2 pointer-events-auto backdrop-blur-md">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    GPS SYNCED
                </div>
            </div>

            <div className="flex-1 w-full relative z-[1]">
                <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%', background: '#09090b' }}>
                    <TileLayer
                        attribution=''
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    />
                    {drivers.map(driver => {
                        if (driver.last_known_lat && driver.last_known_lng) {
                            const assignedBookings = bookings.filter(b => b.driver_id === driver.id && b.status !== 'COMPLETED');
                            return (
                                <Marker key={driver.id} position={[driver.last_known_lat, driver.last_known_lng]}>
                                    <Popup className="premium-popup">
                                        <div className="font-bold text-slate-100">{driver.name}</div>
                                        <div className="text-xs text-slate-400 font-mono mt-1 border-b border-white/10 pb-2 mb-2">Class: {driver.vehicle_type}</div>
                                        {assignedBookings.length > 0 ? (
                                            <div className="text-[10px] font-bold text-blue-400 uppercase tracking-widest bg-blue-500/10 p-1 rounded">
                                                Active: {String(assignedBookings[0].id).substring(0,6)}
                                            </div>
                                        ) : (
                                            <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest bg-emerald-500/10 p-1 rounded">Transmission Ready</div>
                                        )}
                                    </Popup>
                                </Marker>
                            );
                        }
                        return null;
                    })}
                </MapContainer>
            </div>
            
            {/* Scanning Line overlay effect */}
            <div className="absolute inset-0 z-[500] pointer-events-none opacity-10 bg-[linear-gradient(to_bottom,transparent_0%,rgba(96,165,250,0.2)_50%,transparent_100%)] bg-[length:100%_4px] animate-[scan_8s_linear_infinite]"></div>
        </div>
    );
};

export default DriverMap;
