"""
DGX Management API - FastAPI backend for web-ui
Provides container management, system monitoring, and Claude Code endpoints.
"""

import asyncio
import subprocess
import json
import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
import shutil
import docker
import psutil

app = FastAPI(
    title="DGX Management API",
    description="Backend API for managing DGX services",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Docker client - connects via mounted socket
client = docker.from_env()

# Known service containers
MANAGED_SERVICES = {
    "comfyui": {"container": "comfyui", "description": "Image/Video generation"},
    "open-webui": {"container": "open-webui", "description": "Chat interface"},
    "chatterbox": {"container": "chatterbox-tts-server-cu128", "description": "Text-to-speech"},
    "ultravox": {"container": "ultravox-vllm", "description": "Speech LLM"},
    "trinity-backend": {"container": "trinity-backend", "description": "Trinity API"},
    "trinity-frontend": {"container": "trinity-frontend", "description": "Trinity UI"},
    "trinity-mcp": {"container": "trinity-mcp", "description": "Trinity MCP Server"},
}


class CommandRequest(BaseModel):
    command: str
    timeout: int = 30


class ContainerAction(BaseModel):
    action: str  # start, stop, restart


class ClaudeCodeRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    allowed_tools: Optional[List[str]] = None  # e.g., ["Bash", "Read", "Edit"]


class ClaudeCodeResponse(BaseModel):
    result: str
    session_id: str
    duration_ms: int
    cost_usd: float
    is_error: bool


class SaveSessionRequest(BaseModel):
    session_id: str
    name: str
    first_message: Optional[str] = None


class GooseChatRequest(BaseModel):
    message: str
    mode: str = "chat"  # "chat" for quick Q&A, "research" for full research agent


# Claude Code executable path and Sparky agent directory
CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")
SPARKY_WORKING_DIR = os.path.expanduser("~/agent-sparky")

# Goose executable path and research directory
GOOSE_PATH = os.path.expanduser("~/.local/bin/goose")
GOOSE_RESEARCH_DIR = os.path.expanduser("~/goose-research")
GOOSE_DATA_DIR = os.path.expanduser("~/goose-research/data")

# Session storage files
SESSIONS_FILE = os.path.expanduser("~/.dgx-web-ui-sessions.json")

# Rick agent path and sessions (Family Assistant using agent-rick)
RICK_SESSIONS_FILE = os.path.expanduser("~/.dgx-web-ui-rick-sessions.json")
RICK_PATH = os.path.expanduser("~/.local/bin/claude")
RICK_WORKING_DIR = os.path.expanduser("~/agent-rick")

# Upload directories for agents
UPLOAD_DIRS = {
    "rick": os.path.expanduser("~/agent-rick/uploads"),
    "sparky": os.path.expanduser("~/agent-sparky/uploads"),
}

# Ensure upload directories exist
for upload_dir in UPLOAD_DIRS.values():
    os.makedirs(upload_dir, exist_ok=True)


def load_sessions() -> dict:
    """Load saved sessions from JSON file"""
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"sessions": []}
    return {"sessions": []}


