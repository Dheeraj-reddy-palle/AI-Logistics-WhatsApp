import React, { useState, useEffect } from 'react';
import { fetchBookings, fetchDrivers, driverAcceptBooking, verifyWeight, updateDriverLocation } from '../services/api';
import { Truck, Scale, MapPin, Check } from 'lucide-react';

const DriverPanel = () => {
    const [bookings, setBookings] = useState([]);
    const [drivers, setDrivers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [log, setLog] = useState('');

    const loadData = async () => {
        setBookings(await fetchBookings());
        setDrivers(await fetchDrivers());
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleAction = async (actionFn, actionName) => {
        setLoading(true);
        try {
            const res = await actionFn();
            setLog(`[SUCCESS] ${actionName}: ${JSON.stringify(res)}`);
            await loadData();
        } catch (error) {
            setLog(`[ERROR] ${actionName}: ${error.response?.data?.detail || error.message}`);
        }
        setLoading(false);
    };

    const ActionCard = ({ title, description, icon: Icon, children }) => (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4">
            <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-50 text-blue-600 rounded-lg"><Icon className="w-5 h-5"/></div>
                <div>
                    <h3 className="font-bold text-slate-800">{title}</h3>
                    <p className="text-xs text-slate-500">{description}</p>
                </div>
            </div>
            <div className="flex-1 flex flex-col gap-3">
                {children}
            </div>
        </div>
    );

    const pendingBookings = bookings.filter(b => b.status === "PENDING");
    const activeBookings = bookings.filter(b => b.status === "ASSIGNED" || b.status === "IN_TRANSIT");
    const availableDrivers = drivers.filter(d => d.is_available);

    const [selectedAcceptDriver, setSelectedAcceptDriver] = useState('');
    const [selectedAcceptBooking, setSelectedAcceptBooking] = useState('');
    
    const [selectedWeightBooking, setSelectedWeightBooking] = useState('');
    const [weightInput, setWeightInput] = useState('');

    const [selectedLocationBooking, setSelectedLocationBooking] = useState('');
    const [latInput, setLatInput] = useState('');
    const [lngInput, setLngInput] = useState('');

    return (
        <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-800">Driver Simulation Panel</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Accept Booking */}
                <ActionCard title="Accept Delivery" description="Simulate a driver claiming a pending webhook order." icon={Check}>
                    <select className="p-2 border rounded-lg text-sm bg-slate-50" value={selectedAcceptBooking} onChange={e => setSelectedAcceptBooking(e.target.value)}>
                        <option value="">Select Pending Booking</option>
                        {pendingBookings.map(b => <option key={b.id} value={b.id}>{b.id.substring(0,8)} - {b.declared_weight}kg</option>)}
                    </select>
                    <select className="p-2 border rounded-lg text-sm bg-slate-50" value={selectedAcceptDriver} onChange={e => setSelectedAcceptDriver(e.target.value)}>
                        <option value="">Select Available Driver</option>
                        {availableDrivers.map(d => <option key={d.id} value={d.id}>{d.name} ({d.vehicle_type})</option>)}
                    </select>
                    <button 
                        disabled={!selectedAcceptBooking || !selectedAcceptDriver || loading}
                        className="mt-auto bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50 transition"
                        onClick={() => handleAction(() => driverAcceptBooking(selectedAcceptDriver, selectedAcceptBooking), 'Accept Booking')}
                    >Trigger Assignment</button>
                </ActionCard>

                {/* Verify Weight */}
                <ActionCard title="Verify Weight" description="Override the customer's declared weight dynamically." icon={Scale}>
                    <select className="p-2 border rounded-lg text-sm bg-slate-50" value={selectedWeightBooking} onChange={e => setSelectedWeightBooking(e.target.value)}>
                        <option value="">Select Active Booking</option>
                        {activeBookings.map(b => <option key={b.id} value={b.id}>{b.id.substring(0,8)} (Driver: {drivers.find(d=>d.id===b.driver_id)?.name})</option>)}
                    </select>
                    <input 
                        type="number" className="p-2 border rounded-lg text-sm bg-slate-50" placeholder="New Weight (kg)" 
                        value={weightInput} onChange={e => setWeightInput(e.target.value)}
                    />
                    <button 
                        disabled={!selectedWeightBooking || !weightInput || loading}
                        className="mt-auto bg-amber-500 hover:bg-amber-600 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50 transition"
                        onClick={() => {
                            const booking = bookings.find(b => b.id === selectedWeightBooking);
                            handleAction(() => verifyWeight(booking.driver_id, selectedWeightBooking, parseFloat(weightInput)), 'Update Weight');
                        }}
                    >Update Verified Mass</button>
                </ActionCard>

                {/* Update Location */}
                <ActionCard title="Update Location" description="Transmit real-time geographical ping to webhook." icon={MapPin}>
                    <select className="p-2 border rounded-lg text-sm bg-slate-50" value={selectedLocationBooking} onChange={e => setSelectedLocationBooking(e.target.value)}>
                        <option value="">Select Active Booking</option>
                        {activeBookings.map(b => <option key={b.id} value={b.id}>{b.id.substring(0,8)}</option>)}
                    </select>
                    <div className="flex gap-2">
                        <input type="number" step="0.0001" className="w-1/2 p-2 border rounded-lg text-sm bg-slate-50" placeholder="Latitude" value={latInput} onChange={e => setLatInput(e.target.value)} />
                        <input type="number" step="0.0001" className="w-1/2 p-2 border rounded-lg text-sm bg-slate-50" placeholder="Longitude" value={lngInput} onChange={e => setLngInput(e.target.value)} />
                    </div>
                    <button 
                        disabled={!selectedLocationBooking || !latInput || !lngInput || loading}
                        className="mt-auto bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50 transition"
                        onClick={() => {
                            const booking = bookings.find(b => b.id === selectedLocationBooking);
                            handleAction(() => updateDriverLocation(booking.driver_id, selectedLocationBooking, parseFloat(latInput), parseFloat(lngInput)), 'Update GPS Payload');
                        }}
                    >Transmit Ping</button>
                </ActionCard>

            </div>

            <div className="bg-slate-900 rounded-xl p-4 flex flex-col h-48 overflow-y-auto w-full shadow-inner border border-slate-700">
                <h4 className="text-slate-400 font-mono text-xs mb-2 uppercase tracking-wider">REST Sandbox Terminal</h4>
                <div className="text-emerald-400 font-mono text-sm whitespace-pre-wrap">
                    {log || "> Awaiting instruction..."}
                </div>
            </div>
        </div>
    );
};

export default DriverPanel;
