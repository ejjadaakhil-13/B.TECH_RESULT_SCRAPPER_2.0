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
        response = session.post(url, data=payload )
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
                "subject": headers.index("Subject Name"),
                "status": headers.index("Status"),
                "grade_point": headers.index("Grade Points"),
                "credits": headers.index("Credits"),
            }
        except ValueError:
            return student_name, {}, []

        rows = tables[-1].find_all("tr")[0:]  
        subjects_status = {}
        grade_credits = []

        for row in rows:
            cols = row.find_all("td")
            if len(cols) > max(indices.values()):
                subject = cols[indices["subject"]].text.strip()
                status = cols[indices["status"]].text.strip()
                try:
                    grade_point = float(cols[indices["grade_point"]].text.strip())
                    credits = float(cols[indices["credits"]].text.strip())
                except ValueError:
                    grade_point = 0.0
                    credits = 0.0

                subjects_status[subject] = {
                    "status": status,
                    "grade_point": grade_point,
                    "credits": credits
                }
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
            sem_result.update(result)
            grade_credits.extend(sem_gc)

        # Count failed subjects - FIX: Case-insensitive comparison
        for subject, details in sem_result.items():
            # Check if status contains "PASSED" or "passed" in any case
            if "pass" not in details["status"].lower():
                total_failed += 1
                failed_subjects.append(f"{subject} (Semester {semester.replace('_', '-')})")

        sem_gp_sum = sum(gp * cr for gp, cr in grade_credits)
        sem_cr_sum = sum(cr for _, cr in grade_credits)
        sgpa = round(sem_gp_sum / sem_cr_sum, 2) if sem_cr_sum > 0 else 0.0

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
            except Exception as e:
                error = f"Error retrieving results: {str(e)}"
                
    return render_template('index.html', result=result, roll_number=roll_number, 
                          regulation=regulation, error=error)

if __name__ == '__main__':
    app.run(debug=True)
