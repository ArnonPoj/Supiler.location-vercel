from flask import Blueprint, render_template, request, redirect
import uuid

job_bp = Blueprint("job", __name__)

jobs = {}

@job_bp.route("/create_job", methods=["GET","POST"])
def create_job():

    # เปิดหน้า form
    if request.method == "GET":
        return render_template("create_job.html")

    # กดสร้างงาน
    if request.method == "POST":

        job_id = str(uuid.uuid4())[:8]

        jobs[job_id] = {
            "customer": request.form.get("customer"),
            "address": request.form.get("address"),
            "phone": request.form.get("phone"),
            "detail": request.form.get("detail"),
            "pluscode": request.form.get("pluscode"),
            "note": request.form.get("note")
        }

        link = f"/job/{job_id}"

        print("Job created:", job_id)
        print("Driver link:", link)

        return f"สร้างงานสำเร็จ<br>ลิงค์ส่งคนขับ: {link}"
