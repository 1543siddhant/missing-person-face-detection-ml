import cv2
import face_recognition
import numpy as np
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, Response, request, redirect, url_for, flash
from jinja2 import DictLoader
import sys
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# ==============================
# Email Settings & Defaults
# ==============================
SENDER_EMAIL = "tensortitans2612@gmail.com"
SENDER_PASSWORD = "hjcy lblh gwhv jmzk"
DEFAULT_RECEIVERS = ["siddhantpatil1543@gmail.com", "siddhantpatil1540@gmail.com"]
DETECTION_EMAIL_SUBJECT = "Missing Person Found"
DETECTION_EMAIL_MESSAGE = "A missing person has been detected. Please see the attached image."

# ==============================
# Global Variables
# ==============================
target_encoding = None       # To store the missing person's face encoding
alert_sent = False           # Flag to prevent multiple detection emails

# ==============================
# Camera Setup (Improved Quality & Speed)
# ==============================
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)

# ==============================
# Helper: Send Email Function
# ==============================
def send_email(subject, message, receivers, attachment_data=None, attachment_filename=None, attachment_subtype="jpeg"):
    try:
        msg = EmailMessage()
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(receivers)
        msg["Subject"] = subject
        msg.set_content(message)
        if attachment_data is not None:
            msg.add_attachment(attachment_data, maintype="image", subtype=attachment_subtype, filename=attachment_filename)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)

# ==============================
# Background Thread to Reset Detection Alert Flag
# ==============================
def reset_alert_flag():
    global alert_sent
    import time
    while True:
        time.sleep(60)  # Reset flag every 60 seconds
        alert_sent = False

threading.Thread(target=reset_alert_flag, daemon=True).start()

