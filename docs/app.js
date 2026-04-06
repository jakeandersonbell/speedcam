const SUPABASE_URL = "https://dahskjveppeniyyuuuos.supabase.co";
const SUPABASE_KEY = "sb_publishable_-q_g4hdktoRHS_V9kPeRDA_5GIy19AR";
const supa = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

let chartData = [];
let currentHorizon = 'hour';
let chart;
let thresholdTimeout;

const SPEED_BINS = [
    { label: '<20', key: 'cat_20', min: 0 },
    { label: '20',  key: 'cat_25', min: 20 },
    { label: '25',  key: 'cat_30', min: 25 },
    { label: '30',  key: 'cat_35', min: 30 },
    { label: '35',  key: 'cat_40', min: 35 },
    { label: '40',  key: 'cat_45', min: 40 },
    { label: '45',  key: 'cat_50', min: 45 },
    { label: '50',  key: 'cat_55', min: 50 },
    { label: '55+', key: 'cat_60', min: 55 }
];

const HORIZON_CONFIG = {
    '5min':  { view: 'traffic_5min',   limit: 12 },
    'hour':  { view: 'traffic_hourly', limit: 24 },
    '6hour': { view: 'traffic_6hourly', limit: 28 },
    'day':   { view: 'traffic_daily',  limit: 31 }
};

const toBST = (rawStr, options) => {
    if (!rawStr) return "??:??";
    const isoStr = rawStr.replace(' ', 'T').split('+')[0].replace('Z', '') + 'Z';
    const d = new Date(isoStr);
    return isNaN(d.getTime()) ? "??:??" : new Intl.DateTimeFormat('en-GB', { ...options, timeZone: 'Europe/London' }).format(d);
};

function handleThresholdChange() {
    clearTimeout(thresholdTimeout);
    thresholdTimeout = setTimeout(() => { renderChart(); }, 800);
}

function getTooltipHtml(bin, threshold) {
    const maxVal = Math.max(...SPEED_BINS.map(s => bin[s.key])) || 1;
    const pct = bin.total_cars > 0 ? ((bin.dynamicSpeeding / bin.total_cars) * 100).toFixed(0) : 0;
    const formattedDate = toBST(bin.bucket, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });

    let histHtml = `<div class="hist-container border-b border-slate-700/50">`;
    SPEED_BINS.forEach(s => {
        const val = bin[s.key] || 0;
        const h = (val / maxVal) * 100;
        const isSpeeding = s.min >= threshold;
        histHtml += `<div class="hist-bar ${isSpeeding ? 'speeding' : ''}" style="height:${h}%"></div>`;
    });
    histHtml += `</div>`;

    let labelHtml = `<div class="label-grid text-[7px] font-black text-slate-600 uppercase">`;
    SPEED_BINS.forEach(s => labelHtml += `<span>${s.label}</span>`);
    labelHtml += `</div>`;

    return `
        <div class="text-[10px] font-black text-slate-500 mb-1 uppercase">${formattedDate}</div>
        <div class="text-3xl font-black text-white">${bin.total_cars} <span class="text-[10px] text-slate-500">CARS</span></div>
        <div class="flex items-center gap-2 mt-1">
            <div class="h-2 w-2 rounded-full ${pct > 25 ? 'bg-red-500 animate-pulse' : 'bg-green-500'}"></div>
            <span class="text-[11px] font-black uppercase ${pct > 25 ? 'text-red-500' : 'text-green-500'}">${pct}% Speeders</span>
        </div>
        ${histHtml}
        ${labelHtml}
    `;
}

function renderChart() {
    const canvas = document.getElementById('trafficChart');
    const ctx = canvas.getContext('2d');
    if (chart) chart.destroy();

    const threshold = parseInt(document.getElementById('threshold').value) || 30;

    const processedData = chartData.map(b => {
        let speeding = 0;
        SPEED_BINS.forEach(s => { if (s.min >= threshold) speeding += (b[s.key] || 0); });
        return { ...b, dynamicSpeeding: speeding, dynamicNormal: b.total_cars - speeding };
    });

    const totalObs = processedData.reduce((a, b) => a + b.total_cars, 0);
    const totalSpeeders = processedData.reduce((a, b) => a + b.dynamicSpeeding, 0);

    document.getElementById('stat-total').innerText = totalObs.toLocaleString();
    document.getElementById('stat-pct').innerText = totalObs > 0 ? ((totalSpeeders / totalObs) * 100).toFixed(1) + '%' : '0%';

    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: processedData.map(b => {
                if (currentHorizon === '5min') return toBST(b.bucket, { minute: '2-digit' }) + 'm';
                if (currentHorizon === 'day') return toBST(b.bucket, { day: 'numeric', month: 'short' });
                return toBST(b.bucket, { hour: '2-digit', hour12: false });
            }),
            datasets: [
                { label: 'Speeding', data: processedData.map(b => b.dynamicSpeeding), backgroundColor: '#ef4444', stack: 'a', borderRadius: 4 },
                { label: 'Normal', data: processedData.map(b => b.dynamicNormal), backgroundColor: '#1e293b', stack: 'a', borderRadius: 4 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: false,
                    external: function(context) {
                        const tooltipEl = document.getElementById('chart-tooltip');
                        if (context.tooltip.opacity === 0) { tooltipEl.style.opacity = 0; return; }
                        const idx = context.tooltip.dataPoints[0].dataIndex;
                        tooltipEl.innerHTML = getTooltipHtml(processedData[idx], threshold);
                        const position = context.chart.canvas.getBoundingClientRect();
                        tooltipEl.style.opacity = 1;
                        tooltipEl.style.left = (position.left + window.pageXOffset + context.tooltip.caretX) + 'px';
                        tooltipEl.style.top = (position.top + window.pageYOffset + context.tooltip.caretY - 20) + 'px';
                        tooltipEl.style.transform = 'translate(-50%, -100%)'; 
                    }
                }
            },
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { color: '#475569', font: { size: 9, weight: '900' } } },
                y: { stacked: true, grid: { color: '#0f172a' }, ticks: { color: '#475569', font: { weight: 'bold' } } }
            }
        }
    });
}

async function fetchData() {
    const container = document.getElementById('chart-container');
    container.classList.add('loading');
    const config = HORIZON_CONFIG[currentHorizon];

    try {
        const { data, error } = await supa.from(config.view).select('*').order('bucket', { ascending: false }).limit(config.limit);
        if (error) throw error;
        chartData = data.map(d => ({ ...d, _d: new Date(d.bucket.replace(' ', 'T').split('+')[0] + 'Z') })).sort((a, b) => a._d - b._d);
        renderChart();
    } catch (err) {
        console.error(err);
    } finally {
        container.classList.remove('loading');
    }
}

function updateHorizon(h) {
    currentHorizon = h;
    document.querySelectorAll('.filter-btn').forEach(b => {
        b.classList.remove('bg-blue-600', 'text-white');
        b.classList.add('bg-slate-900', 'text-slate-400');
    });
    document.getElementById('hz-' + h).classList.add('bg-blue-600', 'text-white');
    fetchData();
}

document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    setInterval(fetchData, 60000);
});