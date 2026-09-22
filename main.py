from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import sqlite3
import hashlib
import json
import os
import io
import re

from datetime import datetime

from PIL import Image

import pytesseract

import fitz


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.dirname(
    BASE_DIR
)

DATABASE = os.path.join(
    BASE_DIR,
    "database.db"
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(

    title="Intelligent Land Record System",

    version="1.0.0",

    description=
    "BhoomiSetu Land Record Digitization and Validation API"

)


# =========================================================
# CORS
# =========================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://127.0.0.1:5500",

        "http://localhost:5500",

        "http://127.0.0.1:8000",

        "http://localhost:8000"

    ],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"]

)


# =========================================================
# DATABASE
# =========================================================

def get_db():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    return connection


def create_database():

    connection = get_db()


    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS land_records (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            owner_name TEXT NOT NULL,

            khasra_no TEXT NOT NULL,

            area_acres REAL NOT NULL,

            village TEXT NOT NULL,

            district TEXT NOT NULL,

            state TEXT DEFAULT '',

            file_name TEXT,

            file_hash TEXT,

            status TEXT NOT NULL,

            validation_errors TEXT,

            created_at TEXT NOT NULL

        )
        """
    )


    connection.commit()

    connection.close()


create_database()


# =========================================================
# OCR
# =========================================================

def run_ocr(image):

    try:

        return pytesseract.image_to_string(
            image,
            lang="eng",
            config="--psm 6"
        )

    except Exception as error:

        print(
            "OCR error:",
            error
        )

        return ""


# =========================================================
# EXTRACT TEXT FROM FILE
# =========================================================

def extract_text(
    file_bytes,
    filename
):

    extension = os.path.splitext(
        filename
    )[1].lower()


    text = ""


    # -----------------------------------------------------
    # IMAGE
    # -----------------------------------------------------

    if extension in [

        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff"

    ]:

        image = Image.open(
            io.BytesIO(file_bytes)
        )

        text = run_ocr(
            image
        )


    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    elif extension == ".pdf":

        pdf = fitz.open(
            stream=file_bytes,
            filetype="pdf"
        )


        for page in pdf:

            page_text = page.get_text()


            if page_text.strip():

                text += (
                    page_text +
                    "\n"
                )

            else:

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(
                        2,
                        2
                    ),
                    alpha=False
                )


                image = Image.frombytes(

                    "RGB",

                    (
                        pix.width,
                        pix.height
                    ),

                    pix.samples

                )


                text += (
                    run_ocr(image) +
                    "\n"
                )


        pdf.close()


    else:

        raise ValueError(
            "Unsupported file format"
        )


    return text


# =========================================================
# EXTRACT LAND FIELDS
# =========================================================

def extract_land_details(text):

    details = {

        "owner_name": "",

        "khasra_no": "",

        "area_acres": "",

        "village": "",

        "district": ""

    }


    def find(patterns):

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )


            if match:

                return match.group(1).strip()


        return ""


    details["owner_name"] = find([

        r"Owner\s*Name\s*[:\-]\s*([^\n]+)",

        r"Owner\s*[:\-]\s*([^\n]+)",

        r"Khatedar\s*[:\-]\s*([^\n]+)",

        r"Name\s*[:\-]\s*([^\n]+)"

    ])


    details["khasra_no"] = find([

        r"Khasra\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Za-z0-9\/\-]+)",

        r"Survey\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Za-z0-9\/\-]+)"

    ])


    details["area_acres"] = find([

        r"Total\s*Area\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",

        r"Area\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"

    ])


    details["village"] = find([

        r"Revenue\s*Village\s*[:\-]\s*([^\n]+)",

        r"Village\s*[:\-]\s*([^\n]+)"

    ])


    details["district"] = find([

        r"District\s*[:\-]\s*([^\n]+)"

    ])


    return details


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    dashboard = os.path.join(
        PROJECT_DIR,
        "index2.html"
    )


    if os.path.exists(
        dashboard
    ):

        return FileResponse(
            dashboard
        )


    return {

        "message":
        "BhoomiSetu API is running"

    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():

    return {

        "success": True,

        "status": "online",

        "message":
        "FastAPI backend is running"

    }


# =========================================================
# GET ALL RECORDS
# =========================================================

@app.get("/api/records")
def get_records():

    connection = get_db()


    rows = connection.execute(
        """
        SELECT *
        FROM land_records
        ORDER BY id DESC
        """
    ).fetchall()


    connection.close()


    records = []


    for row in rows:

        try:

            errors = json.loads(
                row["validation_errors"]
                or "[]"
            )

        except Exception:

            errors = []


        records.append({

            "id":
            row["id"],

            "owner_name":
            row["owner_name"],

            "khasra_no":
            row["khasra_no"],

            "area_acres":
            row["area_acres"],

            "village":
            row["village"],

            "district":
            row["district"],

            "state":
            row["state"],

            "file_name":
            row["file_name"],

            "file_hash":
            row["file_hash"],

            "hash":
            row["file_hash"],

            "sha256":
            row["file_hash"],

            "status":
            row["status"],

            "validation_status":
            row["status"],

            "validation_errors":
            errors,

            "created_at":
            row["created_at"]

        })


    return {

        "success": True,

        "count":
        len(records),

        "records":
        records

    }


# =========================================================
# DIGITIZE AND VALIDATE
# =========================================================

@app.post(
    "/api/digitize-and-validate"
)
async def digitize_and_validate(

    file: UploadFile = File(...),

    owner_name: str = Form(""),

    khasra_no: str = Form(""),

    area_acres: float = Form(0),

    village: str = Form(""),

    district: str = Form(""),

    state: str = Form("")

):

    errors = []


    # -----------------------------------------------------
    # FILE
    # -----------------------------------------------------

    filename = (
        file.filename
        or "document"
    )


    allowed = {

        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff"

    }


    extension = os.path.splitext(
        filename
    )[1].lower()


    if extension not in allowed:

        errors.append(
            "Unsupported file format."
        )


    content = await file.read()


    if not content:

        errors.append(
            "Uploaded document is empty."
        )


    # -----------------------------------------------------
    # OCR
    # -----------------------------------------------------

    extracted = {}


    if content and extension in allowed:

        try:

            text = extract_text(
                content,
                filename
            )


            extracted =extract_land_details(text)


        except Exception as error:

            print(
                "OCR warning:",
                error
            )

            extracted = {}


    # -----------------------------------------------------
    # MANUAL VALUE OR OCR VALUE
    # -----------------------------------------------------

    final_owner = (
        owner_name.strip()
        or extracted.get(
            "owner_name",
            ""
        )
    )


    final_khasra = (
        khasra_no.strip()
        or extracted.get(
            "khasra_no",
            ""
        )
    )


    final_village = (
        village.strip()
        or extracted.get(
            "village",
            ""
        )
    )


    final_district = (
        district.strip()
        or extracted.get(
            "district",
            ""
        )
    )


    final_area = area_acres


    if final_area <= 0:

        try:

            final_area = float(
                extracted.get(
                    "area_acres",
                    0
                )
            )

        except Exception:

            final_area = 0


    # -----------------------------------------------------
    # VALIDATION RULES
    # -----------------------------------------------------

    if not final_owner:

        errors.append(
            "Owner name is missing."
        )


    if not final_khasra:

        errors.append(
            "Khasra / Survey number is missing."
        )


    if final_area <= 0:

        errors.append(
            "Area must be greater than zero."
        )


    if not final_village:

        errors.append(
            "Revenue village is missing."
        )


    if not final_district:

        errors.append(
            "District is missing."
        )


    # -----------------------------------------------------
    # SHA-256
    # -----------------------------------------------------

    file_hash = hashlib.sha256(
        content
    ).hexdigest()


    # -----------------------------------------------------
    # DUPLICATE CHECK
    # -----------------------------------------------------

    connection = get_db()


    duplicate = connection.execute(

        """
        SELECT id
        FROM land_records
        WHERE file_hash = ?
        """,

        (file_hash,)

    ).fetchone()


    if duplicate:

        errors.append(
            "Duplicate document detected."
        )


    # -----------------------------------------------------
    # FINAL STATUS
    # -----------------------------------------------------

    if len(errors) == 0:

        status = "VALIDATED"

    else:

        status = "FLAGGED"


    # -----------------------------------------------------
    # SAVE UPLOADED DOCUMENT
    # -----------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )


    safe_filename = (
        timestamp +
        "_" +
        filename.replace(
            " ",
            "_"
        )
    )


    save_path = os.path.join(
        UPLOAD_DIR,
        safe_filename
    )


    with open(
        save_path,
        "wb"
    ) as output:

        output.write(content)


    # -----------------------------------------------------
    # SAVE DATABASE RECORD
    # -----------------------------------------------------

    cursor = connection.execute(

        """
        INSERT INTO land_records (

            owner_name,

            khasra_no,

            area_acres,

            village,

            district,

            state,

            file_name,

            file_hash,

            status,

            validation_errors,

            created_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """,

        (

            final_owner,

            final_khasra,

            final_area,

            final_village,

            final_district,

            state.strip(),

            filename,

            file_hash,

            status,

            json.dumps(errors),

            datetime.now().isoformat()

        )

    )


    connection.commit()


    record_id =cursor.lastrowid


    connection.close()


    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {

        "success":
        status == "VALIDATED",

        "status":
        status,

        "validation_status":
        status,

        "record_id":
        record_id,

        "owner_name":
        final_owner,

        "khasra_no":
        final_khasra,

        "area_acres":
        final_area,

        "village":
        final_village,

        "district":
        final_district,

        "state":
        state,

        "file_name":
        filename,

        "hash":
        file_hash,

        "sha256":
        file_hash,

        "validation_errors":
        errors

    }


# =========================================================
# OCR ENDPOINT
# =========================================================

@app.post("/api/ocr")
async def ocr_api(
    file: UploadFile = File(...)
):

    filename = (
        file.filename
        or "document"
    )


    content = await file.read()


    if not content:

        raise HTTPException(

            status_code=400,

            detail=
            "Uploaded file is empty."

        )


    try:

        text = extract_text(
            content,
            filename
        )


        details = extract_land_detail(text)



        return {

            "success": True,

            "filename": filename,

            "text": text,

            "extracted": details

        }


    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=
            f"OCR failed: {error}"

        )


# =========================================================
# GET SINGLE RECORD
# =========================================================

@app.get(
    "/api/records/{record_id}"
)
def get_record(
    record_id: int
):

    connection = get_db()


    row = connection.execute(

        """
        SELECT *
        FROM land_records
        WHERE id = ?
        """,

        (record_id,)

    ).fetchone()


    connection.close()


    if not row:

        raise HTTPException(

            status_code=404,

            detail=
            "Land record not found"

        )


    try:

        errors = json.loads(
            row["validation_errors"]
            or "[]"
        )

    except Exception:

        errors = []


    return {

        "id":
        row["id"],

        "owner_name":
        row["owner_name"],

        "khasra_no":
        row["khasra_no"],

        "area_acres":
        row["area_acres"],

        "village":
        row["village"],

        "district":
        row["district"],

        "state":
        row["state"],

        "file_name":
        row["file_name"],

        "hash":
        row["file_hash"],

        "sha256":
        row["file_hash"],

        "status":
        row["status"],

        "validation_errors":
        errors,

        "created_at":
        row["created_at"]

    }


# =========================================================
# DELETE RECORD
# =========================================================

@app.delete(
    "/api/records/{record_id}"
)
def delete_record(
    record_id: int
):

    connection = get_db()


    record = connection.execute(

        """
        SELECT *
        FROM land_records
        WHERE id = ?
        """,

        (record_id,)

    ).fetchone()


    if not record:

        connection.close()

        raise HTTPException(

            status_code=404,

            detail="Record not found"

        )


    connection.execute(

        """
        DELETE FROM land_records
        WHERE id = ?
        """,

        (record_id,)

    )


    connection.commit()

    connection.close()


    return {

        "success": True,

        "message":
        "Land record deleted successfully"

    }