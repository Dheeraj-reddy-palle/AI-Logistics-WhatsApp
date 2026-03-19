import React, { useState, useEffect } from 'react';
import { fetchBookings, fetchDrivers, driverAcceptBooking, verifyWeight, updateDriverLocation } from '../services/api';
import { Terminal, Crosshair, Scale, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';

const DriverActions = () => {
    const [bookings, setBookings] = useState([]);
    const [drivers, setDrivers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState([]);

    const loadData = async () => { setBookings(await fetchBookings()); setDrivers(await fetchDrivers()); };
    useEffect(() => { loadData(); }, []);

    const addLog = (msg, type = 'info') => {
        setLogs(prev => [`[${new Date().toLocaleTimeString()}] [${type.toUpperCase()}] ${msg}`, ...prev].slice(0, 10));
    };

    const handleAction = async (fn, name) => {
        setLoading(true);
        try {
            await fn();
            addLog(`Executed: ${name}`, 'success');
            await loadData();
        } catch (error) {
            addLog(`${name} failed: ${error.message}`, 'error');
        }
        setLoading(false);
    };

    const pending = bookings.filter(b => b.status === "PENDING");
    const active = bookings.filter(b => b.status === "ASSIGNED" || b.status === "IN_TRANSIT");
    const available = drivers.filter(d => d.is_available);

    const [accD, setAccD] = useState(''); const [accB, setAccB] = useState('');
    const [wB, setWB] = useState(''); const [wInput, setWInput] = useState('');
    const [locB, setLocB] = useState(''); const [latI, setLatI] = useState(''); const [lngI, setLngI] = useState('');

    const Panel = ({ icon: Icon, title, children }) => (
        <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-3 hover:border-white/20 transition-colors">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2"><Icon className="w-4 h-4 text-blue-400" />{title}</h3>
            {children}
        </div>
    );

    const inputCls = "w-full p-2 bg-black/40 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors appearance-none";

    return (
        <div className="glass-panel rounded-2xl p-5 h-full flex flex-col gap-5">
            <div className="flex items-center gap-2 border-b border-white/5 pb-4">
                <Terminal className="w-5 h-5 text-fuchsia-400" />
                <h2 className="text-lg font-bold text-white tracking-wide">Command Overrides</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                <Panel icon={Crosshair} title="Force Assignment">
                    <select className={inputCls} value={accB} onChange={e=>setAccB(e.target.value)}>
                        <option value="">Select Payload</option>
                        {pending.map(b => <option key={b.id} value={b.id}>UUID-{b.id.substring(0,6)}</option>)}
                    </select>
                    <select className={inputCls} value={accD} onChange={e=>setAccD(e.target.value)}>
                        <option value="">Select Node</option>
                        {available.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                    <button className="mt-auto bg-blue-600/20 text-blue-400 hover:bg-blue-600 hover:text-white border border-blue-600/50 py-2 rounded-lg text-sm font-bold tracking-wider transition-all disabled:opacity-50"
                        disabled={!accB || !accD || loading} onClick={() => handleAction(()=>driverAcceptBooking(accD, accB), 'Assignment')}>
                        INITIATE SEQUENCE
                    </button>
                </Panel>

                <Panel icon={Scale} title="Mass Verification">
                    <select className={inputCls} value={wB} onChange={e=>setWB(e.target.value)}>
                        <option value="">Active Payload</option>
                        {active.map(b => <option key={b.id} value={b.id}>UUID-{b.id.substring(0,6)}</option>)}
                    </select>
                    <input type="number" className={inputCls} placeholder="Verified Mass (kg)" value={wInput} onChange={e=>setWInput(e.target.value)} />
                    <button className="mt-auto bg-amber-500/20 text-amber-400 hover:bg-amber-500 hover:text-white border border-amber-500/50 py-2 rounded-lg text-sm font-bold tracking-wider transition-all disabled:opacity-50"
                        disabled={!wB || !wInput || loading} onClick={() => handleAction(()=>verifyWeight(bookings.find(b=>b.id===wB).driver_id, wB, parseFloat(wInput)), 'Weight Sync')}>
                        OVERRIDE
                    </button>
                </Panel>

                <Panel icon={MapPin} title="Inject GPS">
                    <select className={inputCls} value={locB} onChange={e=>setLocB(e.target.value)}>
                        <option value="">Active Payload</option>
                        {active.map(b => <option key={b.id} value={b.id}>UUID-{b.id.substring(0,6)}</option>)}
                    </select>
                    <div className="flex gap-2">
                        <input className={inputCls} placeholder="LAT" value={latI} onChange={e=>setLatI(e.target.value)} />
                        <input className={inputCls} placeholder="LNG" value={lngI} onChange={e=>setLngI(e.target.value)} />
                    </div>
                    <button className="mt-auto bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-white border border-emerald-500/50 py-2 rounded-lg text-sm font-bold tracking-wider transition-all disabled:opacity-50"
                        disabled={!locB || !latI || !lngI || loading} onClick={() => handleAction(()=>updateDriverLocation(bookings.find(b=>b.id===locB).driver_id, locB, parseFloat(latI), parseFloat(lngI)), 'GPS Inject')}>
                        SPOOF LOCATION
                    </button>
                </Panel>

            </div>

            <div className="mt-auto bg-black/60 rounded-xl border border-white/5 p-3 flex-1 overflow-auto font-mono text-xs">
                {logs.length === 0 ? <div className="text-slate-600">No recent mutations executed.</div> : 
                    logs.map((L, i) => (
                        <motion.div initial={{opacity:0, x:-5}} animate={{opacity:1, x:0}} key={i} className={`mb-1 ${L.includes('ERROR') ? 'text-red-400' : 'text-emerald-400'}`}>
                            {L}
                        </motion.div>
                    ))}
            </div>
        </div>
    );
};

export default DriverActions;
