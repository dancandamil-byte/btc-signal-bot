let currentTf = '1m';
let priceChart;
const priceData = { labels: [], data: [] };

function initChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: priceData.labels,
            datasets: [{
                label: 'Precio BTC',
                data: priceData.data,
                borderColor: '#f7931a',
                backgroundColor: 'rgba(247,147,26,0.1)',
                borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0
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

    document.getElementById('price').textContent = `$${signal.price.toLocaleString('es-CO', {minimumFractionDigits: 0})}`;

    // Mensaje de señal completo
    document.getElementById('signal-message').textContent = signal.mensaje;
    const msgCard = document.querySelector('.signal-message-card');
    msgCard.className = `card glass signal-message-card ${signal.signal.includes('BUY') ? 'buy' : signal.signal.includes('SELL') ? 'sell' : 'neutral'}`;

    // Indicadores
    const grid = document.getElementById('indicators-grid');
    grid.innerHTML = signal.indicators.map(i => `
        <div class="indicator-item">
            <div class="name">${i.name}</div>
            <div class="value">${i.value !== null ? i.value : '--'}</div>
            <span class="signal-tag ${i.signal}">${i.signal.includes('BUY') ? 'COMPRA' : i.signal.includes('SELL') ? 'VENTA' : 'NEUTRAL'}</span>
        </div>
    `).join('');

    // On-chain
    document.getElementById('hashrate').textContent = signal.onchain.hashrate_trend;
    document.getElementById('fees').textContent = signal.onchain.estimated_fees ?? '--';
    document.getElementById('difficulty').textContent = signal.onchain.difficulty_adjustment ? `${signal.onchain.difficulty_adjustment.toFixed(2)}%` : '--';

    // Sentimiento
    document.getElementById('fng-value').textContent = signal.sentiment.fear_greed_index ?? '--';
    document.getElementById('fng-label').textContent = signal.sentiment.fear_greed_label;
    const fngSignal = signal.sentiment.signal;
    document.getElementById('fng-signal').textContent = fngSignal.includes('BUY') ? 'COMPRA' : fngSignal.includes('SELL') ? 'VENTA' : 'NEUTRAL';

    // Gráfico
    const time = new Date(signal.timestamp).toLocaleTimeString('es-CO');
    priceData.labels.push(time);
    priceData.data.push(signal.price);
    if (priceData.labels.length > 60) { priceData.labels.shift(); priceData.data.shift(); }
    priceChart.update('none');
}

async function loadResults() {
    try {
        const resp = await fetch(`/api/results/${currentTf}`);
        const results = await resp.json();
        const tbody = document.getElementById('results-body');
        tbody.innerHTML = results.slice(-20).reverse().map(r => {
            const cls = r.resultado.includes('TP') ? 'win' : r.resultado.includes('SL') ? 'loss' : '';
            return `<tr class="${cls}">
                <td>${new Date(r.timestamp).toLocaleTimeString('es-CO')}</td>
                <td>${r.signal.includes('BUY') ? '🟢 COMPRA' : '🔴 VENTA'}</td>
                <td>$${r.price.toLocaleString('es-CO')}</td>
                <td>$${r.tp1.toLocaleString('es-CO')}</td>
                <td>$${r.sl.toLocaleString('es-CO')}</td>
                <td>${r.resultado}</td>
            </tr>`;
        }).join('');
    } catch (e) {}
}

// WebSocket
function connect() {
    const ws = new WebSocket(`ws://${location.host}/ws`);
    const status = document.getElementById('status');
    ws.onopen = () => { status.textContent = '🟢 En vivo'; status.classList.remove('disconnected'); };
    ws.onclose = () => { status.textContent = '🔴 Desconectado'; status.classList.add('disconnected'); setTimeout(connect, 3000); };
    ws.onmessage = (e) => { updateUI(JSON.parse(e.data)); loadResults(); };
}

// Tabs
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelector('.tab.active').classList.remove('active');
        tab.classList.add('active');
        currentTf = tab.dataset.tf;
        priceData.labels = []; priceData.data = [];
        loadResults();
    });
});

initChart();
connect();
loadResults();
