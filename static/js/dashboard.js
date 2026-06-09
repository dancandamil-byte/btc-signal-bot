let currentTf = '1m';
let priceChart;
const priceData = { labels: [], data: [] };
let soundEnabled = false;
let lastSignal = '';

// Audio notification
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
function playAlert(type) {
    if (!soundEnabled) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.frequency.value = type === 'buy' ? 800 : type === 'sell' ? 400 : 600;
    gain.gain.value = 0.3;
    osc.start(); osc.stop(audioCtx.currentTime + 0.3);
}

// Browser push notification
function sendNotification(title, body) {
    if (Notification.permission === 'granted') {
        new Notification(title, { body, icon: '₿' });
    }
}

// Sound toggle
document.getElementById('sound-btn').addEventListener('click', () => {
    soundEnabled = !soundEnabled;
    document.getElementById('sound-btn').textContent = soundEnabled ? '🔊' : '🔇';
    if (soundEnabled && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});

function initChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    priceChart = new Chart(ctx, {
        type: 'line',
        data: { labels: priceData.labels, datasets: [{
            label: 'BTC', data: priceData.data,
            borderColor: '#f7931a', backgroundColor: 'rgba(247,147,26,0.1)',
            borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0
        }]},
        options: { responsive: true, plugins: { legend: { display: false } },
            scales: { x: { display: false }, y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } } }
        }
    });
}

const sessionNames = { asia: '🌏 Asia', europa: '🌍 Europa', ny: '🌎 NY', fuera_horario: '⚠️ Fuera horario' };
const signalLabels = s => s.includes('BUY') ? 'COMPRA' : s.includes('SELL') ? 'VENTA' : 'NEUTRAL';

function updateUI(data) {
    const signal = data[currentTf];
    if (!signal) return;

    document.getElementById('price').textContent = `$${signal.price.toLocaleString('es-CO')}`;
    document.getElementById('signal-message').textContent = signal.mensaje;
    document.getElementById('session').textContent = sessionNames[signal.session] || signal.session;

    const card = document.getElementById('signal-card');
    card.className = `card glass signal-message-card ${signal.signal.includes('BUY') ? 'buy' : signal.signal.includes('SELL') ? 'sell' : 'neutral'}`;

    // Notificación en señal nueva
    if (signal.signal !== 'NEUTRAL' && signal.signal !== lastSignal && !signal.filtered_reason) {
        playAlert(signal.signal.includes('BUY') ? 'buy' : 'sell');
        sendNotification(`BTC ${signalLabels(signal.signal)}`, `$${signal.price.toLocaleString()} | Conf: ${signal.confidence}%`);
        card.classList.add('pulse');
        setTimeout(() => card.classList.remove('pulse'), 2000);
    }
    lastSignal = signal.signal;

    // Indicadores
    document.getElementById('indicators-grid').innerHTML = signal.indicators.map(i => `
        <div class="indicator-item">
            <div class="name">${i.name}</div>
            <div class="value">${i.value !== null ? i.value : '--'}</div>
            <span class="signal-tag ${i.signal}">${signalLabels(i.signal)}</span>
        </div>`).join('');

    // On-chain
    document.getElementById('hashrate').textContent = signal.onchain.hashrate_trend;
    document.getElementById('fees').textContent = signal.onchain.estimated_fees ?? '--';
    document.getElementById('difficulty').textContent = signal.onchain.difficulty_adjustment ? `${signal.onchain.difficulty_adjustment.toFixed(2)}%` : '--';
    document.getElementById('funding').textContent = signal.onchain.funding_rate != null ? `${signal.onchain.funding_rate}%` : '--';
    document.getElementById('liquidations').textContent = signal.onchain.liquidations_24h ? `$${(signal.onchain.liquidations_24h/1e6).toFixed(1)}M` : '--';
    document.getElementById('dominance').textContent = signal.onchain.btc_dominance ? `${signal.onchain.btc_dominance.toFixed(1)}%` : '--';

    // Sentimiento
    document.getElementById('fng-value').textContent = signal.sentiment.fear_greed_index ?? '--';
    document.getElementById('fng-label').textContent = signal.sentiment.fear_greed_label;
    document.getElementById('fng-signal').textContent = signalLabels(signal.sentiment.signal);

    // Chart
    const time = new Date(signal.timestamp).toLocaleTimeString('es-CO');
    priceData.labels.push(time); priceData.data.push(signal.price);
    if (priceData.labels.length > 60) { priceData.labels.shift(); priceData.data.shift(); }
    priceChart.update('none');
}

async function loadResults() {
    try {
        const resp = await fetch(`/api/results/${currentTf}`);
        const results = await resp.json();
        document.getElementById('results-body').innerHTML = results.slice(0, 20).map(r => {
            const cls = r.resultado.includes('TP') || r.resultado === 'TRAILING_STOP' ? 'win' : r.resultado.includes('SL') ? 'loss' : '';
            return `<tr class="${cls}">
                <td>${new Date(r.timestamp).toLocaleTimeString('es-CO')}</td>
                <td>${r.signal.includes('BUY') ? '🟢' : '🔴'} ${signalLabels(r.signal)}</td>
                <td>$${r.price?.toLocaleString('es-CO') || '--'}</td>
                <td>$${r.tp1?.toLocaleString('es-CO') || '--'}</td>
                <td>$${r.sl?.toLocaleString('es-CO') || '--'}</td>
                <td>${r.trailing_sl ? '$'+r.trailing_sl.toLocaleString('es-CO') : '--'}</td>
                <td>${r.confluence ? (r.confluence*100).toFixed(0)+'%' : '--'}</td>
                <td class="${cls}">${r.resultado}</td>
            </tr>`;
        }).join('');
    } catch(e) {}
}

async function loadStats() {
    try {
        const resp = await fetch(`/api/stats/${currentTf}`);
        const s = await resp.json();
        document.getElementById('stat-total').textContent = s.total_signals;
        document.getElementById('stat-wins').textContent = s.wins;
        document.getElementById('stat-losses').textContent = s.losses;
        document.getElementById('stat-winrate').textContent = `${s.win_rate}%`;
        document.getElementById('stat-confluence').textContent = `${(s.avg_confluence*100).toFixed(0)}%`;
    } catch(e) {}
}

function connect() {
    const ws = new WebSocket(`ws://${location.host}/ws`);
    const status = document.getElementById('status');
    ws.onopen = () => { status.textContent = '🟢 En vivo'; status.classList.remove('disconnected'); };
    ws.onclose = () => { status.textContent = '🔴 Desconectado'; status.classList.add('disconnected'); setTimeout(connect, 3000); };
    ws.onmessage = (e) => { updateUI(JSON.parse(e.data)); loadResults(); loadStats(); };
}

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelector('.tab.active').classList.remove('active');
        tab.classList.add('active');
        currentTf = tab.dataset.tf;
        priceData.labels = []; priceData.data = [];
        loadResults(); loadStats();
    });
});

initChart(); connect(); loadResults(); loadStats();
