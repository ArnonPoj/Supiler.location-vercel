let AREA_MAP = {};              // จังหวัด → อำเภอ[]
let PROVINCE_CODE_TO_NAME = {}; // code → ชื่อจังหวัด

async function loadAreaData() {
  const [provRes, distRes] = await Promise.all([
    fetch("/static/thai_province.json"),
    fetch("/static/thai_district.json")
  ]);

  const provinces = await provRes.json();
  const districts = await distRes.json();

  // 1) สร้าง map provinceCode → provinceNameTh
  provinces.forEach(p => {
    PROVINCE_CODE_TO_NAME[p.provinceCode] = p.provinceNameTh;
    AREA_MAP[p.provinceNameTh] = []; // เตรียม key ไว้ก่อน
  });

  // 2) ใส่อำเภอลงจังหวัด
  districts.forEach(d => {
    const provinceName = PROVINCE_CODE_TO_NAME[d.provinceCode];
    if (!provinceName) return;

    AREA_MAP[provinceName].push(d.districtNameTh);
  });

  console.log("AREA_MAP READY", AREA_MAP);

  initProvinceSearch(); // เรียก UI ต่อจากตรงนี้
}

loadAreaData();
