const firebaseConfig = {
    apiKey: "YOUR_KEY_HERE",
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

function processBins() {
    const threshold = parseInt(document.getElementById('threshold').value);
    const now = Math.floor(Date.now() / 1000);
    let binSize, numBins;

    if (currentHorizon === 'hour') { binSize = 300; numBins = 12; }
    else if (currentHorizon === 'day') { binSize = 3600; numBins = 24; }
    else { binSize = 86400; numBins = 7; }

    const startTime = now - (numBins * binSize);
    const bins = Array.from({length: numBins}, (_, i) => ({
        t: startTime + (i * binSize),
        speeding: 0, normal: 0, speeds: []
    }));

    let totalObs = 0, speeders = 0, maxSpeed = 0;

    rawData.forEach(obs => {
        const speed = obs.s || obs.speed; 
        const ts = obs.t || obs.timestamp;
        if (speed > maxSpeed) maxSpeed = speed;

        const idx = Math.floor((ts - startTime) / binSize);
        if (idx >= 0 && idx < numBins) {
            totalObs++;
            if (speed > threshold) { bins[idx].speeding++; speeders++; } 
            else { bins[idx].normal++; }
            bins[idx].speeds.push(speed);
        }
    });

    document.getElementById('stat-total').innerText = totalObs.toLocaleString();
    document.getElementById('stat-pct').innerText = totalObs > 0 ? ((speeders/totalObs)*100).toFixed(1) + '%' : '0%';
    document.getElementById('stat-max').innerText = maxSpeed.toFixed(1);
    return bins;
}

function renderChart() {
    const bins = processBins();
    const ctx = document.getElementById('trafficChart').getContext('2d');
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bins.map(b => new Date(b.t*1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})),
            datasets: [
                { label: 'Speeding', data: bins.map(b => b.speeding), backgroundColor: '#ef4444', stack: 'a' },
                { label: 'Normal', data: bins.map(b => b.normal), backgroundColor: '#1e293b', stack: 'a' }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, grid: { color: '#0f172a' } }
            }
        }
    });
}

function fetchData() {
    db.ref('observations').limitToLast(1000).once('value', (snap) => {
        const val = snap.val();
        rawData = val ? Object.values(val) : [];
        renderChart();
    });
}

function updateFilter(f) {
    currentFilter = f;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(f === 'non-speeding' ? 'btn-non' : 'btn-' + f).classList.add('active');
    renderChart();
}

function updateHorizon(h) {
    currentHorizon = h;
    document.querySelectorAll('.hz-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('hz-' + h).classList.add('active');
    renderChart();
}

fetchData();