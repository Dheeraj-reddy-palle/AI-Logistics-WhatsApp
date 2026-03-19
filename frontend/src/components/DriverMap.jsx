import React, { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchDrivers, fetchBookings } from '../services/api';
import { MapPin, Navigation, Truck, Package } from 'lucide-react';
import L from 'leaflet';

// Custom SVG marker icons
const createIcon = (color, emoji) => L.divIcon({
    className: 'custom-marker',
    html: `<div style="
        width: 36px; height: 36px; 
        background: ${color}; 
        border: 3px solid white; 
        border-radius: 50%; 
        box-shadow: 0 4px 12px ${color}88, 0 0 20px ${color}44;
        display: flex; align-items: center; justify-content: center;
        font-size: 16px; color: white; font-weight: bold;
    ">${emoji}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20]
});

const driverIcon = createIcon('#6366f1', '🚛');
const pickupIcon = createIcon('#22c55e', '📍');
const dropIcon = createIcon('#ef4444', '🏁');

// Component to auto-fit map bounds
const FitBounds = ({ positions }) => {
    const map = useMap();
    useEffect(() => {
        if (positions.length > 1) {
            const bounds = L.latLngBounds(positions);
            map.fitBounds(bounds, { padding: [40, 40] });
        }
    }, [positions, map]);
    return null;
};

// Fetch driving route from OSRM (free, no API key)
const fetchRoute = async (startLat, startLng, endLat, endLng) => {
    try {
        const url = `https://router.project-osrm.org/route/v1/driving/${startLng},${startLat};${endLng},${endLat}?overview=full&geometries=geojson`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.routes && data.routes.length > 0) {
            const coords = data.routes[0].geometry.coordinates;
            const distance = (data.routes[0].distance / 1000).toFixed(1);
            const duration = Math.round(data.routes[0].duration / 60);
            return {
                path: coords.map(c => [c[1], c[0]]), // [lat, lng]
                distance,
                duration
            };
        }
    } catch (e) {
        console.warn('OSRM route fetch failed:', e);
    }
    return null;
};

