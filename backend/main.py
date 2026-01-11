"""
DGX Management API - FastAPI backend for web-ui
Provides container management, system monitoring, and Claude Code endpoints.
"""

import asyncio
import subprocess
import json
import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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


# Claude Code executable path
CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")

# Goose executable path and research directory
GOOSE_PATH = os.path.expanduser("~/.local/bin/goose")
GOOSE_RESEARCH_DIR = os.path.expanduser("~/goose-research")
GOOSE_DATA_DIR = os.path.expanduser("~/goose-research/data")

# Session storage file
SESSIONS_FILE = os.path.expanduser("~/.dgx-web-ui-sessions.json")


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


@app.post("/api/claude/chat/stream")
async def claude_chat_stream(request: ClaudeCodeRequest):
    """Stream response from Claude Code (for future use)"""
    # For now, just return a simple streaming response
    # Real streaming would require --output-format stream-json
    async def generate():
        try:
            cmd = [
                CLAUDE_PATH,
                "-p", request.message,
                "--output-format", "stream-json",
                "--dangerously-skip-permissions"  # YOLO mode
            ]

            if request.session_id:
                cmd.extend(["--resume", request.session_id])

            if request.allowed_tools:
                cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"}
            )

            for line in process.stdout:
                if line.strip():
                    yield f"data: {line}\n\n"

            process.wait()
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
