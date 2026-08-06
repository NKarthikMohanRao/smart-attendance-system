import React, { useRef, useState, useEffect } from 'react';

const Register: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState<{ type: string; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        setStatus({ type: 'error', msg: 'Could not access webcam. Please ensure permissions are granted.' });
      }
    };
    startCamera();

    return () => {
      if (videoRef.current?.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    const formData = new FormData(e.currentTarget);
    const emp_code = formData.get('emp_code') as string;
    const name = formData.get('name') as string;
    const department = formData.get('department') as string;
    const designation = formData.get('designation') as string;

    if (!emp_code || !name) {
      setStatus({ type: 'error', msg: 'Employee Code and Name are required.' });
      return;
    }

    setLoading(true);
    setStatus({ type: 'info', msg: 'Capturing images and registering...' });

    const video = videoRef.current;
    if (!video) {
      setStatus({ type: 'error', msg: 'Video not initialized.' });
      setLoading(false);
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    
    if (!ctx) {
      setLoading(false);
      return;
    }

    const images: string[] = [];
    for (let i = 0; i < 3; i++) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      images.push(canvas.toDataURL('image/jpeg', 0.9));
      await new Promise(r => setTimeout(r, 300));
    }

    try {
      const response = await fetch('http://127.0.0.1:5000/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emp_code, name, department, designation, images })
      });
      
      const data = await response.json();
      if (response.ok) {
        setStatus({ type: 'success', msg: data.message || 'Registration successful!' });
        (e.target as HTMLFormElement).reset();
      } else {
        setStatus({ type: 'error', msg: data.error || 'Registration failed.' });
      }
    } catch (err) {
      setStatus({ type: 'error', msg: 'Network error during registration.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="page-header" style={{ justifyContent: 'center', textAlign: 'center' }}>
        <div>
          <h1>Register New Employee</h1>
          <p>Enroll a new user into the facial recognition system</p>
        </div>
      </div>

      <div className="container" style={{ maxWidth: '900px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
          
          <div className="card">
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Employee Details</h2>
            {status && (
              <div className={`status-message ${status.type}`} style={{ display: 'block' }}>
                {status.msg}
              </div>
            )}
            <form onSubmit={handleSubmit} className="form-grid">
              <div className="form-group">
                <label>Employee Code (Unique)</label>
                <input type="text" name="emp_code" placeholder="e.g. EMP101" required />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input type="text" name="name" placeholder="John Doe" required />
              </div>
              <div className="form-group">
                <label>Department</label>
                <input type="text" name="department" placeholder="e.g. Engineering" />
              </div>
              <div className="form-group">
                <label>Designation</label>
                <input type="text" name="designation" placeholder="e.g. Software Engineer" />
              </div>
              <button type="submit" className="btn" style={{ width: '100%', marginTop: '1rem', padding: '1rem' }} disabled={loading}>
                {loading ? 'Processing...' : 'Capture & Register Face'}
              </button>
            </form>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', width: '100%' }}>Live Camera Feed</h2>
            <div className="camera-preview">
              <video ref={videoRef} autoPlay playsInline muted></video>
              <div className="camera-overlay"></div>
            </div>
            <p style={{ marginTop: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)', textAlign: 'center' }}>
              Position your face clearly in the frame.<br/>Ensure good lighting before capturing.
            </p>
          </div>

        </div>
      </div>
    </>
  );
};

export default Register;
