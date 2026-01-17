let AREA_MAP = {};              // จังหวัด → อำเภอ[]
let PROVINCE_CODE_TO_NAME = {}; // provinceCode → provinceNameTh

async function loadAreaData() {
  const [provRes, distRes] = await Promise.all([
    fetch("/static/thai_province.json"),
    fetch("/static/thai_district.json")
  ]);

  const provinces = await provRes.json();
  const districts = await distRes.json();

  provinces.forEach(p => {
    PROVINCE_CODE_TO_NAME[p.provinceCode] = p.provinceNameTh;
    AREA_MAP[p.provinceNameTh] = [];
  });

  districts.forEach(d => {
    const provinceName = PROVINCE_CODE_TO_NAME[d.provinceCode];
    if (!provinceName) return;
    AREA_MAP[provinceName].push(d.districtNameTh);
  });

  initProvinceSearch();
}

loadAreaData();
