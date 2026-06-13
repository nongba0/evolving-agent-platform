'use client';

import { useState, useEffect, useRef } from 'react';
import { getSettings, updateSettings, createTask, Task, Settings } from '../lib/api';

export default function Dashboard() {
  const [settings, setSettings] = useState<Settings>({ system_active: true, learning_active: true });
  const [prompt, setPrompt] = useState('');
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [logs, setLogs] = useState<{ time: string; agent: string; text: string }[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // DAG States for visualization
  const [dagState, setDagState] = useState({
    orchestrator: 'pending', // pending, running, success, failed
    subagent1: 'pending',
    subagent2: 'pending',
    aggregator: 'pending',
    validator: 'pending',
  });

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Fetch initial settings on load
  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await getSettings();
        setSettings(data);
      } catch (err) {
        console.error('Failed to load settings:', err);
      }
    }
    loadSettings();
  }, []);

  // Scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Toggle active settings
  const handleToggleSystem = async () => {
    const nextVal = !settings.system_active;
    const nextSettings = { ...settings, system_active: nextVal };
    setSettings(nextSettings);
    try {
      await updateSettings(nextSettings);
    } catch (err) {
      setErrorMsg('Failed to update system toggle');
      setSettings(settings); // Rollback
    }
  };

  const handleToggleLearning = async () => {
    const nextVal = !settings.learning_active;
    const nextSettings = { ...settings, learning_active: nextVal };
    setSettings(nextSettings);
    try {
      await updateSettings(nextSettings);
    } catch (err) {
      setErrorMsg('Failed to update memory toggle');
      setSettings(settings); // Rollback
    }
  };

  // Submit new task
  const handleSubmitTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setErrorMsg(null);
    setLoading(true);
    setLogs([]);
    setDagState({
      orchestrator: 'pending',
      subagent1: 'pending',
      subagent2: 'pending',
      aggregator: 'pending',
      validator: 'pending',
    });

    try {
      const task = await createTask(prompt);
      setActiveTask(task);
      setPrompt('');
      
      // Simulate real-time logs and DAG progress (will connect to backend WS in Phase 4)
      simulateTaskExecution();
    } catch (err: any) {
      setErrorMsg(err.message || 'An error occurred while launching task');
    } finally {
      setLoading(false);
    }
  };

  const simulateTaskExecution = () => {
    const addLog = (agent: string, text: string, delay: number) => {
      setTimeout(() => {
        setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), agent, text }]);
      }, delay);
    };

    // Orchestrator start
    addLog('Orchestrator', 'Analyzing task request...', 500);
    setTimeout(() => setDagState(prev => ({ ...prev, orchestrator: 'running' })), 500);
    
    // Decomposition
    addLog('Orchestrator', 'Task decomposed into 2 sub-tasks: [Data Scraper, Data Parser]', 1500);
    setTimeout(() => setDagState(prev => ({ ...prev, orchestrator: 'success', subagent1: 'running', subagent2: 'running' })), 2000);

    // Subagent 1 & 2 Execution
    addLog('Scraper-Agent', 'Scraping Kakao Maps data chunks...', 2500);
    addLog('Parser-Agent', 'Initializing fast regex tokenizer...', 3000);
    
    // Subagent L1 validation
    addLog('Scraper-Agent', 'L1 validation check passed (Schema verified)', 4500);
    setTimeout(() => setDagState(prev => ({ ...prev, subagent1: 'success' })), 4800);

    addLog('Parser-Agent', 'L1 validation check passed (Type safety verified)', 5000);
    setTimeout(() => setDagState(prev => ({ ...prev, subagent2: 'success', aggregator: 'running' })), 5200);

    // Aggregation
    addLog('Aggregator-Agent', 'Merging data structures and executing joins...', 6000);
    setTimeout(() => setDagState(prev => ({ ...prev, aggregator: 'success', validator: 'running' })), 7000);

    // L2 Validation Gate
    addLog('Validator-Agent', 'Running L2 Milestone Gate validation (Semantic review)...', 7500);
    
    setTimeout(() => {
      setDagState(prev => ({ ...prev, validator: 'success' }));
      setLogs(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        agent: 'System',
        text: '✅ Task Completed Successfully! Output saved.'
      }]);
    }, 9000);
  };

  const getStatusColor = (status: string) => {
    if (status === 'success') return 'bg-emerald-500 text-emerald-950 border-emerald-400';
    if (status === 'running') return 'bg-amber-500 text-amber-950 animate-pulse border-amber-400';
    if (status === 'failed') return 'bg-rose-500 text-rose-950 border-rose-400';
    return 'bg-slate-800 text-slate-400 border-slate-700';
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center p-6 bg-slate-900/50 border border-slate-800/80 rounded-2xl backdrop-blur-xl shadow-xl space-y-4 md:space-y-0">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500">
              EvoAgent Console
            </h1>
            <p className="text-sm text-slate-400">Self-Evolving Multi-Agent Task Orchestrator</p>
          </div>
          
          {/* Toggles */}
          <div className="flex space-x-6 items-center bg-slate-950/80 px-4 py-2 rounded-xl border border-slate-800">
            {/* System active toggle */}
            <div className="flex items-center space-x-3">
              <span className="text-xs font-semibold text-slate-400">System</span>
              <button 
                onClick={handleToggleSystem}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${settings.system_active ? 'bg-amber-500' : 'bg-slate-700'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-slate-900 transition-transform ${settings.system_active ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
              <span className={`text-xs font-bold ${settings.system_active ? 'text-amber-400' : 'text-slate-500'}`}>
                {settings.system_active ? 'ON' : 'OFF'}
              </span>
            </div>

            <div className="h-4 w-px bg-slate-800" />

            {/* Learning active toggle */}
            <div className="flex items-center space-x-3">
              <span className="text-xs font-semibold text-slate-400">Evolution/Memory</span>
              <button 
                onClick={handleToggleLearning}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${settings.learning_active ? 'bg-amber-500' : 'bg-slate-700'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-slate-900 transition-transform ${settings.learning_active ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
              <span className={`text-xs font-bold ${settings.learning_active ? 'text-amber-400' : 'text-slate-500'}`}>
                {settings.learning_active ? 'ON' : 'OFF'}
              </span>
            </div>
          </div>
        </header>

        {errorMsg && (
          <div className="p-4 bg-rose-950/30 border border-rose-900/60 rounded-xl text-rose-300 text-sm">
            ⚠️ {errorMsg}
          </div>
        )}

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Panel: Task Submission & Budget */}
          <div className="lg:col-span-1 space-y-6">
            <section className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl space-y-4 shadow-md">
              <h2 className="text-lg font-bold text-slate-200">Start New Task</h2>
              <form onSubmit={handleSubmitTask} className="space-y-4">
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe your data extraction or code parsing task..."
                  rows={4}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50 resize-none text-sm transition-all"
                  disabled={!settings.system_active}
                />
                <button
                  type="submit"
                  disabled={loading || !settings.system_active || !prompt.trim()}
                  className="w-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 disabled:from-slate-800 disabled:to-slate-800 text-slate-950 font-semibold py-2.5 px-4 rounded-xl text-sm transition-all shadow-lg shadow-amber-500/10 active:scale-98"
                >
                  {loading ? 'Submitting...' : 'Launch Agents'}
                </button>
              </form>
            </section>

            <section className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl space-y-4 shadow-md">
              <h2 className="text-lg font-bold text-slate-200">Token Cost & Budget</h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Task Budget Cap:</span>
                  <span className="font-semibold text-amber-400">$0.50</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Accumulated Cost:</span>
                  <span className="font-semibold text-slate-200">$0.00 / $0.50</span>
                </div>
                {/* Progress bar */}
                <div className="w-full bg-slate-950 rounded-full h-2 border border-slate-800 overflow-hidden">
                  <div className="bg-amber-500 h-full w-[0%]" />
                </div>
              </div>
            </section>
          </div>

          {/* Right Panel: Workspace Logs & DAG Map */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Visualizer & Logs Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* DAG Visualization */}
              <section className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl space-y-4 flex flex-col justify-between min-h-[300px]">
                <h2 className="text-lg font-bold text-slate-200">Task Execution Map (DAG)</h2>
                
                {/* Visual Nodes */}
                <div className="flex flex-col items-center space-y-4 py-2">
                  <div className={`px-4 py-2 rounded-lg border text-xs font-semibold ${getStatusColor(dagState.orchestrator)}`}>
                    Orchestrator
                  </div>
                  
                  <div className="h-4 w-px bg-slate-800" />
                  
                  <div className="flex justify-around w-full">
                    <div className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${getStatusColor(dagState.subagent1)}`}>
                      Data Extractor
                    </div>
                    <div className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${getStatusColor(dagState.subagent2)}`}>
                      Data Parser
                    </div>
                  </div>
                  
                  <div className="h-4 w-px bg-slate-800" />
                  
                  <div className={`px-4 py-2 rounded-lg border text-xs font-semibold ${getStatusColor(dagState.aggregator)}`}>
                    Aggregator
                  </div>
                  
                  <div className="h-4 w-px bg-slate-800" />
                  
                  <div className={`px-4 py-2 rounded-lg border text-xs font-semibold ${getStatusColor(dagState.validator)}`}>
                    Milestone Gate
                  </div>
                </div>
              </section>

              {/* Log Console Terminal */}
              <section className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl flex flex-col h-[300px] shadow-md">
                <h2 className="text-lg font-bold text-slate-200 mb-3">Live Log Console</h2>
                <div className="flex-1 bg-slate-950 border border-slate-850 rounded-xl p-3 font-mono text-xs overflow-y-auto space-y-2 text-slate-300">
                  {logs.length === 0 ? (
                    <div className="text-slate-600 text-center py-12">Console idle. Awaiting agent execution...</div>
                  ) : (
                    logs.map((log, i) => (
                      <div key={i} className="leading-relaxed">
                        <span className="text-slate-600">[{log.time}]</span>{' '}
                        <span className="text-amber-500/80 font-bold">{log.agent}:</span>{' '}
                        <span>{log.text}</span>
                      </div>
                    ))
                  )}
                  <div ref={logsEndRef} />
                </div>
              </section>
            </div>

            {/* Evolution Diff Viewer Panel */}
            <section className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl space-y-4 shadow-md">
              <h2 className="text-lg font-bold text-slate-200">Evolution Diff Viewer</h2>
              <div className="bg-slate-950 border border-slate-850 rounded-xl overflow-hidden text-xs font-mono">
                <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex justify-between text-slate-400">
                  <span>File: user_profile.md (Format: Coffee Shop JSON)</span>
                  <span className="text-amber-400 font-bold">Recommended Evolution</span>
                </div>
                <div className="p-4 space-y-1 text-slate-400 overflow-x-auto">
                  <div>  &quot;name&quot;: &quot;Blue Bottle Coffee&quot;,</div>
                  <div className="bg-rose-950/20 text-rose-400 px-1 border-l-2 border-rose-500">- &quot;address&quot;: &quot;Seoul, Seongdong-gu, Achasan-ro 7&quot;,</div>
                  <div className="bg-emerald-950/20 text-emerald-400 px-1 border-l-2 border-emerald-500">+ &quot;address&quot;: &quot;Achasan-ro 7, Seongdong-gu, Seoul&quot;,</div>
                  <div className="bg-emerald-950/20 text-emerald-400 px-1 border-l-2 border-emerald-500">+ &quot;coordinates&quot;: &#123; &quot;latitude&quot;: 37.5451, &quot;longitude&quot;: 127.0435 &#125;,</div>
                  <div>  &quot;tags&quot;: [&quot;#specialty&quot;, &quot;#drip&quot;]</div>
                </div>
              </div>
            </section>

          </div>
        </div>
      </div>
    </main>
  );
}
