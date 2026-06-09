let currentTf = '1m';
let priceChart;
const priceData = { labels: [], data: [] };

// Chart setup
function initChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: priceData.labels,
            datasets: [{
                label: 'BTC Price',
                data: priceData.data,
                borderColor: '#f7931a',
                backgroundColor: 'rgba(247,147,26,0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } }
            }
        }
    });
}

function updateUI(data) {
    const signal = data[currentTf];
    if (!signal) return;

    document.getElementById('price').textContent = `$${signal.price.toLocaleString(undefined, {minimumFractionDigits: 2})}`;

    const badge = document.getElementById('signal-badge');
    badge.textContent = signal.signal.replace('_', ' ');
    badge.className = `signal-badge ${signal.signal}`;

    document.getElementById('confidence').textContent = `${signal.confidence}%`;
    document.getElementById('tech-score').textContent = signal.technical_score.toFixed(4);
    document.getElementById('onchain-score').textContent = signal.onchain_score.toFixed(4);
    document.getElementById('sentiment-score').textContent = signal.sentiment_score.toFixed(4);

    // Indicators
    const grid = document.getElementById('indicators-grid');
    grid.innerHTML = signal.indicators.map(i => `
        <div class="indicator-item">
            <div class="name">${i.name}</div>
            <div class="value">${i.value !== null ? i.value : '--'}</div>
            <span class="signal-tag ${i.signal}">${i.signal.replace('_', ' ')}</span>
        </div>
    `).join('');

    // On-chain
    document.getElementById('hashrate').textContent = signal.onchain.hashrate_trend;
    document.getElementById('fees').textContent = signal.onchain.estimated_fees ?? '--';
    document.getElementById('difficulty').textContent = signal.onchain.difficulty_adjustment ? `${signal.onchain.difficulty_adjustment.toFixed(2)}%` : '--';

    // Sentiment
    document.getElementById('fng-value').textContent = signal.sentiment.fear_greed_index ?? '--';
    document.getElementById('fng-label').textContent = signal.sentiment.fear_greed_label;
    document.getElementById('fng-signal').textContent = signal.sentiment.signal.replace('_', ' ');

    // Chart update
    const time = new Date(signal.timestamp).toLocaleTimeString();
    priceData.labels.push(time);
    priceData.data.push(signal.price);
    if (priceData.labels.length > 60) {
        priceData.labels.shift();
        priceData.data.shift();
    }
    priceChart.update('none');
}

// WebSocket
function connect() {
    const ws = new WebSocket(`ws://${location.host}/ws`);
    const status = document.getElementById('status');

    ws.onopen = () => { status.textContent = 'Live'; status.classList.remove('disconnected'); };
    ws.onclose = () => { status.textContent = 'Disconnected'; status.classList.add('disconnected'); setTimeout(connect, 3000); };
    ws.onmessage = (e) => updateUI(JSON.parse(e.data));
}

// Tabs
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelector('.tab.active').classList.remove('active');
        tab.classList.add('active');
        currentTf = tab.dataset.tf;
        priceData.labels = [];
        priceData.data = [];
    });
});

initChart();
connect();
