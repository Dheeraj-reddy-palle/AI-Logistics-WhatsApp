import React, { useState } from 'react';
import { fetchState } from '../services/api';
import { Search, Database, Code } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const StateViewer = () => {
    const [phone, setPhone] = useState('');
    const [stateData, setStateData] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!phone.trim()) return;
        setLoading(true);
        try { setStateData(await fetchState(phone.trim())); } catch (err) {}
        setLoading(false);
    };

    return (
        <div className="glass-panel rounded-2xl p-5 h-full flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-4">
                <div className="flex items-center gap-2">
                    <Database className="w-5 h-5 text-indigo-400" />
                    <h2 className="text-lg font-bold text-white tracking-wide">Redis Inspector</h2>
                </div>
            </div>

            <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <input type="text" placeholder="Target Phone Hash..." className="w-full pl-9 p-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-white focus:border-indigo-500 outline-none transition" value={phone} onChange={e=>setPhone(e.target.value)} />
                </div>
                <button disabled={loading || !phone} className="px-5 bg-white text-black hover:bg-slate-200 rounded-xl font-bold text-sm transition-colors disabled:opacity-50">QUERY</button>
            </form>

            <div className="flex-1 bg-[#0a0a0c] border border-white/5 rounded-xl overflow-hidden flex flex-col relative">
                <div className="bg-white/5 px-3 py-2 border-b border-white/5 flex gap-2 items-center">
                    <Code className="w-4 h-4 text-slate-400" />
                    <span className="text-xs font-mono text-slate-400">STATE_DICT_LENS</span>
                    {stateData?.current_flow && (
                        <span className="ml-auto text-[10px] font-bold tracking-widest uppercase bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded">
                            {stateData.current_flow}
                        </span>
                    )}
                </div>
                <div className="flex-1 p-4 overflow-auto font-mono text-xs text-slate-300">
                    <AnimatePresence mode="wait">
                        {stateData ? (
                            <motion.pre initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="text-emerald-400">
                                {JSON.stringify(stateData, null, 2)}
                            </motion.pre>
                        ) : (
                            <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="text-slate-600 flex items-center justify-center h-full">
                                ENTER TARGET TO MOUNT BUFFER
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
};

export default StateViewer;
