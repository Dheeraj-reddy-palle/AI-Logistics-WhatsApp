import React, { useState, useEffect } from 'react';
import { fetchBookings } from '../services/api';
import { Search, Hash } from 'lucide-react';
import { cn } from '../utils';

const BookingsTable = () => {
    const [bookings, setBookings] = useState([]);
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState('ALL');

    useEffect(() => {
        const load = async () => setBookings(await fetchBookings());
        load();
        const interval = setInterval(load, 5000);
        return () => clearInterval(interval);
    }, []);

    const filtered = bookings.filter(b => {
        const matchSearch = String(b.id).toLowerCase().includes(search.toLowerCase()) || String(b.customer_phone).includes(search);
        const matchStatus = filter === 'ALL' || b.status === filter;
        return matchSearch && matchStatus;
    });

    const statusColors = {
        'PENDING': 'bg-slate-500/10 text-slate-400 border border-slate-500/20',
        'ASSIGNED': 'bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse',
        'IN_TRANSIT': 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
        'COMPLETED': 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
        'CANCELLED': 'bg-red-500/10 text-red-400 border border-red-500/20'
    };

    return (
        <div className="glass-panel rounded-xl sm:rounded-2xl overflow-hidden flex flex-col h-auto sm:h-[400px]">
            <div className="p-5 border-b border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                    <Hash className="w-5 h-5 text-indigo-400" />
                    <h2 className="text-lg font-bold text-white tracking-wide">Payload Manifests</h2>
                </div>
                <div className="flex items-center gap-3 w-full sm:w-auto">
                    <div className="relative w-full sm:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                        <input 
                            type="text" 
                            placeholder="Query UUID or Phone..."
                            className="w-full pl-9 p-2 bg-black/40 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all placeholder-slate-500"
                            value={search} onChange={e => setSearch(e.target.value)}
                        />
                    </div>
                    <select 
                        className="p-2 bg-black/40 border border-white/10 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-indigo-500 transition-all appearance-none pr-8 cursor-pointer"
                        value={filter} onChange={e => setFilter(e.target.value)}
                    >
                        <option value="ALL">All Vectors</option>
                        <option value="PENDING">Pending</option>
                        <option value="ASSIGNED">Assigned</option>
                        <option value="IN_TRANSIT">In Transit</option>
                        <option value="COMPLETED">Completed</option>
                    </select>
                </div>
            </div>

            {/* Mobile Card View */}
            <div className="flex-1 overflow-auto sm:hidden p-3 space-y-3">
                {filtered.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 font-mono text-xs">No records found.</div>
                ) : filtered.map(b => (
                    <div key={b.id} className="bg-white/5 border border-white/10 rounded-xl p-3 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="font-mono text-xs font-bold text-indigo-400">UUID-{String(b.id).substring(0,8)}</span>
                            <span className={cn("px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest rounded-md", statusColors[b.status])}>{b.status}</span>
                        </div>
                        <div className="text-xs text-slate-300">{b.customer_phone}</div>
                        <div className="flex items-center gap-1 text-[10px] font-mono">
                            <span className="text-blue-400">[{b.pickup_lat?.toFixed(2)},{b.pickup_lng?.toFixed(2)}]</span>
                            <span className="text-slate-600">→</span>
                            <span className="text-emerald-400">[{b.drop_lat?.toFixed(2)},{b.drop_lng?.toFixed(2)}]</span>
                        </div>
                        <div className="text-xs text-slate-400">{b.declared_weight}kg</div>
                    </div>
                ))}
            </div>

            {/* Desktop Table View */}
            <div className="flex-1 overflow-auto hidden sm:block">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                    <thead className="sticky top-0 bg-[#0c0c0e]/95 backdrop-blur-md z-10 border-b border-white/5">
                        <tr className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            <th className="p-4 pl-6">Identifier</th>
                            <th className="p-4">Signals (Cust/Pass)</th>
                            <th className="p-4">Coordinates (Origin → Dest)</th>
                            <th className="p-4">Mass</th>
                            <th className="p-4 pr-6">Status Code</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-sm">
                        {filtered.length === 0 ? (
                            <tr><td colSpan="5" className="p-12 text-center text-slate-500 font-mono">No matching records found.</td></tr>
                        ) : filtered.map(b => (
                            <tr key={b.id} className="hover:bg-white/5 transition-colors group cursor-default">
                                <td className="p-4 pl-6 text-slate-300 font-mono text-xs font-bold group-hover:text-indigo-400 transition-colors">
                                    UUID-{String(b.id).substring(0,8)}
                                </td>
                                <td className="p-4">
                                    <div className="font-medium text-slate-200">{b.customer_phone}</div>
                                    <div className="text-xs text-slate-500">{b.passenger_phone ? `Pass: ${b.passenger_phone}` : 'Direct Link'}</div>
                                </td>
                                <td className="p-4 text-slate-400 text-xs font-mono">
                                    <span className="text-blue-400">[{b.pickup_lat?.toFixed(2)}, {b.pickup_lng?.toFixed(2)}]</span>
                                    <span className="mx-2 text-slate-600">→</span>
                                    <span className="text-emerald-400">[{b.drop_lat?.toFixed(2)}, {b.drop_lng?.toFixed(2)}]</span>
                                </td>
                                <td className="p-4 text-slate-300 font-medium">
                                    {b.declared_weight}kg <span className="text-slate-600 font-normal">/ {b.verified_weight || '-'}</span>
                                </td>
                                <td className="p-4 pr-6">
                                    <span className={cn("px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest rounded-md", statusColors[b.status])}>
                                        {b.status}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default BookingsTable;
