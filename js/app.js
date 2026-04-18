const WS_URL = "ws://localhost:8080";

let socket = null;
function connectWS() {
    socket = new WebSocket(WS_URL);

    socket.onopen = function() {
        console.log("WS connected");
        set_status_WS(true);
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handle_message(data);
    };

    socket.onclose = function() {
        console.log("WS disconnected, retrying in 3s...");
        set_status_WS(false);  // ← fix this
        setTimeout(connectWS, 3000);
    };
    socket.onerror = function(err) {
        console.error("WS error:", err);
        socket.close();
    };
}

function set_status_WS(connected) {
    const dot = document.getElementById("ws_dot");
    const label = document.getElementById("ws_label");
    const status = document.getElementById("ws_status");

    if (connected) {
        dot.style.backgroundColor = "var(--accent_cpu)";
        label.textContent = "connected";
        status.textContent = "connected";
    } else {
        dot.style.backgroundColor = "var(--muted)";
        label.textContent = "disconnected";
        status.textContent = "not connected";
    }
}

function handle_message(data) {
    if (data.cpu) update_CPU(data.cpu);
    if (data.memory) update_memory(data.memory);
    if (data.disk) update_disk(data.disk);
    if (data.network) update_network(data.network);
    if (data.uptime) update_uptime(data.uptime);
    if (data.hostname) hostname_change(data.hostname);
    if (data.processes) proccess_table_UPDATE(data.processes);
    if (data.cpu && data.memory) updateSparklines(data.cpu.percent, data.memory.percent);
}

connectWS();


function update_CPU(data) {
    document.getElementById("cpu_val").textContent = data.percent + "%";
    document.getElementById("cpu_bar").style.width = data.percent + "%";
    document.getElementById("cpu_sub").textContent = data.cores + " cores · " + data.ghz + " GHz";
}

function update_memory(data) {
    document.getElementById("mem_val").textContent = data.percent + "%";
    document.getElementById("mem_bar").style.width = data.percent + "%";
    document.getElementById("mem_sub").textContent = data.used + " / " + data.total + " GB used";
}

function update_disk(data) {
    document.getElementById("disk_val").textContent = data.percent + "%";
    document.getElementById("disk_bar").style.width = data.percent + "%";
    document.getElementById("disk_sub").textContent = "↑ " + data.write + " MB/s · ↓ " + data.read + " MB/s";
}

function update_network(data) {
    document.getElementById("net_val").textContent = data.percent + "%";
    document.getElementById("net_bar").style.width = data.percent + "%";
    document.getElementById("net_sub").textContent = "↑ " + data.upload + " MB/s · ↓ " + data.download + " MB/s";
}

function update_uptime(val) {
    document.getElementById("uptime").textContent = val;
}

function hostname_change(val) {
    document.getElementById("host_name").textContent = val;
}

function proccess_table_UPDATE(processes) {
    const body = document.getElementById("table_body");
    const count = document.getElementById("proc_count");

    count.textContent = processes.length + " running";
    if (processes.length === 0) {
        body.innerHTML = '<div class="table_empty">No processes found</div>';
        return;
    }

    body.innerHTML = "";

    processes.forEach(function(proc) {
        const row = document.createElement("div");
        row.className = "table_row";
        row.innerHTML = `
            <span>${proc.name}</span>
            <span>${proc.pid}</span>
            <span>${proc.cpu}%</span>
            <span>${proc.mem}%</span>
            <span>${proc.threads}</span>
            <span class="state_${proc.state.toLowerCase()}">${proc.state}</span>
        `;
        body.appendChild(row);
    });
}


function nav_initialize() {
    const items = document.querySelectorAll(".nav_item");

    items.forEach(function(item) {
        item.addEventListener("click", function() {
            items.forEach(function(i) {
                i.classList.remove("active");
            });
            item.classList.add("active");
        });
    });
}

nav_initialize();







///////////////////////////////////////////////////////////////////////////////////////////////////


const cpuHistory = [];
const memHistory = [];
const MAX_POINTS = 30;

function addSparkPoint(history, value) {
    history.push(value);
    if (history.length > MAX_POINTS) history.shift();
}

function drawSparkline(elementId, history, color) {
    const container = document.getElementById(elementId);
    const width = container.clientWidth;
    const height = container.clientHeight;

    if (history.length < 2) return;

    const points = history.map(function(val, i) {
        const x = (i / (MAX_POINTS - 1)) * width;
        const y = height - (val / 100) * height;
        return x + "," + y;
    }).join(" ");

    container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
            <polyline
                points="${points}"
                fill="none"
                stroke="${color}"
                stroke-width="1.5"
            />
        </svg>
    `;
}

function updateSparklines(cpuPercent, memPercent) {
    addSparkPoint(cpuHistory, cpuPercent);
    addSparkPoint(memHistory, memPercent);
    drawSparkline("cpu_spark", cpuHistory, "#00e5a0");
    drawSparkline("mem_spark", memHistory, "#4d9fff");
}