const DriverMap = () => {
    const [drivers, setDrivers] = useState([]);
    const [bookings, setBookings] = useState([]);
    const [routes, setRoutes] = useState({});

    // Load data
    useEffect(() => {
        const load = async () => {
            setDrivers(await fetchDrivers());
            setBookings(await fetchBookings());
        };
        load();
        const interval = setInterval(load, 5000);
        return () => clearInterval(interval);
    }, []);

    // Fetch routes for active bookings
    useEffect(() => {
        const loadRoutes = async () => {
            const activeBookings = bookings.filter(b =>
                b.pickup_lat && b.pickup_lng && b.drop_lat && b.drop_lng &&
                ['PENDING', 'ASSIGNED', 'DRIVER_ASSIGNED', 'IN_TRANSIT'].includes(b.status)
            );
            const newRoutes = {};
            for (const b of activeBookings) {
                if (!routes[b.id]) {
                    const route = await fetchRoute(b.pickup_lat, b.pickup_lng, b.drop_lat, b.drop_lng);
                    if (route) newRoutes[b.id] = route;
                }
            }
            if (Object.keys(newRoutes).length > 0) {
                setRoutes(prev => ({ ...prev, ...newRoutes }));
            }
        };
        if (bookings.length > 0) loadRoutes();
    }, [bookings]);

    const center = [17.3850, 78.4867]; // Hyderabad default

    // Collect all positions for auto-fit
    const allPositions = [];
    drivers.forEach(d => {
        if (d.last_known_lat && d.last_known_lng) allPositions.push([d.last_known_lat, d.last_known_lng]);
    });
    bookings.forEach(b => {
        if (b.pickup_lat && b.pickup_lng) allPositions.push([b.pickup_lat, b.pickup_lng]);
        if (b.drop_lat && b.drop_lng) allPositions.push([b.drop_lat, b.drop_lng]);
    });

    const activeBookings = bookings.filter(b =>
        ['PENDING', 'ASSIGNED', 'DRIVER_ASSIGNED', 'IN_TRANSIT'].includes(b.status)
    );

    // Route colors per booking
    const routeColors = ['#6366f1', '#22d3ee', '#f59e0b', '#ec4899', '#10b981'];

    return (
        <div className="glass-panel rounded-xl sm:rounded-2xl overflow-hidden h-full flex flex-col relative border border-white/10 shadow-2xl">
            {/* Overlay Header */}
            <div className="absolute top-0 left-0 right-0 p-3 sm:p-4 z-[1000] pointer-events-none flex justify-between items-start">
                <div className="bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1.5 sm:px-4 sm:py-2 rounded-xl flex items-center gap-2 pointer-events-auto shadow-lg">
                    <MapPin className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-400" />
                    <div>
                        <h2 className="text-xs sm:text-sm font-bold text-white tracking-wide">Live Asset Tracking</h2>
                        <p className="text-[9px] sm:text-[10px] text-indigo-300 font-mono">
                            {drivers.length} Drivers • {activeBookings.length} Active Routes
                        </p>
                    </div>
                </div>
                
                <div className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-1 sm:px-3 sm:py-1.5 rounded-lg text-[10px] sm:text-xs font-mono font-bold flex items-center gap-1.5 pointer-events-auto backdrop-blur-md">
                    <span className="relative flex h-1.5 w-1.5 sm:h-2 sm:w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 sm:h-2 sm:w-2 bg-emerald-500"></span>
                    </span>
                    OSRM LIVE
                </div>
            </div>

            {/* Route Legend */}
            {activeBookings.length > 0 && (
                <div className="absolute bottom-2 left-2 sm:bottom-4 sm:left-4 z-[1000] pointer-events-auto">
                    <div className="bg-black/70 backdrop-blur-md border border-white/10 rounded-lg px-2.5 py-2 sm:px-3 sm:py-2.5 space-y-1">
                        <p className="text-[9px] sm:text-[10px] text-slate-400 font-mono font-bold uppercase tracking-wider mb-1">Routes</p>
                        {activeBookings.slice(0, 5).map((b, i) => (
                            <div key={b.id} className="flex items-center gap-2 text-[10px] sm:text-xs">
                                <div className="w-3 h-0.5 rounded" style={{ backgroundColor: routeColors[i % routeColors.length] }}></div>
                                <span className="text-slate-300 font-mono">UUID-{String(b.id).substring(0,6)}</span>
                                {routes[b.id] && (
                                    <span className="text-slate-500">{routes[b.id].distance}km • {routes[b.id].duration}min</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="flex-1 w-full relative z-[1]">
                <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%', background: '#09090b' }}>
                    <TileLayer
                        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    />

                    {allPositions.length > 1 && <FitBounds positions={allPositions} />}

                    {/* Driving Routes (OSRM polylines) */}
                    {activeBookings.map((b, i) => {
                        const route = routes[b.id];
                        if (!route) return null;
                        return (
                            <Polyline
                                key={`route-${b.id}`}
                                positions={route.path}
                                pathOptions={{
                                    color: routeColors[i % routeColors.length],
                                    weight: 4,
                                    opacity: 0.8,
                                    dashArray: b.status === 'PENDING' ? '8 8' : null,
                                    lineCap: 'round',
                                    lineJoin: 'round'
                                }}
                            />
                        );
                    })}

                    {/* Pickup Markers (green) */}
                    {activeBookings.map(b => {
                        if (!b.pickup_lat || !b.pickup_lng) return null;
                        return (
                            <Marker key={`pickup-${b.id}`} position={[b.pickup_lat, b.pickup_lng]} icon={pickupIcon}>
                                <Popup>
                                    <div className="font-bold text-emerald-400 text-xs">📍 PICKUP</div>
                                    <div className="text-[10px] text-slate-300 font-mono mt-1">
                                        {b.pickup_lat.toFixed(4)}, {b.pickup_lng.toFixed(4)}
                                    </div>
                                    <div className="text-[10px] text-slate-400 mt-1">
                                        Booking: UUID-{String(b.id).substring(0,6)}
                                    </div>
                                </Popup>
                            </Marker>
                        );
                    })}

                    {/* Drop Markers (red) */}
                    {activeBookings.map(b => {
                        if (!b.drop_lat || !b.drop_lng) return null;
                        return (
                            <Marker key={`drop-${b.id}`} position={[b.drop_lat, b.drop_lng]} icon={dropIcon}>
                                <Popup>
                                    <div className="font-bold text-red-400 text-xs">🏁 DROP-OFF</div>
                                    <div className="text-[10px] text-slate-300 font-mono mt-1">
                                        {b.drop_lat.toFixed(4)}, {b.drop_lng.toFixed(4)}
                                    </div>
                                    {routes[b.id] && (
                                        <div className="text-[10px] text-blue-400 mt-1">
                                            {routes[b.id].distance}km • ~{routes[b.id].duration} min drive
                                        </div>
                                    )}
                                </Popup>
                            </Marker>
                        );
                    })}

                    {/* Driver Markers (purple) */}
                    {drivers.map(driver => {
                        if (!driver.last_known_lat || !driver.last_known_lng) return null;
                        const assignedBookings = bookings.filter(b => b.driver_id === driver.id && b.status !== 'COMPLETED');
                        return (
                            <Marker key={`driver-${driver.id}`} position={[driver.last_known_lat, driver.last_known_lng]} icon={driverIcon}>
                                <Popup>
                                    <div className="font-bold text-indigo-400 text-xs">🚛 {driver.name}</div>
                                    <div className="text-[10px] text-slate-400 font-mono mt-1 border-b border-white/10 pb-1 mb-1">
                                        {driver.vehicle_type} • {driver.last_known_lat.toFixed(4)}, {driver.last_known_lng.toFixed(4)}
                                    </div>
                                    {assignedBookings.length > 0 ? (
                                        <div className="text-[10px] font-bold text-blue-400 uppercase tracking-widest bg-blue-500/10 p-1 rounded">
                                            Active: UUID-{String(assignedBookings[0].id).substring(0,6)}
                                        </div>
                                    ) : (
                                        <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest bg-emerald-500/10 p-1 rounded">Available</div>
                                    )}
                                </Popup>
                            </Marker>
                        );
                    })}
                </MapContainer>
            </div>
            
            {/* Scanning Line overlay effect */}
            <div className="absolute inset-0 z-[500] pointer-events-none opacity-10 bg-[linear-gradient(to_bottom,transparent_0%,rgba(96,165,250,0.2)_50%,transparent_100%)] bg-[length:100%_4px] animate-[scan_8s_linear_infinite]"></div>
        </div>
    );
};

export default DriverMap;
