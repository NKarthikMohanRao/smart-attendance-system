import React, { useRef, useState, useEffect } from 'react';

const Kiosk: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [running, setRunning] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'info' | 'success' | 'warning' | 'error' | ''>('');
  
  const intervalRef = useRef<number | null>(null);

  const startKiosk = async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: true });
      setStream(s);
      if (videoRef.current) {
        videoRef.current.srcObject = s;
        await videoRef.current.play();
      }
      setRunning(true);
      showStatus('Started Kiosk Scanner. Looking for faces...', 'info');

      intervalRef.current = window.setInterval(processFrame, 2000);
    } catch (err) {
      showStatus('Could not access webcam for Kiosk.', 'error');
    }
  };

  const stopKiosk = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      setStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setRunning(false);
    showStatus('Kiosk stopped.', 'info');
    setTimeout(() => {
      setStatusType('');
      setStatusMsg('');
    }, 3000);
  };

  useEffect(() => {
    return () => {
      stopKiosk();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const showStatus = (msg: string, type: 'info' | 'success' | 'warning' | 'error') => {
    setStatusMsg(msg);
    setStatusType(type);
  };

  const processFrame = async () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const image = canvas.toDataURL('image/jpeg', 0.8);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'}/api/kiosk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image })
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        showStatus(`✅ ${data.name} - ${data.event} - ${data.confidence}% Match`, 'success');
      } else if (data.status === 'cooldown') {
        showStatus(`👋 Recognized ${data.name} (Cooldown active)`, 'info');
      } else if (data.status === 'spoof') {
        showStatus(`⚠️ Liveness Check Failed`, 'warning');
      } else if (data.status === 'unknown') {
        showStatus(`❌ Unrecognized Face`, 'error');
      }
    } catch (err) {
      console.error("Kiosk API error", err);
    }
  };

  const overlayStyles = () => {
    if (statusType === 'success') return { backgroundColor: 'var(--success-bg)', color: 'var(--success)', border: '1px solid var(--success)' };
    if (statusType === 'error') return { backgroundColor: 'var(--danger-bg)', color: 'var(--danger)', border: '1px solid var(--danger)' };
    if (statusType === 'warning') return { backgroundColor: 'var(--warning-bg)', color: 'var(--warning)', border: '1px solid var(--warning)' };
    return { backgroundColor: 'var(--info-bg)', color: 'var(--info)', border: '1px solid var(--info)' };
  };

  return (
    <>
      <div className="page-header" style={{ justifyContent: 'center', textAlign: 'center' }}>
        <div>
          <h1>Live Attendance Kiosk</h1>
          <p>Automated face detection and attendance logging</p>
        </div>
      </div>

      <div className="container" style={{ maxWidth: '800px' }}>
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
          
          {statusMsg && (
            <div style={{ position: 'absolute', top: '2rem', zIndex: 10, padding: '0.75rem 1.5rem', borderRadius: 'var(--radius-lg)', fontWeight: 600, boxShadow: 'var(--shadow-md)', ...overlayStyles() }}>
              {statusMsg}
            </div>
          )}

          <div className="camera-preview" style={{ width: '100%', maxWidth: '640px', aspectRatio: '4/3', marginBottom: '1.5rem', border: '4px solid var(--border-color)', borderRadius: 'var(--radius-lg)' }}>
            <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }}></video>
            <div className="camera-overlay"></div>
          </div>
          
          <div style={{ display: 'flex', gap: '1rem' }}>
            {!running && (
              <button onClick={startKiosk} className="btn">Start Kiosk Scanner</button>
            )}
            {running && (
              <button onClick={stopKiosk} className="btn btn-secondary">Stop Kiosk</button>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default Kiosk;
