// --- 1. FIREBASE CONFIG ---
const firebaseConfig = {
    apiKey: "YOUR_KEY_HERE", // Replace with your actual key when ready
    authDomain: "pi-speedcamera.firebaseapp.com",
    databaseURL: "https://pi-speedcamera-default-rtdb.europe-west1.firebasedatabase.app/",
    projectId: "pi-speedcamera",
    storageBucket: "pi-speedcamera.appspot.com",
    messagingSenderId: "...",
    appId: "..."
};

firebase.initializeApp(firebaseConfig);
const db = firebase.database();

let rawData = [];
let currentFilter = 'all';
let currentHorizon = 'day';
let chart;

// --- 2. DATA FETCHING (HYBRID) ---
function fetchData() {
    const btn = document.querySelector('button[onclick="fetchData()"]');
    if(btn) btn.innerHTML = "⌛ Syncing...";

    // If looking at Week/Month, pull from summaries. Otherwise, pull raw observations.
    const useSummaries = (currentHorizon === 'week' || currentHorizon === 'month');
    let path = useSummaries ? 'hourly_summaries' : 'observations';
    
    // We pull 2000 records to ensure we cover the full time window
    db.ref(path).limitToLast(2000).once('value', (snap) => {
        const val = snap.val();
        rawData = val ? Object.values(val) : [];
        
        if (useSummaries) {
            rawData.sort((a, b) => (a.t || a.timestamp) - (b.t || b.timestamp));
        }
        
        renderChart();
        if(btn) btn.innerHTML = "<span>🔄</span> Refresh";
    });
}

// --- 3. BINNING LOGIC (DEFENSIVE) ---
function processBins() {
    const threshold = parseInt(document.getElementById('threshold').value);
    const now = Math.floor(Date.now() / 1000);
    
    // Handle Summary Data (Week/Month)
    if (currentHorizon === 'week' || currentHorizon === 'month') {
        return rawData.map(s => ({
            label: new Date((s.t || s.timestamp) * 1000).toLocaleDateString([], {day:'numeric', month:'short'}),
            speeding: s.speeding,
            normal: (s.total || 0) - (s.speeding || 0),
            total: s.total,
            max: s.max
        }));
    }

    // Handle Raw Data (Hour/Day)
    let binSize = currentHorizon === 'hour' ? 300 : 3600;
    let numBins = currentHorizon === 'hour' ? 12 : 24;
    const startTime = now - (numBins * binSize);
    
    const bins = Array.from({length: numBins}, (_, i) => ({
        t: startTime + (i * binSize),
        speeding: 0, normal: 0, max: 0, total: 0
    }));

    rawData.forEach(obs => {
        // DEFENSIVE KEY CHECK: Handles 's', 'speed', 'mph', etc.
        let speed = obs.s || obs.speed || obs.mph || obs.final_speed || 0;
        let ts = obs.t || obs.timestamp || obs.time || 0;

        // DEFENSIVE TIMESTAMP CHECK: If it's in milliseconds, convert to seconds
        if (ts > 1000000000000) ts = Math.floor(ts / 1000);

        const adjSpeed = speed * 0.9;
        const idx = Math.floor((ts - startTime) / binSize);
        
        if (idx >= 0 && idx < numBins) {
            bins[idx].total++;
            if (adjSpeed > threshold) bins[idx].speeding++;
            else bins[idx].normal++;
            if (adjSpeed > bins[idx].max) bins[idx].max = adjSpeed;
        }
    });

    return bins.map(b => ({
        label: currentHorizon === 'hour' ? 
               new Date(b.t*1000).toLocaleTimeString([], {minute:'2-digit'}) + 'm' : 
               new Date(b.t*1000).getHours() + ':00',
        ...b
    }));
}

// --- 4. RENDERING ---
function renderChart() {
    const bins = processBins();
    const ctx = document.getElementById('trafficChart').getContext('2d');
    
    // Update Ticker Stats
    const totalObs = bins.reduce((a, b) => a + (b.total || 0), 0);
    const totalSpeeding = bins.reduce((a, b) => a + (b.speeding || 0), 0);
    const maxSpeed = Math.max(...bins.map(b => b.max || 0), 0);

    document.getElementById('stat-total').innerText = totalObs.toLocaleString();
    document.getElementById('stat-pct').innerText = totalObs > 0 ? ((totalSpeeding/totalObs)*100).toFixed(1) + '%' : '0%';
    document.getElementById('stat-max').innerText = maxSpeed.toFixed(1);

    if (chart) chart.destroy();
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bins.map(b => b.label),
            datasets: [
                { label: 'Speeding', data: bins.map(b => b.speeding), backgroundColor: '#ef4444', hidden: currentFilter === 'non-speeding', stack: 'a', borderRadius: 4 },
                { label: 'Normal', data: bins.map(b => b.normal), backgroundColor: '#1e293b', hidden: currentFilter === 'speeding', stack: 'a', borderRadius: 4 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { color: '#475569', font: { size: 9, weight: 'bold' } } },
                y: { stacked: true, grid: { color: '#0f172a' }, ticks: { color: '#475569' } }
            }
        }
    });
}

function updateFilter(f) {
    currentFilter = f;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    const btnId = f === 'non-speeding' ? 'btn-non' : 'btn-' + f;
    if(document.getElementById(btnId)) document.getElementById(btnId).classList.add('active');
    renderChart();
}

function updateHorizon(h) {
    currentHorizon = h;
    document.querySelectorAll('.hz-btn').forEach(b => b.classList.remove('active'));
    if(document.getElementById('hz-' + h)) document.getElementById('hz-' + h).classList.add('active');
    fetchData(); // Always re-fetch when changing horizon to trigger Hybrid logic
}

fetchData();