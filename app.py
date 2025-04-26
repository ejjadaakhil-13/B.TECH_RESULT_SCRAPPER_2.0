import csv
import io
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from flask import (Flask, jsonify, make_response, render_template, request,
                   send_file)

app = Flask(__name__)

def links_method(regulation):
    portal_link = "https://www.nriitexamcell.com/autonomous/results.php"
    regulation = regulation.upper()  # Convert to uppercase

    response = requests.get(portal_link)
    soup = BeautifulSoup(response.content, "html.parser")
    table_body = soup.find_all("tbody")[0]
    anchors = table_body.find_all("a")
    results_links = {}

    for anchor in anchors:
        text = anchor.text.strip()
        href = anchor.get("href").removeprefix("http://nriitexamcell.com").removeprefix("https://nriitexamcell.com").removesuffix(":")

        if regulation in text and href:
            match = re.search(r"(\d)-(\d)", href)
            if match:
                sem_key = f"{match.group(1)}_{match.group(2)}"
                full_url = f"https://www.nriitexamcell.com{href}"

                if sem_key not in results_links:
                    results_links[sem_key] = []
                results_links[sem_key].insert(0, full_url)

    return results_links

def get_student_info_and_subjects(url, roll_number):
    payload = {"roll": roll_number, "submit": "Get result"}
    session = requests.Session()
    try:
        response = session.post(url, data=payload, timeout=40)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract student name - improved extraction logic
        student_name = ""
        tables = soup.find_all("table", class_="tborder")
        
        if tables:
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        if "Name of the Student" in cells[0].text.strip():
                            student_name = cells[1].text.strip()
                            break
        
        # Extract subjects data
        tables = soup.find_all("table", class_="dtlsbdr")
        if not tables:
            return student_name, {}, []

        headers = [th.text.strip() for th in tables[-1].find_all("th")]
        try:
            indices = {
                "subject_code": headers.index("Subject Code"),  # Added subject code index
                "subject": headers.index("Subject Name"),
                "status": headers.index("Status"),
                "grade_point": headers.index("Grade Points"),
                "credits": headers.index("Credits"),
            }
        except ValueError:
            # If "Subject Code" column doesn't exist, we'll try to extract it from the subject name
            if "Subject Name" in headers:
                indices = {
                    "subject": headers.index("Subject Name"),
                    "status": headers.index("Status"),
                    "grade_point": headers.index("Grade Points"),
                    "credits": headers.index("Credits"),
                }
            else:
                return student_name, {}, []

        rows = tables[-1].find_all("tr")[0:]  
        subjects_status = {}
        grade_credits = []

        for row in rows:
            cols = row.find_all("td")
            if len(cols) > max(indices.values()):
                subject = cols[indices["subject"]].text.strip()
                status = cols[indices["status"]].text.strip()
                
                # Extract subject code if it exists as a separate column or extract from subject name
                if "subject_code" in indices:
                    subject_code = cols[indices["subject_code"]].text.strip()
                else:
                    # Try to extract code from subject name (usually at the beginning)
                    match = re.search(r'^([A-Z0-9]+)', subject)
                    subject_code = match.group(1) if match else subject
                
                try:
                    grade_point = float(cols[indices["grade_point"]].text.strip())
                    credits = float(cols[indices["credits"]].text.strip())
                except ValueError:
                    grade_point = 0.0
                    credits = 0.0

                # Use subject_code as the key instead of subject name
                subjects_status[subject_code] = {
                    "name": subject,  # Store the subject name for display
                    "status": status,
                    "grade_point": grade_point,
                    "credits": credits
                }
                # Store the grade point and credits for all subjects including failed ones
                grade_credits.append((grade_point, credits))

        return student_name, subjects_status, grade_credits
    except Exception as e:
        print(f"Error fetching from {url}: {e}")
        return "", {}, []
    
    

def compile_full_result(roll_number, regulation):
    results_links = links_method(regulation)
    final_result = {}
    total_weighted_gp = 0
    total_credits = 0
    student_name = ""
    total_failed = 0
    failed_subjects = []

    # First pass - just to get student name from any available URL
    for semester, links in results_links.items():
        for url in links:
            name, _, _ = get_student_info_and_subjects(url, roll_number)
            if name:
                student_name = name
                break
        if student_name:
            break

    # Second pass - get all the results
    for semester, links in results_links.items():
        sem_result = {}
        grade_credits = []

        for url in links:
            _, result, sem_gc = get_student_info_and_subjects(url, roll_number)
            
            # Update subjects with new data while preserving subject code as key
            for subject_code, details in result.items():
                sem_result[subject_code] = details
                
            grade_credits.extend(sem_gc)

        # Calculate SGPA including all subjects
        sem_gp_sum = sum(gp * cr for gp, cr in grade_credits)
        sem_cr_sum = sum(cr for _, cr in grade_credits)
        sgpa = round(sem_gp_sum / sem_cr_sum, 2) if sem_cr_sum > 0 else 0.0

        # Count failed subjects
        for subject_code, details in sem_result.items():
            if "pass" not in details["status"].lower():
                total_failed += 1
                failed_subjects.append(f"{details['name']} (Semester {semester.replace('_', '-')})")

        final_result[semester] = {
            "subjects": sem_result,
            "sgpa": sgpa
        }

        total_weighted_gp += sem_gp_sum
        total_credits += sem_cr_sum

    final_result["cgpa"] = round(total_weighted_gp / total_credits, 2) if total_credits > 0 else 0.0
    final_result["student_name"] = student_name
    final_result["total_failed"] = total_failed
    final_result["failed_subjects"] = failed_subjects
    return final_result

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    roll_number = None
    regulation = "NRIA20"  # Default regulation
    error = None
    
    if request.method == 'POST':
        roll_number = request.form.get('roll_number')
        regulation = request.form.get('regulation', 'NRIA20')
        
        if not roll_number:
            error = "Please enter a roll number"
        else:
            try:
                result = compile_full_result(roll_number, regulation)
                if not result or (len(result) <= 3 and "cgpa" in result):
                    error = "No results found for this roll number and regulation"
                    result = None
                else:
                    # Sort semesters by year and semester number
                    result["sorted_semesters"] = sorted(
                        [sem_key for sem_key in result.keys() 
                         if sem_key not in ["cgpa", "student_name", "total_failed", "failed_subjects", "sorted_semesters"]],
                        key=lambda x: (int(x.split('_')[0]), int(x.split('_')[1]))
                    )
            except Exception as e:
                error = f"Error retrieving results: {str(e)}"
                
    return render_template('index.html', result=result, roll_number=roll_number, 
                          regulation=regulation, error=error)

if __name__ == '__main__':
    app.run(debug=True)