# ==============================
# HTML Templates (Using DictLoader)
# ==============================
base_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Missing Person Dashboard</title>
  <!-- Bootstrap CSS -->
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
  <!-- Font Awesome for icons -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    /* Global Styles */
    body {
      background: url("{{ url_for('static', filename='apple.jpg') }}") no-repeat center center;
      background-size: cover;
      color: #e0e0e0;
      font-family: 'Inter', sans-serif;
      margin: 0;
      padding: 0;
    }
    /* Main Content - Centered & Separated from Sidebar */
    .main-content {
      margin: 40px auto;
      max-width: 800px;
      padding: 40px;
      padding-top: 120px; /* To avoid fixed navbar */
      background: rgba(0, 0, 0, 0.75);
      border-radius: 15px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8);
      border: 1px solid rgba(50, 50, 50, 0.8);
      text-align: center;
      position: relative;
      left: 125px;
    }
    /* Sidebar Styling - Light Dark Grey Gradient */
    .sidenav {
      position: fixed;
      top: 0;
      left: 0;
      height: 100%;
      width: 250px;
      background: linear-gradient(135deg, #2a2a2a, #1f1f1f);
      padding: 30px 20px;
      overflow-y: auto;
      box-shadow: 2px 0 8px rgba(0, 0, 0, 0.8);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .sidenav:hover {
      transform: translateX(5px);
      box-shadow: 4px 0 16px rgba(0, 0, 0, 0.9);
    }
    .sidenav h3 {
      margin: 0;
      padding-bottom: 20px;
    }
    /* Tensor Titans Box with Gradient Hover */
    .btn-grad {
      background-image: linear-gradient(to right, #C04848 0%, #480048 51%, #C04848 100%);
      margin: 20px 10px; /* increased vertical spacing */
      padding: 15px 45px;
      text-align: center;
      text-transform: uppercase;
      transition: 0.5s;
      background-size: 200% auto;
      color: white;            
      box-shadow: 0 0 20px #eee;
      border-radius: 15px; /* increased border radius */
      display: block;
    }
    .btn-grad:hover {
      background-position: right center;
      color: #fff;
      text-decoration: none;
    }
    .sidenav .nav-link {
      display: block;
      padding: 12px 10px;
      margin-bottom: 12px;
      color: #ffffff;
      border: 1px solid #444444;
      border-radius: 8px;
      text-align: center;
      font-weight: bold;
      background: rgba(255,255,255,0.05);
      text-decoration: none;
      transition: background 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease, color 0.3s ease;
    }
    .sidenav .nav-link:hover {
      background: #03dac6;
      color: #000000;
      transform: translateY(-3px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.7);
    }
    /* Top Navbar */
    .topnav {
      margin-left: 250px;
      background: linear-gradient(135deg, #1f1f1f, #0d0d0d);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #444444;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
    }
    .breadcrumb {
      background: transparent;
      margin-bottom: 0;
      font-size: 1.1em;
      color: #aaaaaa;
    }
    /* Narrow Input Fields */
    .narrow-field {
      max-width: 400px;
      margin: 10px auto;
    }
    /* Form Controls */
    .form-control, .form-control-file, textarea {
      background-color: #1f1f1f;
      border: 1px solid #444444;
      color: #e0e0e0;
      border-radius: 5px;
      transition: box-shadow 0.3s ease;
    }
    .form-control:focus, textarea:focus {
      box-shadow: 0 0 8px rgba(100, 100, 100, 0.8);
    }
    label {
      font-weight: bold;
      color: #ffffff;
      margin-bottom: 5px;
      display: block;
      background: linear-gradient(135deg, #333333, #222222);
      padding: 5px;
      border-radius: 5px;
      border: 1px solid #555555;
    }
    h1, h2, p {
      text-align: center;
    }
    /* Original Button Styling */
    .btn {
      all: unset;
      padding: 0.5em 1.5em;
      font-size: 16px;
      background: transparent;
      border: none;
      position: relative;
      color: #f0f0f0;
      cursor: pointer;
      z-index: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
      user-select: none;
      -webkit-user-select: none;
      touch-action: manipulation;
      transition: color 250ms;
    }
    .btn::after,
    .btn::before {
      content: "";
      position: absolute;
      bottom: 0;
      right: 0;
      z-index: -1;
      transition: all 0.4s;
    }
    .btn::before {
      transform: translate(0%, 0%);
      width: 100%;
      height: 100%;
      background: #28282d;
      border-radius: 10px;
    }
    .btn::after {
      transform: translate(10px, 10px);
      width: 35px;
      height: 35px;
      background: #ffffff15;
      backdrop-filter: blur(5px);
      -webkit-backdrop-filter: blur(5px);
      border-radius: 50px;
    }
    .btn:hover::before {
      transform: translate(5%, 20%);
      width: 110%;
      height: 110%;
    }
    .btn:hover::after {
      border-radius: 10px;
      transform: translate(0, 0);
      width: 100%;
      height: 100%;
    }
    .btn:active::after {
      transition: 0s;
      transform: translate(0, 5%);
    }
    .btn:hover {
      color: #fff;
    }
    /* Drag & Drop Upload Area CSS */
    .upload-area {
      margin-top: 1.25rem;
      border: none;
      background-image: url("data:image/svg+xml,%3csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3e%3crect width='100%25' height='100%25' fill='none' stroke='%23ccc' stroke-width='3' stroke-dasharray='6, 14' stroke-dashoffset='0' stroke-linecap='square'/%3e%3c/svg%3e");
      background-color: transparent;
      padding: 3rem;
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: background-image 0.3s;
      cursor: pointer;
    }
    .upload-area:hover, .upload-area:focus {
      background-image: url("data:image/svg+xml,%3csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3e%3crect width='100%25' height='100%25' fill='none' stroke='%232e44ff' stroke-width='3' stroke-dasharray='6, 14' stroke-dashoffset='0' stroke-linecap='square'/%3e%3c/svg%3e");
    }
    .upload-area-icon {
      display: block;
      width: 2.25rem;
      height: 2.25rem;
    }
    .upload-area-icon svg {
      max-height: 100%;
      max-width: 100%;
    }
    .upload-area-title {
      margin-top: 1rem;
      display: block;
      font-weight: 700;
      color: #D3D3D3;
    }
    .upload-area-description {
      display: block;
      color: #6a6b76;
    }
    .upload-area-description strong {
      color: #2e44ff;
      font-weight: 700;
    }
    /* Video Box Style for Find Missing Person Page */
    .video-box {
      border: 2px solid #03dac6;
      border-radius: 15px;
      overflow: hidden;
      box-shadow: 0 0 10px rgba(3, 218, 198, 0.7);
      margin: 20px 0;
    }
    /* Alert Form Style for Alert Others Page */
    .alert-form {
      max-width: 500px;
      margin: 20px auto;
      background: rgba(0, 0, 0, 0.6);
      padding: 25px;
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.8);
    }
    /* Sidebar Footer */
    .sidebar-footer {
      position: absolute;
      bottom: 20px;
      left: 20px;
      right: 20px;
      font-size: 10px;
      color: #aaa;
      text-align: center;
    }
    .sidebar-footer a {
      color: #aaa;
      margin: 0 4px;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <!-- Sidebar -->
  <aside class="sidenav">
    <div class="btn-grad"><b>Tensor Titans</b></div>
    <!-- New Home Tab -->
    <a class="nav-link" href="https://www.google.com" target="_blank">Home</a>
    <a class="nav-link" href="{{ url_for('index') }}">Enter Face of Missing Person</a>
    <a class="nav-link" href="{{ url_for('find_person') }}">Find Missing Person</a>
    <a class="nav-link" href="{{ url_for('alert_others') }}">Alert Others</a>
    <!-- Sidebar Footer with Icons and Contact Info -->
    <div class="sidebar-footer">
       <div>
         <a href="#"><i class="fas fa-cog"></i></a>
         <a href="#"><i class="fab fa-twitter"></i></a>
         <a href="#"><i class="fab fa-facebook"></i></a>
         <a href="#"><i class="fab fa-instagram"></i></a>
       </div>
       <div style="margin-top:5px;">Contact us: tensortitans2612@gmail.com</div>
    </div>
  </aside>
  <!-- Top Navbar -->
  <nav class="topnav">
    <ol class="breadcrumb">
      <li class="breadcrumb-item">Pages</li>
      <li class="breadcrumb-item active">{{ page_title|default("Dashboard") }}</li>
    </ol>
    <div>
      <!-- Logo at top right -->
      <a href="#"><img src="{{ url_for('static', filename='logo.jpg') }}" alt="Logo" style="height:60px;"></a>
    </div>
  </nav>
  <!-- Main Content -->
  <div class="main-content">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert alert-info" role="alert" style="background: #111111; border: 1px solid #333333;">
          {% for message in messages %}
            <p>{{ message }}</p>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>
  <!-- Bootstrap JS and dependencies -->
  <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js"></script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
  <!-- JavaScript to wire up the drag & drop upload areas -->
  <script>
    document.addEventListener("DOMContentLoaded", function() {
      function setupUploadArea(areaId, inputId) {
        var area = document.getElementById(areaId);
        var fileInput = document.getElementById(inputId);
        if (!area || !fileInput) return;
        area.addEventListener("click", function() {
          fileInput.click();
        });
        area.addEventListener("dragover", function(e) {
          e.preventDefault();
          e.stopPropagation();
          area.style.backgroundColor = "#f0f0f0";
        });
        area.addEventListener("dragleave", function(e) {
          e.preventDefault();
          e.stopPropagation();
          area.style.backgroundColor = "transparent";
        });
        area.addEventListener("drop", function(e) {
          e.preventDefault();
          e.stopPropagation();
          fileInput.files = e.dataTransfer.files;
        });
      }
      // Setup for the Enter Face page
      setupUploadArea("upload-area-enter", "image");
      // Setup for the Alert Others page (using different IDs)
      setupUploadArea("upload-area-alert", "alert-image");
    });
  </script>
  {% block extra_js %}{% endblock %}
</body>
</html>
'''

enter_face_html = '''
{% extends "base.html" %}
{% block content %}
<h1>Enter Face of Missing Person</h1>
<p>Upload an image of the missing person. The system will extract the face encoding for detection.</p>
<form action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data" class="narrow-field">
    <div class="form-group">
        <!-- Drag & Drop Upload Area for Enter Face page -->
        <label for="image">Upload Image</label>
        <div id="upload-area-enter" class="upload-area">
            <span class="upload-area-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
                <path fill="none" d="M0 0h24v24H0V0z"/>
                <path d="M19 9l-7-7-7 7h4v7h6V9h4z" fill="#2e44ff"/>
                </svg>
            </span>
            <span class="upload-area-title">Drag file(s) here to upload.</span>
            <span class="upload-area-description">Alternatively, click here to select a file</span>
        </div>
        <input type="file" id="image" name="image" accept="image/*" style="display:none;">
    </div>
    <button type="submit" class="btn">Upload and Save Face</button>
</form>
{% endblock %}
'''

find_person_html = '''
{% extends "base.html" %}
{% block content %}
<h1>Find Missing Person</h1>
<p>The live video feed below will search for the missing person. Please allow camera access.</p>
<div class="video-box mb-4">
    <img src="{{ url_for('video_feed') }}" style="width:100%;" alt="Live Video Feed" />
</div>
<p class="lead">If the missing person is detected, an email alert will be sent automatically.</p>
{% endblock %}
'''

alert_others_html = '''
{% extends "base.html" %}
{% block content %}
<h1>Alert Others</h1>
<p>Upload an image and provide details about the missing person to alert others and authorities.</p>
<form action="{{ url_for('alert_others') }}" method="post" enctype="multipart/form-data" class="narrow-field alert-form">
  <div class="form-group input-group">
    <label for="details">Basic Details</label>
    <input type="text" name="details" id="details" class="form-control" placeholder="Enter basic details">
  </div>
  <div class="form-group input-group">
    <label for="description">Short Description</label>
    <textarea name="description" id="description" class="form-control" rows="4" placeholder="Enter description about the missing person"></textarea>
  </div>
  <div class="form-group input-group">
    <label for="receiver_emails">Receiver Emails (comma-separated)</label>
    <input type="text" name="receiver_emails" id="receiver_emails" class="form-control" value="{{ default_receivers }}">
  </div>
  <div class="form-group">
    <label for="alert-image">Upload Image (optional)</label>
    <!-- Drag & Drop Upload Area with enhanced interactive styling -->
    <div id="upload-area-alert" class="upload-area">
      <span class="upload-area-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
          <path fill="none" d="M0 0h24v24H0V0z"/>
          <path d="M19 9l-7-7-7 7h4v7h6V9h4z" fill="#2e44ff"/>
        </svg>
      </span>
      <span class="upload-area-title">Drag file(s) here to upload.</span>
      <span class="upload-area-description">Alternatively, click here to select a file</span>
    </div>
    <input type="file" id="alert-image" name="image" accept="image/*" style="display:none;">
  </div>
  <button type="submit" class="btn red">Send Alert Email</button>
</form>
{% endblock %}
'''

# Load templates via DictLoader
app.jinja_loader = DictLoader({
    'base.html': base_html,
    'enter_face.html': enter_face_html,
    'find_person.html': find_person_html,
    'alert_others.html': alert_others_html,
})

# ==============================
# Video Streaming Generator with Face Detection & Email Alert
# ==============================
def gen_frames():
    global target_encoding, alert_sent
    frame_counter = 0
    while True:
        success, frame = camera.read()
        if not success:
            break
        frame_counter += 1
        # Process every other frame to reduce computational load
        if target_encoding is not None and (frame_counter % 2 == 0):
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                distance = face_recognition.face_distance([target_encoding], face_encoding)[0]
                threshold = 0.6
                if distance < threshold:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
                    cv2.putText(frame, "Missing Person Found", (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
                    if not alert_sent:
                        ret, buffer = cv2.imencode('.jpg', frame)
                        frame_bytes = buffer.tobytes()
                        threading.Thread(target=send_email, args=(DETECTION_EMAIL_SUBJECT,
                                                                  DETECTION_EMAIL_MESSAGE,
                                                                  DEFAULT_RECEIVERS,
                                                                  frame_bytes,
                                                                  "detection.jpg",
                                                                  "jpeg")).start()
                        alert_sent = True
                else:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0,0,255), 2)
                    cv2.putText(frame, "Unknown Person", (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# ==============================
# Flask Routes
# ==============================
@app.route('/')
def index():
    return render_template('enter_face.html', page_title="Enter Face of Missing Person")

@app.route('/upload', methods=['POST'])
def upload():
    global target_encoding
    if 'image' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('index'))
    file = request.files['image']
    if file.filename == '':
        flash('No file selected. Please try again.')
        return redirect(url_for('index'))
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        flash('Could not process the image. Please try again.')
        return redirect(url_for('index'))
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_img)
    if encodings:
        target_encoding = encodings[0]
        flash("Face encoding extracted and saved!")
        return redirect(url_for('find_person'))
    else:
        flash("No face found in the image. Please upload a clear image.")
        return redirect(url_for('index'))

@app.route('/find')
def find_person():
    global target_encoding
    if target_encoding is None:
        flash("Please upload a missing person's face first.")
        return redirect(url_for('index'))
    return render_template('find_person.html', page_title="Find Missing Person")

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/alert', methods=['GET', 'POST'])
def alert_others():
    if request.method == 'POST':
        details = request.form.get('details', '')
        description = request.form.get('description', '')
        receiver_emails = request.form.get('receiver_emails', '')
        receivers = [email.strip() for email in receiver_emails.split(",")] if receiver_emails else DEFAULT_RECEIVERS
        message = f"Missing Person Alert!\n\nDetails: {details}\n\nDescription: {description}"
        attachment_data = None
        attachment_filename = None
        attachment_subtype = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                attachment_data = file.read()
                attachment_filename = file.filename
                attachment_subtype = attachment_filename.split('.')[-1]
        success, result_msg = send_email("Missing Person Alert", message, receivers, attachment_data, attachment_filename, attachment_subtype)
        if success:
            flash("All the Users alerted !! Authorities Alerted !!")
        else:
            flash(f"Failed to send alert email: {result_msg}")
        return redirect(url_for('alert_others'))
    return render_template('alert_others.html', page_title="Alert Others", default_receivers=", ".join(DEFAULT_RECEIVERS))

# ==============================
# Run the Application
# ==============================
if __name__ == '__main__':
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        camera.release()
        sys.exit()
