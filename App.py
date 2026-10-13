import streamlit as st
import pandas as pd
import pyproj
import folium
from streamlit_folium import st_folium
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

formatted_provinces = [f"{prov} - {ktt}°" for prov, ktt in PROVINCES_KTT.items()]
sonla_label = f"Sơn La - {PROVINCES_KTT['Sơn La']}°"
formatted_provinces.remove(sonla_label)
formatted_provinces.insert(0, sonla_label)

st.set_page_config(page_title="Chuyển tọa độ VN2000 ↔ WGS84", layout="wide") # Mở rộng giao diện để xem map dễ hơn

# --- HÀM TẠO BỘ CHUYỂN ĐỔI ---
@st.cache_resource
def get_transformer(ktt, direction):
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
    selected_label = st.selectbox("Chọn Tỉnh/Thành phố:", formatted_provinces)
    selected_province = selected_label.split(" - ")[0]
    ktt = PROVINCES_KTT[selected_province]
    
with col_dir:
    direction = st.radio("Chọn chiều chuyển đổi:", ("VN2000 -> WGS84", "WGS84 -> VN2000"))

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
                        val_x = float(row[col_x])
                        val_y = float(row[col_y])
                        
                        if direction == "VN2000 -> WGS84":
                            out_x, out_y = transformer.transform(val_y, val_x)
                        else:
                            out_x, out_y = transformer.transform(val_y, val_x)
                            
                        res_x.append(out_x)
                        res_y.append(out_y)
                    except Exception:
                        res_x.append(None)
                        res_y.append(None)
            
            # Lưu kết quả
            map_data = pd.DataFrame()
            if direction == "VN2000 -> WGS84":
                df["KinhDo_WGS84 (Lon)"] = res_x
                df["ViDo_WGS84 (Lat)"] = res_y
                map_data["lon"] = res_x
                map_data["lat"] = res_y
            else:
                df["ToaDo_Y_Dong_VN2000"] = res_x
                df["ToaDo_X_Bac_VN2000"] = res_y
                map_data["lon"] = pd.to_numeric(df[col_y], errors='coerce')
                map_data["lat"] = pd.to_numeric(df[col_x], errors='coerce')
                
            # Lọc bỏ các điểm lỗi
            map_data = map_data.dropna()
            
            st.success("Hoàn tất tính toán!")
            
            # Chia layout: Bên trái Bản đồ - Bên phải Bảng dữ liệu
            col_map, col_data = st.columns([6, 4])
            
            with col_map:
                st.markdown("### 4. Bản đồ định vị")
                if not map_data.empty:
                    # Lấy tọa độ trung tâm để hiển thị bản đồ
                    center_lat = map_data["lat"].mean()
                    center_lon = map_data["lon"].mean()
                    
                    # Khởi tạo bản đồ Folium
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
                    
                    # Thêm các lớp (Layers) Bản đồ Google
                    folium.TileLayer(
                        tiles='http://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}',
                        attr='Google Satellite',
                        name='Google Vệ tinh',
                        max_zoom=20
                    ).add_to(m)
                    
                    folium.TileLayer(
                        tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
                        attr='Google Maps',
                        name='Google Đường phố',
                        max_zoom=20
                    ).add_to(m)
                    
                    folium.TileLayer(
                        tiles='http://mt0.google.com/vt/lyrs=p&hl=en&x={x}&y={y}&z={z}',
                        attr='Google Terrain',
                        name='Google Địa hình',
                        max_zoom=20
                    ).add_to(m)

                    # Đánh dấu các điểm lên bản đồ
                    for i, row in map_data.iterrows():
                        folium.Marker(
                            [row["lat"], row["lon"]], 
                            popup=f"Điểm {i+1}<br>Lat: {row['lat']:.6f}<br>Lon: {row['lon']:.6f}"
                        ).add_to(m)
                    
                    # Thêm nút chọn lớp (Layer Control) ở góc trên bên phải
                    folium.LayerControl().add_to(m)
                    
                    # Hiển thị bản đồ trên Streamlit
                    st_folium(m, width="100%", height=500, returned_objects=[])
                else:
                    st.warning("Không có dữ liệu tọa độ hợp lệ để vẽ bản đồ.")
            
            with col_data:
                st.markdown("### 5. Tải File & Xem trước")
                st.dataframe(df.head(10))
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='KetQua')
                
                st.download_button(
                    label="📥 Tải file Excel kết quả",
                    data=output.getvalue(),
                    file_name=f"KetQua_{direction.replace(' -> ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    except Exception as e:
        st.error(f"Lỗi hệ thống hoặc định dạng file: {e}")
