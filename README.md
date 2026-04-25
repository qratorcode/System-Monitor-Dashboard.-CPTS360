## User Instructions

### Prerequisites
- Node.js
- Python 3 + psutil (run pip install psutil)

### Setup

1. Clone the repo - paste line by line in WSL:

git clone https://github.com/qratorcode/System-Monitor-Dashboard.-CPTS360.git
cd System-Monitor-Dashboard.-CPTS360

2. Install server dependencies (run in WSL):

npm install

3. Start the Python Backend (new terminal):

python backend.py

4. Start the WebSocket Server (new terminal):

node server.js

You should see: WebSocket server listening on port 8080

5. Open index.html in your browser:
   - Direct: right-click index.html in your file explorer -> Open with -> your browser
   - VS Code: open the project folder in VS Code, right-click index.html -> Open with Live Server (requires the Live Server extension)
