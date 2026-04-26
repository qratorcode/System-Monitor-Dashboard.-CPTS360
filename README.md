GitHub Repo - https://github.com/qratorcode/System-Monitor-Dashboard.-CPTS360
## User Instructions
### Prerequisites
- Node.js
- Python 3 + psutil (run pip install psutil)
- websockets (run pip install websockets)

### Setup
1. Clone the repo - paste line by line in WSL:
git clone https://github.com/qratorcode/System-Monitor-Dashboard.-CPTS360.git
cd System-Monitor-Dashboard.-CPTS360

2. Install server dependencies (run in WSL):
npm install

3. Start the WebSocket Server (new WSL terminal):
node server.js
You should see: WebSocket server listening on port 8080

4. Start the Python Backend (new PowerShell terminal):
python system_monitor_daemon.py

5. Open http://localhost:3000 in browser

---

## Project Overview and Goals
This project is a web-based system dashboard that replicates the functionality of Windows Task Manager with a modern, web-first approach. The dashboard provides real-time monitoring of critical computer performance metrics in an intuitive, accessible interface.

### Goals
- Educational: Demonstrate proficiency in building performant web applications that interact with system-level data and provide real-time updates
- Portfolio Showcase: Create a visually polished, fully-featured application that highlights full-stack development capabilities and attention to UI/UX design
- Practical Utility: Develop a functional alternative to traditional system monitoring tools for realtime monitoring of CPU, memory, disk, and network performance

### Key Features
- Real-time monitoring of system resources including CPU, Memory, Disk, and Network statistics
- Comprehensive process/service list showing active applications and background services
- Responsive, intuitive interface designed for both desktop and extended monitoring sessions

---

## Course Themes
**Process Scheduling:** The dashboard monitors all active processes in real time, displaying each process by name, PID, CPU/Memory usage, thread count, and state. The daemon uses psutil to iterate over running processes and sorts them by current cpu usage. This mirrors how an OS scheduler prioritizes processes by resource consumption.

**Virtual Memory:** Usage is tracked continually using psutil's virtual memory interface. It reports total memory, used memory, and usage percentage. This is visualized as both a live percentage and a rolling graph showing a 30 second history.

**System I/O Disk and Network Activity:** Monitors as realtime read/write rates in MB/s. The Daemon calculates these rates by comparing cumulative byte counts between updates.

**Concurrent Programming:** The daemon uses a hybrid concurrency model. Python threading handles metric collection while asyncio manages the WebSocket connection to the server. This allows Blocking psutil calls to run without freezing the event loop, enabling updates every 500 milliseconds, without sacrificing network responsiveness.

---

## Design Decisions and Trade-offs

### WebSocket Architecture
We chose WebSocket technology for real-time data communication to enable live system metric updates without constant polling. This decision provided the most responsive user experience, though it required learning a new communication paradigm compared to traditional REST APIs.

The WebSocket system utilizes a two-tier design, where the Python daemon streams raw metrics to the backend, and the frontend connects to a separate endpoint to receive broadcasted updates. This architecture provides a tidy separation of concerns, where the daemon only pushes data and the backend handles distribution and transformation.

### Real-Time Streaming vs. Polling
Instead of using periodic polling, we chose a push-based streaming model. The daemon sends updates approximately every 500 milliseconds, ensuring almost instant changes are reflected in the user interface. This creates a highly responsive experience. However, it also increases bandwidth usage, requiring careful disconnect and reconnect handling. Our decision prioritized real-time accuracy over maximum resource efficiency.

### Connection Reliability and Reconnect Strategy
The daemon and frontend both implement automatic reconnection logic. The daemon uses exponential backoff to avoid overwhelming the server during outages, and the frontend retries every three seconds for a smooth user experience.

This improves resilience but also features trade-offs. Synchronized reconnect bursts are possible due to the frontend's fixed reconnect intervals. Additionally, exponential daemon backoff implies long outages eventually halt attempts to reconnect.

