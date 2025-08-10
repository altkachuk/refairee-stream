from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import subprocess
import os
import time
from datetime import datetime

app = FastAPI()

# Processes
proc_camera = None
proc_rtsp_server = None
proc_ffmpeg = None
proc_recording = None


@app.post("/start_stream")
def start_stream():
    global proc_camera, proc_rtsp_server, proc_ffmpeg

    if proc_camera or proc_rtsp_server or proc_ffmpeg:
        return {"status": "already running"}

    # 1. Start libcamera-vid
    camera_cmd = [
        "rpicam-vid",
        "-t",
        "0",
        "--width",
        "1920",
        "--height",
        "1080",
        "--framerate",
        "12.5",
        "--shutter",
        "15000",
        "--gain",
        "10",
        "--brightness",
        "0.0",
        "--contrast",
        "1.0",
        "--awb",
        "auto",
        "--denoise",
        "cdn_off",
        "--codec",
        "h264",
        "--profile",
        "baseline",
        "--level",
        "4.2",
        "--bitrate",
        "4000000",
        "--inline",
        "--listen",
        "-o",
        "tcp://0.0.0.0:3000",
    ]
    proc_camera = subprocess.Popen(camera_cmd)

    # 2. Start mediamtx
    rtsp_server_cmd = ["./mediamtx"]
    proc_rtsp_server = subprocess.Popen(rtsp_server_cmd)

    # Wait 3 seconds before starting ffmpeg
    time.sleep(3)

    # 3. Start ffmpeg
    ffmpeg_cmd = [
        "ffmpeg",
        "-fflags",
        "+genpts+igndts",
        "-use_wallclock_as_timestamps",
        "1",
        "-analyzeduration",
        "10M",
        "-probesize",
        "10M",
        "-f",
        "h264",
        "-i",
        "tcp://0.0.0.0:3000",
        "-c",
        "copy",
        "-rtsp_transport",
        "tcp",
        "-threads",
        "4",
        "-muxdelay",
        "0",
        "-muxpreload",
        "0",
        "-max_delay",
        "0",
        "-f",
        "rtsp",
        "rtsp://0.0.0.0:8554/stream",
    ]
    proc_ffmpeg = subprocess.Popen(ffmpeg_cmd)

    return {"status": "started"}


@app.post("/stop_stream")
def stop_stream():
    global proc_camera, proc_rtsp_server, proc_ffmpeg

    for proc in (proc_ffmpeg, proc_rtsp_server, proc_camera):
        if proc:
            proc.terminate()

    proc_camera = None
    proc_rtsp_server = None
    proc_ffmpeg = None

    return {"status": "stopped"}


@app.post("/start_recording")
def start_recording():
    global proc_recording

    if proc_recording:
        return {"status": "already recording"}

    now = datetime.now()  # current date and time

    now_str = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    filename = f"./recordings/{now_str}.mp4"  # make sure this folder exists

    ffmpeg_cmd = ["ffmpeg", "-i", "rtsp://192.168.100.100:8554/stream", "-c", "copy", filename]

    try:
        proc_recording = subprocess.Popen(ffmpeg_cmd)
        return {"status": "recording started", "filename": filename}
    except Exception as e:
        return {"status": f"error: {str(e)}"}


@app.post("/stop_recording")
def stop_recording():
    global proc_recording
    if proc_recording is None:
        return {"status": "no recording in progress"}

    # Terminate ffmpeg recording process
    proc_recording.terminate()
    proc_recording = None

    return {"status": "recording stopped"}


@app.get("/status")
def status():
    return {
        "camera_running": proc_camera is not None,
        "rtsp_server_running": proc_rtsp_server is not None,
        "ffmpeg_running": proc_ffmpeg is not None,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
        <head>
            <title>Stream Control</title>
        </head>
        <body>
            <h1>Camera Stream</h1>
            <button id="startStreamBtn" onclick="startStream()">Start Stream</button>
            <button id="stopStreamBtn" onclick="stopStream()" disabled>Stop Stream</button>

            <div>
                <h3>Live Stream Status: <span id="streamStatus">Stream is stopped</span></h3>
            </div>

            <div id="recordingControls" style="display:none;">
                <button id="startRecordBtn" onclick="startRecording()">Start Recording</button>
                <button id="stopRecordBtn" onclick="stopRecording()" style="display:none;">Stop Recording</button>
                <p id="recordingStatus"></p>
            </div>

            <script>
                async function startStream() {
                    await fetch('/start_stream', { method: 'POST' });
                    document.getElementById('streamStatus').textContent = 'Stream is active';
                    document.getElementById('startStreamBtn').disabled = true;
                    document.getElementById('stopStreamBtn').disabled = false;

                    // Show recording controls
                    document.getElementById('recordingControls').style.display = 'block';
                    document.getElementById('startRecordBtn').style.display = 'inline';
                    document.getElementById('stopRecordBtn').style.display = 'none';
                    document.getElementById('recordingStatus').textContent = '';

                    // No video tag here, just status and buttons
                }

                async function stopStream() {
                    await fetch('/stop_stream', { method: 'POST' });
                    document.getElementById('streamStatus').textContent = 'Stream is stopped';
                    document.getElementById('startStreamBtn').disabled = false;
                    document.getElementById('stopStreamBtn').disabled = true;

                    // Hide recording controls
                    document.getElementById('recordingControls').style.display = 'none';
                    document.getElementById('recordingStatus').textContent = '';
                }

                async function startRecording() {
                    const response = await fetch('/start_recording', { method: 'POST' });
                    const data = await response.json();

                    if(data.status === 'recording started') {
                        document.getElementById('recordingStatus').textContent = 'Recording started: ' + data.filename;
                        document.getElementById('startRecordBtn').style.display = 'none';
                        document.getElementById('stopRecordBtn').style.display = 'inline';
                    } else {
                        document.getElementById('recordingStatus').textContent = data.status;
                    }
                }

                async function stopRecording() {
                    const response = await fetch('/stop_recording', { method: 'POST' });
                    const data = await response.json();

                    document.getElementById('recordingStatus').textContent = data.status;
                    if(data.status === 'recording stopped') {
                        document.getElementById('startRecordBtn').style.display = 'inline';
                        document.getElementById('stopRecordBtn').style.display = 'none';
                    }
                }
            </script>
        </body>
    </html>
    """
