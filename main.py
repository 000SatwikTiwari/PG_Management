# pg_owner.py
# Run: uvicorn temp2:app --reload

from fastapi import FastAPI, Path, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from datetime import date, datetime
from typing import Annotated
from pymongo import MongoClient

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

app = FastAPI()

# ================= DATABASE =================
client = MongoClient("mongodb+srv://db_sat:otXj03GNr05TcQHK@cluster0.iotuxte.mongodb.net/jobtracker?retryWrites=true&w=majority&appName=Cluster0")
db1 = client["pg_management"]
collection = db1["hisab_data"]

# ================= UI =================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<title>PG Management</title>
<style>
body { font-family: Arial; background:#ffffff; margin:0; }
header { background:#b30000; color:white; padding:20px; text-align:center; font-size:26px; }
.container { width:85%; margin:20px auto; }
.card { background:#ffe6e6; padding:20px; margin-bottom:20px; border-radius:10px; box-shadow:0 3px 6px rgba(0,0,0,0.1); }
input,button { width:100%; padding:10px; margin:5px 0; border-radius:5px; border:1px solid #b30000; }
button { background:#b30000; color:white; font-weight:bold; cursor:pointer; }
button:hover { background:#800000; }
h2 { color:#b30000; }
ul { background:white; padding:15px; border-radius:5px; }
.success { color:green; font-weight:bold; }
.error { color:red; font-weight:bold; }
</style>
</head>
<body>

<header>PG Management System-by Satwik</header>

<div class="container">

<div class="card">
<h2>Add Rent Record</h2>
<input id="name" placeholder="Name">
<input id="rent" type="number" placeholder="Rent Paid">
<input id="duration" type="number" placeholder="Duration (days)">
<input id="hisab_date" type="date">
<button onclick="addRent()">Add Record</button>
<div id="addMsg"></div>
</div>

<div class="card">
<h2>Get Person Data</h2>
<input id="searchName" placeholder="Enter Name">
<button onclick="getData()">Get Data</button>
<ul id="result"></ul>
</div>

<div class="card">
<h2>Delete Record</h2>
<input id="delName" placeholder="Name">
<input id="delDate" type="date">
<button onclick="deleteRecord()">Delete Record</button>
<div id="delMsg"></div>
</div>

<div class="card">
<h2>View All People</h2>
<button onclick="getPeople()">Show People</button>
<ul id="peopleResult"></ul>
</div>

<div class="card">
<h2>Generate Electricity Bill</h2>
<input id="eb_name" placeholder="Name">
<input id="rate" type="number" step="0.01" placeholder="Rate Per Unit (₹)">
<input id="last_reading" type="number" step="0.01" placeholder="Last Meter Reading">
<input id="current_reading" type="number" step="0.01" placeholder="Current Meter Reading">
<button onclick="generateBill()">Generate Bill PDF</button>
<div id="billMsg"></div>
</div>

</div>

<script>

async function addRent() {
    let name = document.getElementById("name").value;
    let rent = document.getElementById("rent").value;
    let duration = document.getElementById("duration").value;
    let date = document.getElementById("hisab_date").value;

    let url = `/hisab/${name}/${rent}/${duration}`;
    if(date) {
        url += `?hisab_date=${date}`;
    }

    let res = await fetch(url, {method:"POST"});
    let data = await res.json();

    document.getElementById("addMsg").innerHTML =
        "<span class='success'>" + data.message + "</span>";
}

async function getData() {
    let name = document.getElementById("searchName").value;
    let res = await fetch(`/data/${name}`);
    let resultDiv = document.getElementById("result");
    resultDiv.innerHTML = "";

    if(res.status === 404){
        resultDiv.innerHTML = "<li class='error'>No records found</li>";
        return;
    }

    let data = await res.json();

    data.records.forEach(r => {
        resultDiv.innerHTML += `
            <li>
             Paid ₹${r.paid_RS} <br>
             Duration: ${r.for_duration_days} days <br>
             Date: ${r.on_date}
            <hr>
            </li>
        `;
    });

    resultDiv.innerHTML += `<li><strong>Total Paid: ₹${data.total_paid}</strong></li>`;
}

async function deleteRecord() {
    let name = document.getElementById("delName").value;
    let date = document.getElementById("delDate").value;

    let res = await fetch(`/delete/${name}?hisab_date=${date}`, {method:"DELETE"});
    let data = await res.json();

    if(res.status === 404){
        document.getElementById("delMsg").innerHTML =
            "<span class='error'>" + data.detail + "</span>";
    } else {
        document.getElementById("delMsg").innerHTML =
            "<span class='success'>" + data.message + "</span>";
    }
}

async function getPeople() {
    let res = await fetch(`/people`);
    let data = await res.json();
    let peopleDiv = document.getElementById("peopleResult");
    peopleDiv.innerHTML = "";

    data.people.forEach(p => {
        peopleDiv.innerHTML += `<li> ${p}</li>`;
    });

    peopleDiv.innerHTML += `<li><strong>Total People: ${data.total_people}</strong></li>`;
}

async function generateBill() {
    let name = document.getElementById("eb_name").value;
    let rate = document.getElementById("rate").value;
    let last = document.getElementById("last_reading").value;
    let current = document.getElementById("current_reading").value;

    let url = `/electricity-bill?name=${name}&rate_per_unit=${rate}&last_reading=${last}&current_reading=${current}`;

    let res = await fetch(url);

    if(res.status === 400){
        let data = await res.json();
        document.getElementById("billMsg").innerHTML =
            "<span class='error'>" + data.detail + "</span>";
        return;
    }

    let blob = await res.blob();
    let link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = name + "_electricity_bill.pdf";
    link.click();

    document.getElementById("billMsg").innerHTML =
        "<span class='success'>Bill Generated & Downloaded Successfully</span>";
}

</script>

</body>
</html>
"""

# ================= ADD RENT =================
@app.post("/hisab/{name}/{rent_paid}/{duration}")
def save_data(
    name: str,
    rent_paid: Annotated[float, Path(gt=0)],
    duration: Annotated[int, Path(gt=0, lt=32)],
    hisab_date: date | None = None
):

    if not hisab_date:
        hisab_date = date.today()

    data = {
        "Name": name,
        "rent_paid": rent_paid,
        "duration": duration,
        "hisab_date": datetime.combine(hisab_date, datetime.min.time())
    }

    collection.insert_one(data)
    return {"message": "Added successfully"}

# ================= GET DATA =================
@app.get("/data/{name}")
def give_data(name: str):

    records = collection.find({
        "Name": {"$regex": f"^{name}$", "$options": "i"}
    })

    return_list = []
    total_paid = 0

    for x in records:
        total_paid += x["rent_paid"]
        return_list.append({
            "paid_RS": x["rent_paid"],
            "on_date": x["hisab_date"].strftime("%Y-%m-%d"),
            "for_duration_days": x["duration"]
        })

    if not return_list:
        raise HTTPException(status_code=404, detail="No records found")

    return {"records": return_list, "total_paid": total_paid}

# ================= DELETE =================
@app.delete("/delete/{name}")
def delete_data(name: str, hisab_date: date):

    result = collection.delete_one({
        "Name": {"$regex": f"^{name}$", "$options": "i"},
        "hisab_date": datetime.combine(hisab_date, datetime.min.time())
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found")

    return {"message": "Record deleted successfully"}

# ================= PEOPLE =================
@app.get("/people")
def get_unique_workers():
    people = collection.distinct("Name")
    return {"total_people": len(people), "people": people}

# ================= ELECTRICITY BILL =================
from io import BytesIO
from fastapi.responses import StreamingResponse

@app.get("/electricity-bill")
def generate_electricity_bill(
    name: str,
    rate_per_unit: float,
    last_reading: float,
    current_reading: float
):

    if current_reading < last_reading:
        raise HTTPException(
            status_code=400,
            detail="Current reading must be greater than last reading"
        )

    units_used = current_reading - last_reading
    total_bill = units_used * rate_per_unit

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>PG Electricity Bill</b>", styles["Title"]))
    elements.append(Spacer(1, 0.5 * inch))

    data = [
        ["Name", name],
        ["Rate Per Unit (₹)", rate_per_unit],
        ["Last Meter Reading", last_reading],
        ["Current Meter Reading", current_reading],
        ["Units Consumed", units_used],
        ["Total Bill (₹)", total_bill]
    ]

    table = Table(data, colWidths=[220, 220])
    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={name}_electricity_bill.pdf"
        }
    )

