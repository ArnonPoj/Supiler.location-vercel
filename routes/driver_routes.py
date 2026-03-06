from flask import Blueprint, render_template

driver_bp = Blueprint("driver", __name__)

@driver_bp.route("/driver/map")
def driver_map():
    return render_template("driver/driver_map.html")
