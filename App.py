import streamlit as st
import pandas as pd
import pyproj
import folium
from streamlit_folium import st_folium
from io import BytesIO
import re # Thư viện để phân tích chuỗi

# --- KHỞI TẠO BỘ NHỚ TẠM (SESSION STATE) CHO VIỆC NHẬP TAY ---
if "manual_points" not in st.session_state:
    st.session_state.manual_points = []

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

st.set_page_config(page_title="Chuyển tọa độ VN2000 ↔ WGS84", layout="wide")

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
st.title("🗺️ App Chuyển Tọa Độ VN 2000 ↔ WGS 84 - Văn phòng Đăng ký đất đai tỉnh Sơn La")

st.markdown("### 1. Thiết lập thông số")
col_prov, col_dir = st.columns(2)
with col_prov:
    selected_label = st.selectbox("Chọn Tỉnh/Thành phố:", formatted_provinces)
    selected_province = selected_label.split(" - ")[0]
    ktt = PROVINCES_KTT[selected_province]
    
with col_dir:
    direction = st.radio("Chọn chiều chuyển đổi:", ("VN2000 -> WGS84", "WGS84 -> VN2000"))

# --- 2. NHẬP DỮ LIỆU ---
st.markdown("### 2. Nhập dữ liệu")

tab1, tab2 = st.tabs(["✍️ Nhập tay nhiều điểm", "📁 Tải file Excel lên"])

df = None 
col_x = ""
col_y = ""

with tab1:
    st.write("Dán hoặc nhập trực tiếp tọa độ (Cách nhau bằng dấu phẩy hoặc khoảng trắng).")
    
    with st.form("form_nhap_tay", clear_on_submit=True):
        if direction == "VN2000 -> WGS84":
            placeholder = "Ví dụ: 2315000.12, 500000.45"
            help_text = "Nhập X (Bắc) trước, Y (Đông) sau"
        else:
            placeholder = "Ví dụ: 20.9086115, 104.6745430"
            help_text = "Nhập Vĩ độ (Lat) trước, Kinh độ (Lon) sau. Có thể copy từ Google Maps."
            
        input_coords = st.text_input("Nhập tọa độ:", placeholder=placeholder, help=help_text)
            
        submit_add = st.form_submit_button("➕ Thêm điểm vào danh sách")
        
        if submit_add:
            if input_coords.strip():
                try:
                    # Dùng regex để tách số bằng dấu phẩy hoặc khoảng trắng
                    # Chấp nhận cả số âm, số thập phân
                    parts = re.findall(r'-?\d+\.?\d*', input_coords)
                    
                    if len(parts) >= 2:
                        val_1 = float(parts[0])
                        val_2 = float(parts[1])
                        
                        st.session_state.manual_points.append({
                            "X_input": val_1,
                            "Y_input": val_2
                        })
                        st.success(f"Đã thêm điểm: ({val_1}, {val_2})")
                    else:
                        st.error("Không tìm thấy đủ 2 giá trị tọa độ. Vui lòng kiểm tra lại.")
                except ValueError:
                    st.error("Dữ liệu nhập vào không phải là số hợp lệ.")
            else:
                st.warning("Vui lòng nhập tọa độ trước khi bấm Thêm.")

    # Hiển thị danh sách nếu đã có điểm
    if st.session_state.manual_points:
        st.markdown(f"**Danh sách đang có {len(st.session_state.manual_points)} điểm chờ chuyển đổi:**")
        df_manual = pd.DataFrame(st.session_state.manual_points)
        df_manual.index += 1
        
        # Đổi tên cột hiển thị cho dễ nhìn tùy theo chiều chuyển đổi
        if direction == "VN2000 -> WGS84":
            df_manual.columns = ["X (Bắc/Northing)", "Y (Đông/Easting)"]
        else:
            df_manual.columns = ["Vĩ độ (Latitude)", "Kinh độ (Longitude)"]
            
        st.dataframe(df_manual)
        
        col_btn_chuyen, col_btn_xoa = st.columns([1, 4])
        with col_btn_chuyen:
            if st.button("🚀 Chuyển đổi danh sách", type="primary", key="btn_chuyen_tay"):
                # Trả lại tên cột nội bộ để xử lý đồng nhất với file upload
                df = pd.DataFrame(st.session_state.manual_points) 
                col_x = "X_input"
                col_y = "Y_input"
        with col_btn_xoa:
            if st.button("🗑️ Xóa trắng danh sách"):
                st.session_state.manual_points = []
                st.rerun()

with tab2:
    uploaded_file = st.file_uploader("Tải file Excel (.xlsx) để xử lý hàng loạt", type=["xlsx"])
    if uploaded_file is not None:
        try:
            df_upload = pd.read_excel(uploaded_file)
            columns = df_upload.columns.tolist()
            
            st.write("**Ghép nối cột dữ liệu từ file Excel**")
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                label_x = "Cột X (Bắc/Northing)" if direction == "VN2000 -> WGS84" else "Cột Vĩ độ (Lat)"
                col_sel_x = st.selectbox(label_x, columns)
            with col_sel2:
                label_y = "Cột Y (Đông/Easting)" if direction == "VN2000 -> WGS84" else "Cột Kinh độ (Lon)"
                col_sel_y = st.selectbox(label_y, columns)
                
            if st.button("Bắt đầu chuyển đổi file", type="primary", key="btn_file"):
                df = df_upload.copy()
                col_x = col_sel_x
                col_y = col_sel_y
        except Exception as e:
            st.error(f"Không thể đọc file: {e}")

# --- XỬ LÝ CHUYỂN ĐỔI CHUNG ---
if df is not None:
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
        
    map_data = map_data.dropna()
    st.success("Hoàn tất tính toán!")
    
    # --- HIỂN THỊ KẾT QUẢ VÀ BẢN ĐỒ ---
    st.markdown("---")
    col_map, col_data = st.columns([6, 4])
    
    with col_map:
        st.markdown("### Bản đồ định vị")
        if not map_data.empty:
            m = folium.Map(tiles=None)
            
            folium.TileLayer(
                tiles='http://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Vệ tinh',
                max_zoom=20,
                control=True
            ).add_to(m)
            
            folium.TileLayer(
                tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Đường phố',
                max_zoom=20,
                control=True
            ).add_to(m)

            for i, row in map_data.iterrows():
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=6,
                    popup=f"<b>Điểm {i+1}</b><br>Lat: {row['lat']:.6f}<br>Lon: {row['lon']:.6f}",
                    color="#0052cc",
                    fill=True,
                    fill_color="#3388ff",
                    fill_opacity=0.8,
                    weight=2
                ).add_to(m)
            
            min_lat = map_data["lat"].min()
            max_lat = map_data["lat"].max()
            min_lon = map_data["lon"].min()
            max_lon = map_data["lon"].max()
            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
            
            folium.LayerControl().add_to(m)
            st_folium(m, width="100%", height=500, returned_objects=[])
        else:
            st.warning("Không có dữ liệu tọa độ hợp lệ để vẽ bản đồ.")
    
    with col_data:
        st.markdown("### Dữ liệu Kết quả")
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
