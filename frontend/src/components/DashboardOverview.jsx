import React, { useState, useEffect } from 'react';
import { fetchBookings, fetchDrivers } from '../services/api';
import { motion } from 'framer-motion';
import { Package, Truck, CheckCircle, Clock, Activity } from 'lucide-react';
import { cn } from '../utils';

const StatCard = ({ title, value, icon: Icon, colorClass }) => (
    <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between h-[130px] relative overflow-hidden group">
        <div className="absolute -right-6 -top-6 w-24 h-24 rounded-full blur-2xl opacity-20 transition-opacity group-hover:opacity-40" style={{ backgroundColor: colorClass }}></div>
        <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-slate-400 tracking-wide">{title}</p>
            <div className={cn("p-2 rounded-xl bg-white/5 border border-white/5", `text-[${colorClass}]`)}>
                <Icon className="h-5 w-5" style={{ color: colorClass }} />
            </div>
        </div>
        <div className="flex items-end justify-between">
            <h3 className="text-4xl font-bold tracking-tight text-white">{value}</h3>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                LIVE
            </span>
        </div>
    </div>
);

const DashboardOverview = () => {
    const [stats, setStats] = useState({ total: 0, active: 0, completed: 0, drivers: 0, recent: [] });

    useEffect(() => {
        const load = async () => {
            try {
                const bRes = await fetchBookings();
                const dRes = await fetchDrivers();
                setStats({
                    total: bRes.length,
                    active: bRes.filter(b => ['PENDING', 'ASSIGNED', 'IN_TRANSIT'].includes(b.status)).length,
                    completed: bRes.filter(b => b.status === 'COMPLETED').length,
                    drivers: dRes.filter(d => d.is_available).length,
                    recent: bRes.slice(0, 4)
                });
            } catch (e) {}
        };
        load();
        const interval = setInterval(load, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="h-full flex flex-col gap-6">
            <div className="grid grid-cols-2 gap-4">
                <StatCard title="Total Cargo" value={stats.total} icon={Package} colorClass="#60a5fa" />
                <StatCard title="Active Enroute" value={stats.active} icon={Clock} colorClass="#f59e0b" />
                <StatCard title="Completed" value={stats.completed} icon={CheckCircle} colorClass="#10b981" />
                <StatCard title="Fleet Nodes" value={stats.drivers} icon={Truck} colorClass="#c084fc" />
            </div>
            
            {/* Recent Activity Feed */}
            <div className="glass-panel p-5 rounded-2xl flex-1 flex flex-col min-h-[180px]">
                <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2 uppercase tracking-widest"><Activity className="w-4 h-4 text-blue-400"/> Event Horizon</h3>
                <div className="space-y-3 flex-1 overflow-auto pr-2">
                    {stats.recent.length === 0 ? <div className="text-xs text-slate-500 font-mono">No telemetry objects detected.</div> : null}
                    {stats.recent.map(b => (
                        <div key={b.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition">
                            <div className="flex items-center gap-3">
                                <div className={cn("w-2 h-2 rounded-full", b.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-blue-500 animate-pulse')}></div>
                                <div className="flex flex-col">
                                    <span className="text-xs font-mono font-bold text-slate-200">UUID-{b.id.substring(0,6).toUpperCase()}</span>
                                    <span className="text-[10px] text-slate-500 uppercase tracking-wide">{b.declared_weight}kg Payload</span>
                                </div>
                            </div>
                            <span className="text-xs font-semibold px-2 py-1 bg-black/40 rounded border border-white/5">{b.status}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default DashboardOverview;
