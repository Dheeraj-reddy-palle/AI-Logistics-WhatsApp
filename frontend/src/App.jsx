import React from 'react';
import { motion } from 'framer-motion';
import { Activity } from 'lucide-react';

import DashboardOverview from './components/DashboardOverview';
import BookingsTable from './components/BookingsTable';
import DriverMap from './components/DriverMap';
import DriverActions from './components/DriverActions';
import StateViewer from './components/StateViewer';

function App() {
  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 bg-[#050505] text-slate-200 selection:bg-blue-500/30">
      
      {/* Header */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 sm:mb-8 pb-4 border-b border-white/5 gap-3"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-900/20 flex-shrink-0">
            <Activity className="text-white w-5 h-5 sm:w-6 sm:h-6" />
          </div>
          <div>
            <h1 className="text-lg sm:text-2xl font-bold tracking-tight text-white">Logistics Command Center</h1>
            <p className="text-xs sm:text-sm text-slate-400 font-medium tracking-wide">AI Node Aggregation Network</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3 text-[10px] sm:text-xs font-mono font-medium text-slate-500 bg-white/5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg border border-white/5">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            ONLINE
          </span>
          <span className="text-slate-600">|</span>
          <span>v2.0.0</span>
        </div>
      </motion.header>

      {/* Bento Grid Layout */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 max-w-[1800px] mx-auto auto-rows-min">
        
        {/* Top Row: Overview Metrics & Map */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}>
            <DashboardOverview />
          </motion.div>
        </div>
        
        <div className="lg:col-span-8 flex flex-col min-h-[300px] sm:min-h-[450px]">
          <motion.div className="h-full flex-1" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}>
            <DriverMap />
          </motion.div>
        </div>

        {/* Middle Row: Active Bookings Table */}
        <div className="lg:col-span-12">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }}>
            <BookingsTable />
          </motion.div>
        </div>

        {/* Bottom Row: Actions & Debugger */}
        <div className="lg:col-span-7">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.4 }}>
            <DriverActions />
          </motion.div>
        </div>

        <div className="lg:col-span-5">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.5 }}>
            <StateViewer />
          </motion.div>
        </div>

      </main>

    </div>
  );
}

export default App;
