# NRIIT Results Portal 2.0
A Flask-based web application that provides a consolidated view of academic results for B.Tech students, now with enhanced capabilities and improved performance.

## Live Demo
The application is deployed and can be accessed at:
https://b-tech-result-scrapper-2-0.onrender.com/

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/ejjadaakhil-13/B.TECH_RESULT_SCRAPPER_2.0.git
   ```
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```
3. Install the required packages:
   ```
   pip install flask requests beautifulsoup4 
   ```

## Project Structure
```
nriit_results_app_v2/
├── app.py
└── templates/
    └── index.html
```
- `app.py`: Main application file with Flask routes and enhanced result processing logic
- `templates/index.html`: Responsive HTML template with Bootstrap styling for the user interface

## Usage
1. Start the application:
   ```
   python app.py
   ```
2. Open your web browser and navigate to http://127.0.0.1:5000/
3. Enter your roll number (format: 20KN1A0XXX) and click Search
4. View your consolidated academic results across all semesters
   
![Recording2025-04-26221815-ezgif com-video-to-gif-converter](https://github.com/user-attachments/assets/8c63e9ca-18bc-4bfb-b155-b80292177069)


## Key Features

### New in Version 2.0:
- **Remaining Supply Attempts**: Shows the number of remaining attempts for failed subjects
- **GPA Calculator**: Displays both CGPA (Cumulative) and SGPA (Semester) metrics
- **Multi-Regulation Support**: Compatible with results from any regulation and batch
- **Responsive Design**: Better mobile and desktop experience

### Core Features:
- Consolidated view of all semester results in one place
- Clean, intuitive interface with status indicators
- Subject-wise performance tracking
- Parallel fetching of results for optimized speed

## Notes
- The application runs on a free hosting service, so initial loading may take a few moments
- No student data is stored on the server; all processing happens in real-time
- Results are fetched directly from the official NRIIT result portal

## Requirements
- Python 3.6+
- Flask
- Requests
- BeautifulSoup4
- concurrent.futures
- Internet connection to fetch results from the NRIIT server

