from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
import psycopg2
import os
import re
from openlocationcode import openlocationcode as olc
import csv
from io import StringIO
import pandas as pd

app = Flask(__name__)

DATABASE_URL = "postgresql://neondb_owner:npg_Rfi9yh6gpFTC@ep-delicate-flower-a1m8x768-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL ยังไม่ถูกตั้งใน environment variable")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS markers (
            id SERIAL PRIMARY KEY,
            lat DOUBLE PRECISION NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            title TEXT NOT NULL,
            olc TEXT,
            address TEXT,
            detail TEXT,
            tag TEXT  -- เพิ่มคอลัมน์ tag
        )
    ''')
    conn.commit()
    conn.close()

def get_all_markers():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, lat, lon, title, olc, address, detail, tag FROM markers")  # เพิ่ม tag
    rows = c.fetchall()
    conn.close()
    return rows

def get_marker_by_id(id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, lat, lon, title, olc, address, detail, tag FROM markers WHERE id = %s", (id,))  # เพิ่ม tag
    row = c.fetchone()
    conn.close()
    return row

def add_marker(lat, lon, title, olc_code=None, address=None, detail=None, tag=None):  # เพิ่ม tag
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO markers (lat, lon, title, olc, address, detail, tag)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (lat, lon, title, olc_code, address, detail, tag))  # เพิ่ม tag
    conn.commit()
    conn.close()


def update_marker(id, lat, lon, title, olc_code=None, address=None, detail=None, tag=None):  # เพิ่ม tag
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE markers
        SET lat=%s, lon=%s, title=%s, olc=%s, address=%s, detail=%s, tag=%s
        WHERE id=%s
    """, (lat, lon, title, olc_code, address, detail, tag, id))  # เพิ่ม tag
    conn.commit()
    conn.close()

def delete_marker(id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM markers WHERE id = %s", (id,))
    conn.commit()
    conn.close()

province_refs = {
    "กรุงเทพมหานคร": (13.7563, 100.5018),
    "เชียงใหม่": (18.7883, 98.9853),
    "สงขลา": (7.2000, 100.5954),
    "ขอนแก่น": (16.4322, 102.8236),
    "ชลบุรี": (13.3611, 100.9847),
    "นครราชสีมา": (14.9799, 102.0977),
    "พิษณุโลก": (16.8211, 100.2659),
    "นราธิวาส": (6.4264, 101.8231),
    "สุราษฎร์ธานี": (9.1401, 99.3337),
    "ยะลา": (6.5412, 101.2802),
    "นนทบุรี": (13.8625, 100.5144),
    "กระบี่": (8.0863, 98.9063),
    "กาญจนบุรี": (14.0206, 99.5377),
    "กาฬสินธุ์": (16.4379, 103.5055),
    "กำแพงเพชร": (16.4669, 99.5257),
    "จันทบุรี": (12.6111, 102.1033),
    "ฉะเชิงเทรา": (13.6932, 101.0401),
    "ชัยนาท": (15.1857, 100.1225),
    "ชัยภูมิ": (15.8066, 102.0500),
    "ชุมพร": (10.4893, 99.1787),
    "เชียงราย": (19.9072, 99.8325),
    "ตรัง": (7.5670, 99.6111),
    "ตราด": (12.2429, 102.5150),
    "ตาก": (16.8694, 98.4300),
    "นครนายก": (14.2035, 101.2136),
    "นครปฐม": (13.8170, 100.0583),
    "นครพนม": (17.4079, 104.7791),
    "นครศรีธรรมราช": (8.4311, 99.9631),
    "นครสวรรค์": (15.7053, 100.1265),
    "น่าน": (18.7829, 100.7761),
    "บึงกาฬ": (18.3572, 103.6426),
    "บุรีรัมย์": (14.9939, 103.1002),
    "ปทุมธานี": (14.0206, 100.5250),
    "ประจวบคีรีขันธ์": (11.8068, 99.7756),
    "ปราจีนบุรี": (14.0403, 101.3939),
    "ปัตตานี": (6.8695, 101.2504),
    "พระนครศรีอยุธยา": (14.3518, 100.5681),
    "พะเยา": (19.1622, 99.8860),
    "พังงา": (8.4500, 98.5167),
    "พัทลุง": (7.6172, 100.0728),
    "พิจิตร": (16.4282, 100.3543),
    "เพชรบุรี": (13.1087, 99.9367),
    "เพชรบูรณ์": (16.4216, 101.1486),
    "แพร่": (18.1400, 100.1413),
    "ภูเก็ต": (7.8804, 98.3923),
    "มหาสารคาม": (16.1742, 103.2920),
    "มุกดาหาร": (16.5342, 104.7266),
    "แม่ฮ่องสอน": (18.2774, 97.9670),
    "ยโสธร": (15.8079, 104.1439),
    "ร้อยเอ็ด": (16.0571, 103.6504),
    "ระนอง": (9.9647, 98.6362),
    "ระยอง": (12.6818, 101.2781),
    "ราชบุรี": (13.5367, 99.8131),
    "ลพบุรี": (14.8056, 100.6534),
    "ลำปาง": (18.2881, 99.4799),
    "ลำพูน": (18.5708, 99.0283),
    "เลย": (17.4850, 101.7249),
    "ศรีสะเกษ": (15.1130, 104.3427),
    "สกลนคร": (17.1682, 104.1467),
    "สตูล": (6.6231, 100.0671),
    "สมุทรปราการ": (13.5995, 100.5990),
    "สมุทรสงคราม": (13.4069, 100.0007),
    "สมุทรสาคร": (13.5360, 100.2675),
    "สระแก้ว": (13.8752, 102.0837),
    "สระบุรี": (14.5197, 100.9145),
    "สิงห์บุรี": (14.8883, 100.3973),
    "สุโขทัย": (17.0131, 99.8233),
    "สุพรรณบุรี": (14.4823, 100.1163),
    "สุรินทร์": (14.8819, 103.4935),
    "หนองคาย": (17.8789, 102.7631),
    "หนองบัวลำภู": (17.3940, 102.4207),
    "อ่างทอง": (14.5833, 100.4500),
    "อำนาจเจริญ": (15.8153, 104.5670),
    "อุดรธานี": (17.4156, 102.7855),
    "อุตรดิตถ์": (17.6125, 100.0940),
    "อุทัยธานี": (15.3833, 100.1167),
    "อุบลราชธานี": (15.2449, 104.8484),
    "Bangkok": (13.7563, 100.5018),
    "Chiang Mai": (18.7883, 98.9853),
    "Songkhla": (7.2000, 100.5954),
    "Khon Kaen": (16.4322, 102.8236),
    "Chonburi": (13.3611, 100.9847),
    "Chon Buri": (13.3611, 100.9847),
    "Nakhon Ratchasima": (14.9799, 102.0977),
    "Phitsanulok": (16.8211, 100.2659),
    "Narathiwat": (6.4264, 101.8231),
    "Surat Thani": (9.1401, 99.3337),
    "Yala": (6.5412, 101.2802),
    "Nonthaburi": (13.8625, 100.5144),
    "Krabi": (8.0863, 98.9063),
    "Kanchanaburi": (14.0206, 99.5377),
    "Kalasin": (16.4379, 103.5055),
    "Kamphaeng Phet": (16.4669, 99.5257),
    "Chanthaburi": (12.6111, 102.1033),
    "Chachoengsao": (13.6932, 101.0401),
    "Chai Nat": (15.1857, 100.1225),
    "Chaiyaphum": (15.8066, 102.0500),
    "Chumphon": (10.4893, 99.1787),
    "Chiang Rai": (19.9072, 99.8325),
    "Trang": (7.5670, 99.6111),
    "Trat": (12.2429, 102.5150),
    "Tak": (16.8694, 98.4300),
    "Nakhon Nayok": (14.2035, 101.2136),
    "Nakhon Pathom": (13.8170, 100.0583),
    "Nakhon Phanom": (17.4079, 104.7791),
    "Nakhon Si Thammarat": (8.4311, 99.9631),
    "Nakhon Sawan": (15.7053, 100.1265),
    "Nan": (18.7829, 100.7761),
    "Bueng Kan": (18.3572, 103.6426),
    "Buri Ram": (14.9939, 103.1002),
    "Pathum Thani": (14.0206, 100.5250),
    "Prachuap Khiri Khan": (11.8068, 99.7756),
    "Prachin Buri": (14.0403, 101.3939),
    "Pattani": (6.8695, 101.2504),
    "Phra Nakhon Si Ayutthaya": (14.3518, 100.5681),
    "Phayao": (19.1622, 99.8860),
    "Phang Nga": (8.4500, 98.5167),
    "Phatthalung": (7.6172, 100.0728),
    "Phichit": (16.4282, 100.3543),
    "Phetchaburi": (13.1087, 99.9367),
    "Phetchabun": (16.4216, 101.1486),
    "Phrae": (18.1400, 100.1413),
    "Phuket": (7.8804, 98.3923),
    "Maha Sarakham": (16.1742, 103.2920),
    "Mukdahan": (16.5342, 104.7266),
    "Mae Hong Son": (18.2774, 97.9670),
    "Yasothon": (15.8079, 104.1439),
    "Roi Et": (16.0571, 103.6504),
    "Ranong": (9.9647, 98.6362),
    "Rayong": (12.6818, 101.2781),
    "Ratchaburi": (13.5367, 99.8131),
    "Lopburi": (14.8056, 100.6534),
    "Lampang": (18.2881, 99.4799),
    "Lamphun": (18.5708, 99.0283),
    "Loei": (17.4850, 101.7249),
    "Si Sa Ket": (15.1130, 104.3427),
    "Sakon Nakhon": (17.1682, 104.1467),
    "Satun": (6.6231, 100.0671),
    "Samut Prakan": (13.5995, 100.5990),
    "Samut Songkhram": (13.4069, 100.0007),
    "Samut Sakhon": (13.5360, 100.2675),
    "Sa Kaeo": (13.8752, 102.0837),
    "Saraburi": (14.5197, 100.9145),
    "Sing Buri": (14.8883, 100.3973),
    "Sukhothai": (17.0131, 99.8233),
    "Suphan Buri": (14.4823, 100.1163),
    "Surin": (14.8819, 103.4935),
    "Nong Khai": (17.8789, 102.7631),
    "Nong Bua Lamphu": (17.3940, 102.4207),
    "Ang Thong": (14.5833, 100.4500),
    "Amnat Charoen": (15.8153, 104.5670),
    "Udon Thani": (17.4156, 102.7855),
    "Uttaradit": (17.6125, 100.0940),
    "Uthai Thani": (15.3833, 100.1167),
    "Ubon Ratchathani": (15.2449, 104.8484)
}

def extract_plus_code(text):
    match = re.search(r'[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}', text.upper())
    if match:
        return match.group(0)
    return text.strip()

def detect_province_from_text(text):
    for p in province_refs:
        if p in text:
            return p
    return None

def decode_olc(code, province=None):
    plus_code = code.strip()
    ref_lat, ref_lon = 15.0, 100.0

    if province and province in province_refs:
        ref_lat, ref_lon = province_refs[province]

    if not olc.isFull(plus_code):
        recovered = olc.recoverNearest(plus_code, ref_lat, ref_lon)
        decoded = olc.decode(recovered)
    else:
        decoded = olc.decode(plus_code)

    return decoded.latitudeCenter, decoded.longitudeCenter

@app.route('/')
def index():
    return render_template('map_leaflet.html')

@app.route('/markers')
def markers_api():
    markers = get_all_markers()
    return jsonify([
        {
            'id': m[0], 'lat': m[1], 'lon': m[2],
            'title': m[3], 'olc': m[4], 'address': m[5], 'detail': m[6], 'tag': m[7]  # เพิ่ม tag
        }
        for m in markers
    ])

@app.route('/decode_olc_temp', methods=['POST'])
def decode_olc_temp():
    data = request.json or {}
    olc_code_raw = (data.get("olc") or "").strip()
    province = data.get("province", "").strip() or "Bangkok"

    if not olc_code_raw:
        return jsonify({"error": "กรุณาส่งค่า OLC"}), 400

    try:
        # ดึงเฉพาะ Plus Code ตัวแรกจากข้อความ (รองรับข้อความต่อท้าย เช่น "JGWG+3F Lat Luang,...")
        m = re.search(r'([23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3})', olc_code_raw.upper())
        if m:
            olc_code = m.group(1)
        else:
            # fallback: ใช้คำแรก
            olc_code = olc_code_raw.split()[0]

        # เลือก reference point (province_refs เก็บเป็น tuple (lat, lon))
        if province in province_refs:
            ref_lat, ref_lng = province_refs[province]
        else:
            # ถ้าไม่รู้จังหวัด ให้ใช้ Bangkok เป็น default
            ref_lat, ref_lng = province_refs.get("Bangkok", (13.7563, 100.5018))

        # ถ้า short code ให้ recoverNearest ก่อน
        if not olc.isFull(olc_code):
            recovered = olc.recoverNearest(olc_code, ref_lat, ref_lng)
            decoded = olc.decode(recovered)
        else:
            decoded = olc.decode(olc_code)

        return jsonify({
            "lat": decoded.latitudeCenter,
            "lng": decoded.longitudeCenter
        }), 200

    except Exception as e:
        return jsonify({"error": f"ไม่สามารถถอดรหัส OLC: {str(e)}"}), 400


@app.route('/add_marker', methods=['POST'])
def add_marker_api():
    data = request.get_json()
    title = data.get('title')
    olc_code_raw = data.get('olc', '').strip() or None
    address = data.get('address', '').strip() or None
    detail = data.get('detail', '').strip() or None
    tag = data.get('tag', '').strip() or None  # รับ tag
    lat = data.get('lat')
    lon = data.get('lon')

    olc_code = extract_plus_code(olc_code_raw) if olc_code_raw else None
    province = data.get('province', '').strip() or None
    if not province and olc_code_raw:
        province = detect_province_from_text(olc_code_raw)

    if not title:
        return {"error": "กรุณากรอกชื่อสถานที่"}, 400

    if lat is not None and lon is not None:
        try:
            lat = float(lat)
            lon = float(lon)
        except:
            return {"error": "พิกัดไม่ถูกต้อง"}, 400
    elif olc_code:
        try:
            lat, lon = decode_olc(olc_code, province)
        except Exception as e:
            return {"error": f"OLC ไม่ถูกต้อง: {str(e)}"}, 400
    else:
        return {"error": "กรุณาระบุพิกัดหรือ OLC"}, 400

    add_marker(lat, lon, title, olc_code_raw, address, detail, tag)  # ส่ง tag

    return {"message": "เพิ่มหมุดสำเร็จ"}, 200

@app.route('/edit_marker/<int:id>', methods=['PUT'])
def edit_marker_api(id):
    data = request.get_json()
    title = data.get('title', '').strip()
    olc_code_raw = data.get('olc', '').strip() or None
    address = data.get('address', '').strip() or None
    detail = data.get('detail', '').strip() or None
    tag = data.get('tag', '').strip() or None  # รับ tag

    if not title:
        return {"error": "กรุณาระบุชื่อ"}, 400

    olc_code = extract_plus_code(olc_code_raw) if olc_code_raw else None
    province = detect_province_from_text(olc_code_raw) if olc_code_raw else None

    try:
        if olc_code:
            lat, lon = decode_olc(olc_code, province)
        else:
            m = get_marker_by_id(id)
            if not m:
                return {"error": "ไม่พบหมุด"}, 404
            lat, lon = m[1], m[2]
    except Exception as e:
        return {"error": f"OLC ไม่ถูกต้อง: {str(e)}"}, 400

    update_marker(id, lat, lon, title, olc_code_raw, address, detail, tag)  # ส่ง tag
    return {"message": "แก้ไขหมุดสำเร็จ"}, 200

@app.route('/delete_marker/<int:id>', methods=['DELETE'])
def delete_marker_api(id):
    try:
        delete_marker(id)
        return jsonify({"message": "ลบหมุดสำเร็จ"}), 200
    except Exception as e:
        return jsonify({"error": f"ลบไม่สำเร็จ: {str(e)}"}), 500

@app.route('/export')
def export_markers():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT id, lat, lon, title, olc, address, detail, tag FROM markers")
        rows = cur.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    # เขียน BOM ที่หัวไฟล์เพื่อให้ Excel แสดงภาษาไทยได้ถูกต้อง
    output.write('\ufeff')
    writer.writerow(['id', 'lat', 'lon', 'title', 'olc', 'address', 'detail', 'tag'])
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={"Content-Disposition": "attachment;filename=markers_export.csv"}
    )

def add_pickup_personal(driver_name, phone=None, note=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO transport_pickup_personal (driver_name, phone, note)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (driver_name, phone, note))
    new_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return new_id

def get_all_pickup_personal():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, driver_name, phone, note
        FROM transport_pickup_personal
        ORDER BY driver_name
    """)
    rows = c.fetchall()
    conn.close()
    return rows
    
@app.route('/pickup_personal', methods=['POST'])
def add_pickup_personal_api():
    data = request.get_json() or {}

    driver_name = data.get('driver_name', '').strip()
    phone = data.get('phone', '').strip() or None
    note = data.get('note', '').strip() or None

    if not driver_name:
        return jsonify({'error': 'กรุณาระบุชื่อคนขับ'}), 400

    new_id = add_pickup_personal(driver_name, phone, note)

    return jsonify({
        'message': 'เพิ่มรถกระบะส่วนบุคคลสำเร็จ',
        'id': new_id
    }), 200
    
@app.route('/pickup_personal', methods=['GET'])
def get_pickup_personal_api():
    rows = get_all_pickup_personal()
    return jsonify([
        {
            'id': r[0],
            'driver_name': r[1],
            'phone': r[2],
            'note': r[3]
        }
        for r in rows
    ])

@app.route('/save_transport_personal', methods=['POST'])
def save_transport_personal():
    data = request.get_json() or {}

    owner_name = data.get("owner_name")
    phone = data.get("phone")
    line = data.get("line")
    vehicle_type = data.get("vehicle_type")
    capacity_ton = data.get("capacity_ton")
    license_plate = data.get("license_plate")
    areas = data.get("areas", [])

    if not owner_name or not phone:
        return jsonify({"error": "ข้อมูลไม่ครบ"}), 400

    conn = get_conn()
    cur = conn.cursor()

    # 1️⃣ insert หลัก
    cur.execute("""
        INSERT INTO personal_transport
        (owner_name, phone, line, vehicle_type, capacity_ton, license_plate)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        owner_name, phone, line,
        vehicle_type, capacity_ton, license_plate
    ))

    transport_id = cur.fetchone()[0]

    # 2️⃣ insert areas
    for a in areas:
        cur.execute("""
            INSERT INTO personal_transport_area
            (transport_id, province, district, subdistrict)
            VALUES (%s,%s,%s,%s)
        """, (
            transport_id,
            a.get("province"),
            a.get("district"),
            a.get("subdistrict")
        ))

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "id": transport_id})

@app.route('/import', methods=['POST'])
def import_markers():
    if 'file' not in request.files:
        return jsonify({'error': 'ไม่พบไฟล์'}), 400
    
    file = request.files['file']
    filename = secure_filename(file.filename)

    if not filename.endswith('.csv'):
        return jsonify({'error': 'รองรับเฉพาะไฟล์ CSV เท่านั้น'}), 400

    try:
        # ใช้ pandas อ่านไฟล์ CSV
        df = pd.read_csv(file)

        # ตรวจสอบว่ามีคอลัมน์ครบ
        expected_cols = {'id', 'lat', 'lon', 'title', 'olc', 'address', 'detail', 'tag'}
        if not expected_cols.issubset(df.columns):
            return jsonify({'error': 'รูปแบบไฟล์ไม่ถูกต้อง'}), 400

        conn = get_conn()
        cur = conn.cursor()

        # ลบข้อมูลเก่าออกก่อน ถ้าต้องการ merge ให้เปลี่ยน logic ตรงนี้
        cur.execute("DELETE FROM markers")

        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO markers (lat, lon, title, olc, address, detail, tag)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                float(row['lat']), float(row['lon']), row['title'],
                row['olc'], row['address'], row['detail'], row['tag']
            ))



        conn.commit()
        conn.close()

        return jsonify({'message': 'นำเข้าข้อมูลสำเร็จ'}), 200

    except Exception as e:
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

if __name__ == '__main__':
    init_db()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=True
    )