def save_sessions(data: dict):
    """Save sessions to JSON file"""
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ============ Health & Info ============

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/info")
async def get_info():
    """Get Docker and system info"""
    try:
        info = client.info()
        return {
            "docker_version": client.version()["Version"],
            "containers_running": info["ContainersRunning"],
            "containers_total": info["Containers"],
            "images": info["Images"],
            "memory_total_gb": round(info["MemTotal"] / (1024**3), 1),
            "cpus": info["NCPU"],
            "os": info["OperatingSystem"],
            "architecture": info["Architecture"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Container Management ============

@app.get("/api/containers")
async def list_containers(all: bool = False):
    """List all containers with status"""
    try:
        containers = client.containers.list(all=all)
        result = []
        for c in containers:
            # Find if it's a managed service
            service_name = None
            for name, info in MANAGED_SERVICES.items():
                if info["container"] in c.name:
                    service_name = name
                    break

            result.append({
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "service": service_name,
                "ports": c.ports,
            })
        return {"containers": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/containers/{container_name}")
async def get_container(container_name: str):
    """Get details for a specific container"""
    try:
        container = client.containers.get(container_name)
        return {
            "id": container.short_id,
            "name": container.name,
            "status": container.status,
            "image": container.image.tags[0] if container.image.tags else container.image.short_id,
            "ports": container.ports,
            "created": container.attrs["Created"],
            "state": container.attrs["State"],
        }
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/containers/{container_name}/action")
async def container_action(container_name: str, action: ContainerAction):
    """Perform action on container: start, stop, restart"""
    try:
        container = client.containers.get(container_name)

        if action.action == "start":
            container.start()
            return {"message": f"Container '{container_name}' started", "status": "started"}
        elif action.action == "stop":
            container.stop(timeout=10)
            return {"message": f"Container '{container_name}' stopped", "status": "stopped"}
        elif action.action == "restart":
            container.restart(timeout=10)
            return {"message": f"Container '{container_name}' restarted", "status": "restarted"}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")

    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/containers/{container_name}/logs")
async def get_container_logs(container_name: str, lines: int = 100):
    """Get container logs"""
    try:
        container = client.containers.get(container_name)
        logs = container.logs(tail=lines, timestamps=True).decode("utf-8")
        return {"container": container_name, "logs": logs}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Services (Managed Containers + Ollama) ============

def check_ollama_status():
    """Check if Ollama is running via process check"""
    try:
        # Check if ollama process is running (snap or direct install)
        result = subprocess.run(
            ["pgrep", "-f", "ollama.*serve"],
            capture_output=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return "running"
        return "stopped"
    except Exception:
        return "unknown"

@app.get("/api/services")
async def list_services():
    """List all managed services with their status"""
    services = []

    # Add Docker container services
    for name, info in MANAGED_SERVICES.items():
        try:
            container = client.containers.get(info["container"])
            status = container.status
        except docker.errors.NotFound:
            status = "not found"
        except Exception:
            status = "error"

        services.append({
            "name": name,
            "container": info["container"],
            "description": info["description"],
            "status": status,
        })

    # Add Ollama (process-based service)
    services.append({
        "name": "ollama",
        "container": None,
        "description": "LLM inference engine",
        "status": check_ollama_status(),
    })

    return {"services": services}


@app.post("/api/services/{service_name}/restart")
async def restart_service(service_name: str):
    """Restart a managed service by name"""
    # Special handling for Ollama
    # Note: Ollama runs via snap on the host. We can kill it and snap will auto-restart.
    # Container can see host processes via pid:host but can't run snap commands.
    if service_name == "ollama":
        try:
            # Kill Ollama processes - snap will auto-restart if enabled
            subprocess.run(["pkill", "-f", "ollama.*serve"], timeout=10, check=False)
            await asyncio.sleep(3)  # Wait for snap auto-restart
            status = check_ollama_status()
            if status == "running":
                return {"message": "Ollama restarted (snap auto-restart)", "status": status}
            else:
                return {"message": "Ollama stopped. Start manually via SSH or Management page if snap auto-restart is disabled.", "status": status}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to restart Ollama: {str(e)}")

    # Docker container services
    if service_name not in MANAGED_SERVICES:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_name}")

    container_name = MANAGED_SERVICES[service_name]["container"]
    try:
        container = client.containers.get(container_name)
        container.restart(timeout=10)
        return {"message": f"Service '{service_name}' restarted", "container": container_name}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/services/{service_name}/start")
async def start_service(service_name: str):
    """Start a service"""
    if service_name == "ollama":
        # Cannot start Ollama from container - snap is on host, not in container
        # User needs to use SSH: snap start ollama
        raise HTTPException(
            status_code=501,
            detail="Cannot start Ollama from container. Use SSH: 'snap start ollama' or try Restart button (uses snap auto-restart)"
        )

    # Docker containers not supported yet
    raise HTTPException(status_code=501, detail="Start not implemented for containers")


@app.post("/api/services/{service_name}/stop")
async def stop_service(service_name: str):
    """Stop a service"""
    if service_name == "ollama":
        try:
            # Kill Ollama processes
            subprocess.run(["pkill", "-f", "ollama.*serve"], timeout=10, check=False)
            await asyncio.sleep(1)
            status = check_ollama_status()
            return {"message": "Ollama stopped", "status": status}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to stop Ollama: {str(e)}")

    # Docker containers not supported yet
    raise HTTPException(status_code=501, detail="Stop not implemented for containers")


# ============ GPU & System Stats ============

def parse_nvidia_value(val, type_fn=int, default=0):
    """Parse nvidia-smi value, handling N/A and [N/A]"""
    val = val.strip().replace("[", "").replace("]", "")
    if val.upper() == "N/A" or val == "":
        return default
    try:
        return type_fn(val)
    except (ValueError, TypeError):
        return default


@app.get("/api/gpu")
async def get_gpu_stats():
    """Get GPU stats via nvidia-smi"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="nvidia-smi failed")

        parts = result.stdout.strip().split(", ")
        if len(parts) >= 6:
            return {
                "name": parts[0].strip(),
                "memory_used_mb": parse_nvidia_value(parts[1], int, 0),
                "memory_total_mb": parse_nvidia_value(parts[2], int, 128000),
                "utilization_percent": parse_nvidia_value(parts[3], int, 0),
                "temperature_c": parse_nvidia_value(parts[4], int, 0),
                "power_draw_w": parse_nvidia_value(parts[5], float, 0.0),
            }
        return {"raw": result.stdout}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="nvidia-smi timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="nvidia-smi not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/disk")
async def get_disk_stats():
    """Get disk usage stats"""
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            return {
                "filesystem": parts[0],
                "size": parts[1],
                "used": parts[2],
                "available": parts[3],
                "use_percent": parts[4],
            }
        return {"raw": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/processes")
async def get_top_processes(limit: int = 10):
    """Get top processes by CPU and memory usage, plus GPU processes"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'cmdline']):
            try:
                info = proc.info
                # Skip kernel processes and very low usage
                if info['cpu_percent'] is None or info['memory_percent'] is None:
                    continue
                # Build a useful cmdline summary
                cmdline = info['cmdline']
                if cmdline:
                    # Join full cmdline but truncate to reasonable length
                    full_cmd = ' '.join(cmdline)
                    # Truncate at 120 chars for display
                    cmdline_display = full_cmd[:120] + ('...' if len(full_cmd) > 120 else '')
                else:
                    cmdline_display = info['name']

                processes.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'cpu_percent': round(info['cpu_percent'], 1),
                    'memory_percent': round(info['memory_percent'], 1),
                    'memory_mb': round(info['memory_info'].rss / (1024 * 1024), 1) if info['memory_info'] else 0,
                    'cmdline': cmdline_display
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort by CPU, then memory
        top_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
        top_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:limit]

        # Get GPU processes via nvidia-smi
        gpu_processes = []
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,used_memory,process_name", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        gpu_processes.append({
                            'pid': int(parts[0]),
                            'gpu_memory_mb': int(parts[1]),
                            'name': parts[2].split('/')[-1]  # Get just the process name
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return {
            'top_cpu': top_cpu,
            'top_memory': top_memory,
            'gpu_processes': gpu_processes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Trinity Management ============

TRINITY_SERVICES = ["trinity-backend", "trinity-frontend", "trinity-mcp"]

@app.get("/api/trinity/status")
async def get_trinity_status():
    """Get Trinity-specific status including version"""
    services = []
    for name in TRINITY_SERVICES:
        container_name = name
        try:
            container = client.containers.get(container_name)
            status = container.status
        except docker.errors.NotFound:
            status = "not found"
        except Exception:
            status = "error"

        services.append({
            "name": name.replace("trinity-", ""),
            "container": container_name,
            "status": status,
        })

    # Get git version
    version = None
    try:
        result = subprocess.run(
            ["git", "-C", os.path.expanduser("~/trinity"), "log", "-1", "--format=%h %s (%cr)"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
    except Exception:
        pass

    return {"services": services, "version": version}


@app.post("/api/trinity/update")
async def update_trinity():
    """Pull latest Trinity from GitHub and restart containers.
    Note: Build is skipped because docker compose build doesn't work from inside a container.
    If you need to rebuild images, use the /update-trinity skill or run manually on the DGX.
    """
    trinity_dir = os.path.expanduser("~/trinity")
    results = {"steps": [], "success": True, "error": None}

    try:
        # Step 1: Git pull
        results["steps"].append({"name": "git_pull", "status": "running"})
        pull_result = subprocess.run(
            ["git", "-C", trinity_dir, "pull", "origin", "main"],
            capture_output=True, text=True, timeout=60
        )
        if pull_result.returncode != 0:
            results["steps"][-1]["status"] = "failed"
            results["steps"][-1]["output"] = pull_result.stderr
            results["success"] = False
            results["error"] = "Git pull failed"
            return results
        results["steps"][-1]["status"] = "done"
        results["steps"][-1]["output"] = pull_result.stdout.strip()

        # Step 2: Restart containers (skip build - doesn't work from inside container)
        results["steps"].append({"name": "restart", "status": "running"})
        subprocess.run(
            ["docker", "compose", "down"],
            capture_output=True, timeout=30, cwd=trinity_dir
        )
        up_result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            capture_output=True, text=True, timeout=180, cwd=trinity_dir
        )
        if up_result.returncode != 0:
            results["steps"][-1]["status"] = "failed"
            results["success"] = False
            results["error"] = "Container restart failed"
            return results
        results["steps"][-1]["status"] = "done"

        # Get new version
        version_result = subprocess.run(
            ["git", "-C", trinity_dir, "log", "-1", "--format=%h %s (%cr)"],
            capture_output=True, text=True, timeout=5
        )
        results["version"] = version_result.stdout.strip() if version_result.returncode == 0 else None

        return results

    except subprocess.TimeoutExpired:
        results["success"] = False
        results["error"] = "Operation timed out"
        return results
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
        return results


@app.post("/api/trinity/restart")
async def restart_trinity():
    """Restart all Trinity containers"""
    trinity_dir = os.path.expanduser("~/trinity")
    try:
        subprocess.run(
            ["docker", "compose", "restart"],
            capture_output=True, timeout=60, cwd=trinity_dir
        )
        return {"success": True, "message": "Trinity restarted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Shell Commands (Limited) ============

ALLOWED_COMMANDS = [
    "nvidia-smi",
    "df -h",
    "free -h",
    "uptime",
    "docker stats --no-stream",
    "ollama list",
]

@app.post("/api/exec")
async def exec_command(request: CommandRequest):
    """Execute a whitelisted command"""
    cmd = request.command.strip()

    # Check if command is allowed
    if not any(cmd.startswith(allowed) for allowed in ALLOWED_COMMANDS):
        raise HTTPException(
            status_code=403,
            detail=f"Command not allowed. Allowed: {ALLOWED_COMMANDS}"
        )

    try:
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True,
            timeout=request.timeout
        )
        return {
            "command": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail=f"Command timed out after {request.timeout}s")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Claude Code Integration ============

@app.get("/api/claude/status")
async def claude_status():
    """Check if Claude Code is available"""
    try:
        result = subprocess.run(
            [CLAUDE_PATH, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {
                "available": True,
                "version": result.stdout.strip(),
                "path": CLAUDE_PATH
            }
        return {"available": False, "error": result.stderr}
    except FileNotFoundError:
        return {"available": False, "error": "Claude Code not found"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.post("/api/claude/chat")
async def claude_chat(request: ClaudeCodeRequest):
    """Send a message to Claude Code and get a response"""
    try:
        # Build command with dangerously-skip-permissions for autonomous execution
        cmd = [
            CLAUDE_PATH,
            "-p", request.message,
            "--output-format", "json",
            "--dangerously-skip-permissions"  # YOLO mode - no approval needed
        ]

        # Add session continuation if provided
        if request.session_id:
            cmd.extend(["--resume", request.session_id])

        # Add allowed tools if specified
        if request.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

        # Run Claude Code with timeout (5 minutes max)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"}
        )

        if result.returncode != 0:
            return {
                "result": f"Error: {result.stderr or 'Unknown error'}",
                "session_id": None,
                "duration_ms": 0,
                "cost_usd": 0,
                "is_error": True
            }

        # Parse JSON response
        try:
            data = json.loads(result.stdout)
            return {
                "result": data.get("result", "No response"),
                "session_id": data.get("session_id"),
                "duration_ms": data.get("duration_ms", 0),
                "cost_usd": data.get("total_cost_usd", 0),
                "is_error": data.get("is_error", False)
            }
        except json.JSONDecodeError:
            # Return raw output if not JSON
            return {
                "result": result.stdout,
                "session_id": None,
                "duration_ms": 0,
                "cost_usd": 0,
                "is_error": False
            }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Claude Code request timed out (5 min limit)")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Claude Code not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Session Management ============

@app.get("/api/claude/sessions")
async def list_sessions():
    """List all saved sessions"""
    data = load_sessions()
    return {"sessions": data.get("sessions", [])}


@app.post("/api/claude/sessions")
async def save_session(request: SaveSessionRequest):
    """Save or update a session"""
    from datetime import datetime

    data = load_sessions()
    sessions = data.get("sessions", [])

    # Check if session already exists
    existing = next((s for s in sessions if s["session_id"] == request.session_id), None)

    if existing:
        # Update existing session
        existing["name"] = request.name
        existing["updated_at"] = datetime.now().isoformat()
        if request.first_message:
            existing["first_message"] = request.first_message
    else:
        # Add new session
        sessions.append({
            "session_id": request.session_id,
            "name": request.name,
            "first_message": request.first_message or "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

    data["sessions"] = sessions
    save_sessions(data)
    return {"success": True, "session_id": request.session_id}


@app.delete("/api/claude/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a saved session"""
    data = load_sessions()
    sessions = data.get("sessions", [])

    original_count = len(sessions)
    sessions = [s for s in sessions if s["session_id"] != session_id]

    if len(sessions) == original_count:
        raise HTTPException(status_code=404, detail="Session not found")

    data["sessions"] = sessions
    save_sessions(data)
    return {"success": True, "deleted": session_id}


# ============ File Upload ============

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    agent: str = Form(default="sparky")
):
    """Upload a file for an agent to access.

    Files are stored in the agent's uploads directory and can be referenced
    in prompts. Supports images (jpg, png, gif, webp) and PDFs.
    """
    # Validate agent
    if agent not in UPLOAD_DIRS:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {agent}. Valid agents: {list(UPLOAD_DIRS.keys())}")

    upload_dir = UPLOAD_DIRS[agent]

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check file size by reading content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB")

    # Generate unique filename
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"{unique_id}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(upload_dir, safe_filename)

    # Save file
    try:
        with open(file_path, 'wb') as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return {
        "success": True,
        "filename": safe_filename,
        "path": file_path,
        "size": len(content),
        "agent": agent
    }


@app.get("/api/uploads/{agent}")
async def list_uploads(agent: str):
    """List uploaded files for an agent"""
    if agent not in UPLOAD_DIRS:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {agent}")

    upload_dir = UPLOAD_DIRS[agent]
    files = []

    if os.path.exists(upload_dir):
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    "name": filename,
                    "path": filepath,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        files.sort(key=lambda x: x["modified"], reverse=True)

    return {"files": files, "agent": agent}


@app.delete("/api/uploads/{agent}/{filename}")
async def delete_upload(agent: str, filename: str):
    """Delete an uploaded file"""
    if agent not in UPLOAD_DIRS:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {agent}")

    upload_dir = UPLOAD_DIRS[agent]
    file_path = os.path.join(upload_dir, filename)

    # Security check - ensure we're not deleting outside uploads dir
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath(upload_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        os.remove(file_path)
        return {"success": True, "deleted": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@app.post("/api/claude/chat/stream")
async def claude_chat_stream(request: ClaudeCodeRequest):
    """Stream response from Claude Code using SSE.

    Returns Server-Sent Events with the following event types:
    - init: Initial event with basic info
    - message: Claude's streaming text output
    - tool_use: When Claude uses a tool
    - result: Final result with session_id and cost
    - error: If an error occurs
    - done: Stream complete
    """
    async def generate():
        import time
        start_time = time.time()
        session_id = request.session_id
        accumulated_text = []

        try:
            cmd = [
                CLAUDE_PATH,
                "-p", request.message,
                "--output-format", "stream-json",
                "--verbose",  # Required when using stream-json with --print
                "--dangerously-skip-permissions"  # YOLO mode - no approval needed
            ]

            if request.session_id:
                cmd.extend(["--resume", request.session_id])

            if request.allowed_tools:
                cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

            # Send init event
            yield f"data: {json.dumps({'type': 'init', 'message': 'Starting Claude Code...'})}\n\n"

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=SPARKY_WORKING_DIR,  # Run in agent-sparky directory for Sparky context
                env={**os.environ, "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"}
            )

            # Read stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_text = line.decode('utf-8').strip()
                if not line_text:
                    continue

                try:
                    # Parse the stream-json event
                    event = json.loads(line_text)
                    event_type = event.get('type', 'unknown')

                    # Extract session_id from any event that has it
                    if 'session_id' in event and not session_id:
                        session_id = event['session_id']

                    # Handle different event types from Claude Code stream-json
                    if event_type == 'assistant':
                        # Assistant message with content
                        message = event.get('message', {})
                        content = message.get('content', [])
                        for block in content:
                            if block.get('type') == 'text':
                                text = block.get('text', '')
                                accumulated_text.append(text)
                                yield f"data: {json.dumps({'type': 'message', 'text': text, 'session_id': session_id})}\n\n"
                            elif block.get('type') == 'tool_use':
                                tool_name = block.get('name', 'unknown')
                                yield f"data: {json.dumps({'type': 'tool_use', 'tool': tool_name, 'session_id': session_id})}\n\n"

                    elif event_type == 'result':
                        # Final result event
                        result_text = event.get('result', '')
                        cost = event.get('total_cost_usd', 0)
                        duration_ms = int((time.time() - start_time) * 1000)
                        final_session_id = event.get('session_id', session_id)

                        yield f"data: {json.dumps({'type': 'result', 'result': result_text, 'session_id': final_session_id, 'cost_usd': cost, 'duration_ms': duration_ms})}\n\n"

                    elif event_type == 'error':
                        error_msg = event.get('error', {}).get('message', 'Unknown error')
                        yield f"data: {json.dumps({'type': 'error', 'error': error_msg, 'session_id': session_id})}\n\n"

                    elif event_type == 'system':
                        # System messages (e.g., "Thinking...")
                        system_msg = event.get('message', '')
                        if system_msg:
                            yield f"data: {json.dumps({'type': 'system', 'message': system_msg, 'session_id': session_id})}\n\n"

                    else:
                        # Forward other events as-is for debugging
                        event['session_id'] = session_id
                        yield f"data: {json.dumps(event)}\n\n"

                except json.JSONDecodeError:
                    # Not JSON, forward as raw text
                    accumulated_text.append(line_text)
                    yield f"data: {json.dumps({'type': 'message', 'text': line_text, 'session_id': session_id})}\n\n"

            # Wait for process to complete
            await process.wait()

            # Check for errors in stderr
            stderr_data = await process.stderr.read()
            if process.returncode != 0 and stderr_data:
                error_text = stderr_data.decode('utf-8').strip()
                yield f"data: {json.dumps({'type': 'error', 'error': error_text, 'session_id': session_id})}\n\n"

            # Send final done event
            duration_ms = int((time.time() - start_time) * 1000)
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'duration_ms': duration_ms})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected
            yield f"data: {json.dumps({'type': 'cancelled', 'session_id': session_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============ Goose Research Agent Integration ============

@app.get("/api/goose/status")
async def goose_status():
    """Check if Goose is available"""
    try:
        result = subprocess.run(
            [GOOSE_PATH, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {
                "available": True,
                "version": result.stdout.strip(),
                "path": GOOSE_PATH
            }
        return {"available": False, "error": result.stderr}
    except FileNotFoundError:
        return {"available": False, "error": "Goose not found"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.post("/api/goose/chat")
async def goose_chat(request: GooseChatRequest):
    """Send a message to Goose research agent"""
    import time
    start_time = time.time()

    try:
        # Build command based on mode
        if request.mode == "research":
            # Use the research recipe for full research with saving
            cmd = [
                GOOSE_PATH, "run",
                "--recipe", os.path.join(GOOSE_RESEARCH_DIR, "research-agent.yaml"),
                "--params", f"topic={request.message}"
            ]
        else:
            # Quick chat mode - just run with text
            cmd = [
                GOOSE_PATH, "run",
                "--text", request.message
            ]

        # Set environment for Ollama (use env var or default to host.docker.internal for container)
        ollama_host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
        env = {
            **os.environ,
            "OLLAMA_HOST": ollama_host,
            "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"
        }

        # Run Goose with timeout (10 minutes for research, 3 minutes for chat)
        timeout = 600 if request.mode == "research" else 180
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=GOOSE_RESEARCH_DIR
        )

        duration_ms = int((time.time() - start_time) * 1000)

        if result.returncode != 0:
            return {
                "result": f"Error: {result.stderr or 'Unknown error'}",
                "duration_ms": duration_ms,
                "sources": [],
                "saved_file": None,
                "is_error": True
            }

        # Parse output to extract sources if present
        output = result.stdout
        sources = []
        saved_file = None

        # Try to extract URLs from output
        import re
        # Match URLs but exclude trailing punctuation like ), ], etc.
        raw_urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', output)
        # Clean up URLs by removing trailing punctuation
        cleaned_urls = []
        for url in raw_urls:
            # Remove trailing punctuation that's often not part of the URL
            url = url.rstrip('.,;:!?)>\'"')
            if url and len(url) > 10:  # Basic sanity check
                cleaned_urls.append(url)
        sources = list(set(cleaned_urls))[:10]  # Dedupe and limit to 10

        # Check if a file was saved (look for "Saved to:" pattern)
        saved_match = re.search(r'(?:Saved to|saved to|Saving to):\s*([^\s\n]+\.md)', output)
        if saved_match:
            saved_file = saved_match.group(1)

        return {
            "result": output,
            "duration_ms": duration_ms,
            "sources": sources,
            "saved_file": saved_file,
            "is_error": False
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"Goose request timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Goose not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/goose/research")
async def list_research():
    """List all saved research files"""
    try:
        files = []
        if os.path.exists(GOOSE_DATA_DIR):
            for filename in os.listdir(GOOSE_DATA_DIR):
                if filename.endswith('.md'):
                    filepath = os.path.join(GOOSE_DATA_DIR, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "name": filename,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    })
            # Sort by modified time, newest first
            files.sort(key=lambda x: x["modified"], reverse=True)
            # Convert mtime to ISO format
            from datetime import datetime
            for f in files:
                f["modified"] = datetime.fromtimestamp(f["modified"]).isoformat()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/goose/research/{filename}")
async def get_research(filename: str):
    """Get content of a research file"""
    try:
        filepath = os.path.join(GOOSE_DATA_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")

        # Security check - ensure we're not reading outside data dir
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(os.path.realpath(GOOSE_DATA_DIR)):
            raise HTTPException(status_code=403, detail="Access denied")

        with open(filepath, 'r') as f:
            content = f.read()
        return {"content": content, "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/goose/research/{filename}")
async def delete_research(filename: str):
    """Delete a research file"""
    try:
        filepath = os.path.join(GOOSE_DATA_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")

        # Security check
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(os.path.realpath(GOOSE_DATA_DIR)):
            raise HTTPException(status_code=403, detail="Access denied")

        os.remove(filepath)
        return {"success": True, "deleted": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Rick Agent Integration (Family Assistant) ============

def load_rick_sessions() -> dict:
    """Load saved Rick sessions from JSON file"""
    if os.path.exists(RICK_SESSIONS_FILE):
        try:
            with open(RICK_SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"sessions": []}
    return {"sessions": []}


def save_rick_sessions(data: dict):
    """Save Rick sessions to JSON file"""
    with open(RICK_SESSIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@app.get("/api/rick/status")
async def rick_status():
    """Check if Rick agent is available"""
    try:
        result = subprocess.run(
            [RICK_PATH, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {
                "available": True,
                "version": result.stdout.strip(),
                "path": RICK_PATH,
                "working_dir": RICK_WORKING_DIR
            }
        return {"available": False, "error": result.stderr}
    except FileNotFoundError:
        return {"available": False, "error": "Claude Code not found"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/api/rick/sessions")
async def list_rick_sessions():
    """List all saved Rick sessions"""
    data = load_rick_sessions()
    return {"sessions": data.get("sessions", [])}


@app.post("/api/rick/sessions")
async def save_rick_session(request: SaveSessionRequest):
    """Save or update a Rick session"""
    from datetime import datetime

    data = load_rick_sessions()
    sessions = data.get("sessions", [])

    existing = next((s for s in sessions if s["session_id"] == request.session_id), None)

    if existing:
        existing["name"] = request.name
        existing["updated_at"] = datetime.now().isoformat()
        if request.first_message:
            existing["first_message"] = request.first_message
    else:
        sessions.append({
            "session_id": request.session_id,
            "name": request.name,
            "first_message": request.first_message or "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

    data["sessions"] = sessions
    save_rick_sessions(data)
    return {"success": True, "session_id": request.session_id}


@app.delete("/api/rick/sessions/{session_id}")
async def delete_rick_session(session_id: str):
    """Delete a saved Rick session"""
    data = load_rick_sessions()
    sessions = data.get("sessions", [])

    original_count = len(sessions)
    sessions = [s for s in sessions if s["session_id"] != session_id]

    if len(sessions) == original_count:
        raise HTTPException(status_code=404, detail="Session not found")

    data["sessions"] = sessions
    save_rick_sessions(data)
    return {"success": True, "deleted": session_id}


@app.post("/api/rick/chat/stream")
async def rick_chat_stream(request: ClaudeCodeRequest):
    """Stream response from Rick agent using SSE.

    Rick runs Claude Code with the agent-rick working directory context,
    giving it access to family documents and personal information.
    """
    async def generate():
        import time
        start_time = time.time()
        session_id = request.session_id
        accumulated_text = []

        try:
            cmd = [
                RICK_PATH,
                "-p", request.message,
                "--output-format", "stream-json",
                "--verbose",
                "--dangerously-skip-permissions"
            ]

            if request.session_id:
                cmd.extend(["--resume", request.session_id])

            if request.allowed_tools:
                cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

            # Send init event
            yield f"data: {json.dumps({'type': 'init', 'message': 'Starting Rick...'})}\n\n"

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=RICK_WORKING_DIR,  # Run in agent-rick directory for context
                env={**os.environ, "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"}
            )

            # Read stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_text = line.decode('utf-8').strip()
                if not line_text:
                    continue

                try:
                    event = json.loads(line_text)
                    event_type = event.get('type', 'unknown')

                    if 'session_id' in event and not session_id:
                        session_id = event['session_id']

                    if event_type == 'assistant':
                        message = event.get('message', {})
                        content = message.get('content', [])
                        for block in content:
                            if block.get('type') == 'text':
                                text = block.get('text', '')
                                accumulated_text.append(text)
                                yield f"data: {json.dumps({'type': 'message', 'text': text, 'session_id': session_id})}\n\n"
                            elif block.get('type') == 'tool_use':
                                tool_name = block.get('name', 'unknown')
                                yield f"data: {json.dumps({'type': 'tool_use', 'tool': tool_name, 'session_id': session_id})}\n\n"

                    elif event_type == 'result':
                        result_text = event.get('result', '')
                        cost = event.get('total_cost_usd', 0)
                        duration_ms = int((time.time() - start_time) * 1000)
                        final_session_id = event.get('session_id', session_id)

                        yield f"data: {json.dumps({'type': 'result', 'result': result_text, 'session_id': final_session_id, 'cost_usd': cost, 'duration_ms': duration_ms})}\n\n"

                    elif event_type == 'error':
                        error_msg = event.get('error', {}).get('message', 'Unknown error')
                        yield f"data: {json.dumps({'type': 'error', 'error': error_msg, 'session_id': session_id})}\n\n"

                    elif event_type == 'system':
                        system_msg = event.get('message', '')
                        if system_msg:
                            yield f"data: {json.dumps({'type': 'system', 'message': system_msg, 'session_id': session_id})}\n\n"

                    else:
                        event['session_id'] = session_id
                        yield f"data: {json.dumps(event)}\n\n"

                except json.JSONDecodeError:
                    accumulated_text.append(line_text)
                    yield f"data: {json.dumps({'type': 'message', 'text': line_text, 'session_id': session_id})}\n\n"

            await process.wait()

            stderr_data = await process.stderr.read()
            if process.returncode != 0 and stderr_data:
                error_text = stderr_data.decode('utf-8').strip()
                yield f"data: {json.dumps({'type': 'error', 'error': error_text, 'session_id': session_id})}\n\n"

            duration_ms = int((time.time() - start_time) * 1000)
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'duration_ms': duration_ms})}\n\n"

        except asyncio.CancelledError:
            yield f"data: {json.dumps({'type': 'cancelled', 'session_id': session_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


class SessionNameRequest(BaseModel):
    first_message: str
    session_id: str


@app.post("/api/rick/name-session")
async def rick_name_session(request: SessionNameRequest):
    """Generate a meaningful name for a Rick session based on the first message."""
    try:
        # Use Claude to generate a short, meaningful session name
        prompt = f'Name this conversation in 3-5 words (no quotes, no punctuation, just the name): "{request.first_message[:200]}"'

        cmd = [
            RICK_PATH,
            "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=RICK_WORKING_DIR,
            env={**os.environ, "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"}
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

        if process.returncode == 0:
            result = json.loads(stdout.decode('utf-8'))
            name = result.get('result', '').strip()
            # Clean up the name - remove quotes, limit length
            name = name.strip('"\'').strip()[:50]
            if name:
                return {"success": True, "name": name}

        # Fallback: use truncated first message
        fallback = request.first_message[:30].strip()
        if len(request.first_message) > 30:
            fallback += "..."
        return {"success": True, "name": fallback}

    except asyncio.TimeoutError:
        # Timeout - use fallback
        fallback = request.first_message[:30].strip()
        return {"success": True, "name": fallback}
    except Exception as e:
        return {"success": False, "error": str(e), "name": request.first_message[:30]}


@app.post("/api/claude/name-session")
async def claude_name_session(request: SessionNameRequest):
    """Generate a meaningful name for a Sparky session based on the first message."""
    try:
        prompt = f'Name this conversation in 3-5 words (no quotes, no punctuation, just the name): "{request.first_message[:200]}"'

        cmd = [
            CLAUDE_PATH,
            "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=SPARKY_WORKING_DIR,
            env={**os.environ, "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"}
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

        if process.returncode == 0:
            result = json.loads(stdout.decode('utf-8'))
            name = result.get('result', '').strip()
            name = name.strip('"\'').strip()[:50]
            if name:
                return {"success": True, "name": name}

        fallback = request.first_message[:30].strip()
        if len(request.first_message) > 30:
            fallback += "..."
        return {"success": True, "name": fallback}

    except asyncio.TimeoutError:
        fallback = request.first_message[:30].strip()
        return {"success": True, "name": fallback}
    except Exception as e:
        return {"success": False, "error": str(e), "name": request.first_message[:30]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
