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
    if (data.cpu_percent !== undefined) update_CPU(data);
    if (data.memory_percent !== undefined) update_memory(data);
    if (data.disk_read_rate !== undefined || data.disk_write_rate !== undefined) update_disk(data);
    if (data.net_sent_rate !== undefined || data.net_recv_rate !== undefined) update_network(data);
    if (data.uptime) update_uptime(data.uptime);
    if (data.hostname) hostname_change(data.hostname);
    if (data.processes) proccess_table_UPDATE(data.processes);
    if (data.cpu_percent !== undefined && data.memory_percent !== undefined) updateSparklines(data.cpu_percent, data.memory_percent);
}

connectWS();


function update_CPU(data) {
    const value = Math.round(data.cpu_percent * 10) / 10;
    document.getElementById("cpu_val").textContent = value + "%";
    document.getElementById("cpu_bar").style.width = value + "%";
    document.getElementById("cpu_sub").textContent = "Live CPU usage";
}

function update_memory(data) {
    const value = Math.round(data.memory_percent * 10) / 10;
    document.getElementById("mem_val").textContent = value + "%";
    document.getElementById("mem_bar").style.width = value + "%";
    document.getElementById("mem_sub").textContent = data.memory_used_mb.toFixed(1) + " / " + data.memory_total_mb.toFixed(1) + " GB used";
}

function update_disk(data) {
    const readMB = (data.disk_read_rate / 1024 / 1024).toFixed(2);
    const writeMB = (data.disk_write_rate / 1024 / 1024).toFixed(2);
    document.getElementById("disk_val").textContent = readMB + " ↓ / " + writeMB + " ↑ MB/s";
    document.getElementById("disk_bar").style.width = "100%";
    document.getElementById("disk_sub").textContent = "Read " + readMB + " MB/s · Write " + writeMB + " MB/s";
}

function update_network(data) {
    const recvMB = (data.net_recv_rate / 1024 / 1024).toFixed(2);
    const sentMB = (data.net_sent_rate / 1024 / 1024).toFixed(2);
    document.getElementById("net_val").textContent = recvMB + " ↓ / " + sentMB + " ↑ MB/s";
    document.getElementById("net_bar").style.width = "100%";
    document.getElementById("net_sub").textContent = "Download " + recvMB + " MB/s · Upload " + sentMB + " MB/s";
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
        row.setAttribute("role", "row");
        row.innerHTML = `
            <span role="gridcell">${proc.name}</span>
            <span role="gridcell">${proc.pid}</span>
            <span role="gridcell">${proc.cpu_percent.toFixed(1)}%</span>
            <span role="gridcell">${proc.memory_percent.toFixed(1)}%</span>
            <span role="gridcell">${proc.num_threads}</span>
            <span role="gridcell" class="state_${proc.state.toLowerCase()}">${proc.state}</span>
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