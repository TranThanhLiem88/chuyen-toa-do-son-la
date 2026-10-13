import streamlit as st
import pandas as pd
import pyproj
from io import BytesIO

# --- DỮ LIỆU KINH TUYẾN TRỤC 63 TỈNH THÀNH ---
PROVINCES_KTT = {
    "Sơn La": 104.00, "Lai Châu": 103.00, "Điện Biên": 103.00, "Hà Nội": 105.00, "An Giang": 104.45, 
    "Bà Rịa - Vũng Tàu": 105.45, "Bạc Liêu": 105.00, "Bắc Kạn": 106.15, "Bắc Giang": 107.00, "Bắc Ninh": 105.30, 
    "Bến Tre": 105.45, "Bình Dương": 105.45, "Bình Định": 108.15, "Bình Phước": 106.15, "Bình Thuận": 108.30, 
    "Cà Mau": 104.30, "Cao Bằng": 106.15, "Cần Thơ": 105.00, "Đà Nẵng": 107.45, "Đắk Lắk": 108.30, 
    "Đắk Nông": 108.30, "Đồng Nai": 107.45, "Đồng Tháp": 105.00, "Gia Lai": 108.30, "Hà Giang": 105.30, 
    "Hà Nam": 105.00, "Hà Tĩnh": 105.30, "Hải Dương": 105.30, "Hải Phòng": 105.45, "Hậu Giang": 105.00, 
    "Hòa Bình": 105.00, "Hưng Yên": 105.30, "Khánh Hòa": 108.15, "Kiên Giang": 104.30, "Kon Tum": 108.15, 
    "Lạng Sơn": 107.15, "Lào Cai": 104.45, "Lâm Đồng": 107.45, "Long An": 105.45, "Nam Định": 105.30, 
    "Nghệ An": 104.45, "Ninh Bình": 105.00, "Ninh Thuận": 108.15, "Phú Thọ": 104.45, "Phú Yên": 108.30, 
    "Quảng Bình": 106.00, "Quảng Nam": 107.45, "Quảng Ngãi": 108.00, "Quảng Ninh": 107.45, "Quảng Trị": 106.15, 
    "Sóc Trăng": 105.30, "Tây Ninh": 105.45, "Thái Bình": 105.30, "Thái Nguyên": 105.45, "Thanh Hóa": 105.00, 
    "Thừa Thiên Huế": 107.00, "Tiền Giang": 105.45, "Trà Vinh": 105.30, "Tuyên Quang": 105.00, "Vĩnh Long": 105.30, 
    "Vĩnh Phúc": 105.00, "Yên Bái": 104.45, "TP.HCM": 105.45
}

# Đưa Sơn La lên đầu danh sách để làm mặc định
province_names = list(PROVINCES_KTT.keys())
province_names.insert(0, province_names.pop(province_names.index("Sơn La")))

st.set_page_config(page_title="Chuyển tọa độ VN2000 ↔ WGS84", layout="centered")

# --- HÀM TẠO BỘ CHUYỂN ĐỔI ---
@st.cache_resource
def get_transformer(ktt, direction):
    # Chuỗi thông số VN2000 linh động theo KTT
    vn2000_proj = (
        f"+proj=tmerc +lat_0=0 +lon_0={ktt} +k=0.9999 +x_0=500000 +y_0=0 "
        "+ellps=WGS84 +towgs84=-191.90441429,-39.30318279,-111.45032835,"
        "-0.00928836,0.01975479,-0.00427372,0.252906278 +units=m +no_defs"
    )
    wgs84_proj = "epsg:4326"
    
    if direction == "VN2000 -> WGS84":
        return pyproj.Transformer.from_crs(vn2000_proj, wgs84_proj, always_xy=True)
    else:
        return pyproj.Transformer.from_crs(wgs84_proj, vn2000_proj, always_xy=True)

# --- GIAO DIỆN CHÍNH ---
st.title("🗺️ App Chuyển Tọa Độ VN 2000 ↔ WGS 84")

st.markdown("### 1. Thiết lập thông số")
col_prov, col_dir = st.columns(2)
with col_prov:
    selected_province = st.selectbox("Chọn Tỉnh/Thành phố:", province_names)
    ktt = PROVINCES_KTT[selected_province]
    st.info(f"Kinh tuyến trục: **{ktt}°** (Múi 3°)")
    
with col_dir:
    direction = st.radio("Chọn chiều chuyển đổi:", ("VN2000 -> WGS84", "WGS84 -> VN2000"))

# Đổi nhãn input dựa trên chiều chuyển đổi
label_x = "Cột X (Bắc/Northing)" if direction == "VN2000 -> WGS84" else "Cột Vĩ độ (Latitude)"
label_y = "Cột Y (Đông/Easting)" if direction == "VN2000 -> WGS84" else "Cột Kinh độ (Longitude)"

st.markdown("### 2. Tải dữ liệu lên")
uploaded_file = st.file_uploader("Tải file Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        columns = df.columns.tolist()
        
        st.write("### 3. Ghép nối cột dữ liệu")
        col1, col2 = st.columns(2)
        with col1:
            col_x = st.selectbox(label_x, columns)
        with col2:
            col_y = st.selectbox(label_y, columns)
            
        if st.button("Bắt đầu chuyển đổi", type="primary"):
            transformer = get_transformer(ktt, direction)
            res_x, res_y = [], []
            
            with st.spinner('Đang tính toán...'):
                for index, row in df.iterrows():
                    try:
                        # VN->WGS cần (Easting, Northing). WGS->VN cần (Longitude, Latitude)
                        val_x = float(row[col_x])
                        val_y = float(row[col_y])
                        
                        if direction == "VN2000 -> WGS84":
                            # val_x là Northing, val_y là Easting
                            out_x, out_y = transformer.transform(val_y, val_x) # Trả về Lon, Lat
                        else:
                            # val_x là Lat, val_y là Lon
                            out_x, out_y = transformer.transform(val_y, val_x) # Trả về Easting, Northing
                            
                        res_x.append(out_x)
                        res_y.append(out_y)
                    except Exception:
                        res_x.append(None)
                        res_y.append(None)
            
            # Ghi kết quả vào DataFrame
            if direction == "VN2000 -> WGS84":
                df["KinhDo_WGS84 (Lon)"] = res_x
                df["ViDo_WGS84 (Lat)"] = res_y
            else:
                df["ToaDo_Y_Dong_VN2000"] = res_x
                df["ToaDo_X_Bac_VN2000"] = res_y
                
            st.success("Hoàn tất!")
            st.dataframe(df.head())
            
            # Xuất file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='KetQua')
            
            st.download_button(
                label="📥 Tải file kết quả",
                data=output.getvalue(),
                file_name=f"KetQua_{direction.replace(' -> ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Lỗi: {e}")