### Broadcast Model for Frontend Clients
The backend stores recent metrics in memory, broadcasting them to all connected clients. This keeps the system simple and quick for minimal users, but does not scale horizontally. Furthermore, it does not support per-client throttling or backpressure. These limitations were accepted because the project focuses on small-scale usage, not large-scale deployment.

### Frontend State and History Management
The frontend stores CPU and memory history locally in vanilla javascript, which avoids backend storage requirements and maintains UI responsiveness. The trade-off is that history resets on refresh and cannot be shared across sessions, but this is acceptable given the project's focus on real-time monitoring instead of long-term analytics.

### Scoped Feature Set
Given the complexity of this being a first full-stack project with WebSocket integration, we made deliberate decisions to scope the initial release. Rather than attempting to implement every Task Manager feature, we focused on core system monitoring (CPU, Memory, Disk, Network, and Processes) to ensure robust implementation of each component. This allowed us to deliver a polished, production-ready application within the project timeline while maintaining code quality.

### Code Organization Priority
Early in development, we learned that code organization becomes increasingly critical as projects grow. We prioritized restructuring our codebase with clear separation of concerns—dividing frontend logic, backend services, and WebSocket handlers into distinct modules. This trade-off involved spending extra time on refactoring but paid dividends in maintainability and debugging efficiency.

---

## Challenges Encountered and Lessons Learned

### Learning Curve: WebSocket Implementation
**Challenge:** WebSocket communication was entirely new to the team. Understanding bidirectional real-time communication, connection management, and error handling required significant research and experimentation.

**Solution & Lesson:** We invested time in studying WebSocket fundamentals and implemented robust error handling with reconnection logic. This foundational knowledge proved invaluable and is now a core competency for building real-time applications.

### Cross-Platform Compatibility
**Challenge:** The daemon was originally written to read system metrics directly from Linux/proc files, which only exist in WSL. This meant that the dashboard was reporting WSL stats instead of the hardware stats.

**Solution & Lesson:** We switched the daemon to use the psutil library, which reads real hardware data. This taught us the importance of testing on the actual target environment early in production, instead of just assuming a solution that works in one environment will automatically work in another.

### Installing Proper Dependencies
**Challenge:** Running generalized commands to install dependencies occasionally leads to broken code and system crashes. Without knowing the specific details of each necessity, we assumed certain dependencies could simply be configured through the command line. However, some dependencies, such as Express.js, work significantly better when specifying an older version in the terminal. Without knowing a dependency's recent updates are problematic, debugging a program is frustrating until such is realized.

**Solution & Lesson:** Sometimes using older versions of certain dependencies, such as Express.js 4 instead of Express.js 5, is acceptable for easier debugging and lack of new feature knowledge. Refactoring our project to work with Express.js 5 would have consumed hours of research and tedious labor.

### Codebase Organization Under Growth
**Challenge:** As the project expanded, our initial monolithic structure became difficult to navigate and maintain. Adding new features required hunting through sprawling files to find the right place to implement logic.

**Solution & Lesson:** We refactored the codebase with clear module separation: dedicated folders for frontend components, backend services, WebSocket handlers, and utilities. This experience taught us that establishing good organizational patterns early—even if it slows initial development—saves exponential time later.

### Scope Management
**Challenge:** The ambition to replicate all Windows Task Manager features while learning multiple new technologies simultaneously threatened project completion.

**Solution & Lesson:** We made the strategic decision to reduce scope to a focused feature set (core metrics and process monitoring). This taught us that shipping a polished, complete product is more valuable than an incomplete ambitious one. It also provided a solid foundation for future feature additions.

---

## Key Takeaways
- WebSockets are powerful for real-time applications but require careful consideration of connection state, error handling, and reconnection strategies
- Backend Abstraction prevents system-specific logic from spreading throughout the codebase and makes the project more maintainable
- Code Organization should be planned early; refactoring becomes exponentially harder as a project grows
- Scope Management is critical in learning projects; delivering a complete core feature set is better than partially implementing many features
