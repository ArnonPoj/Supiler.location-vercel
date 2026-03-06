from flask import Blueprint, render_template, request

job_bp = Blueprint("job", __name__)

@job_bp.route("/create_job", methods=["GET","POST"])
def create_job():

    if request.method == "POST":
        customer = request.form["customer"]
        address = request.form["address"]
        phone = request.form["phone"]
        detail = request.form["detail"]
        pluscode = request.form["pluscode"]
        note = request.form["note"]

        # save database

        return "สร้างงานสำเร็จ"

    return render_template("create_job.html")
