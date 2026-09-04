import streamlit as st
import pandas as pd
import pyproj
from io import BytesIO

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Chuyển tọa độ VN2000 - WGS84, VPĐKĐĐ tỉnh Sơn La", layout="centered")

# --- HÀM CHUYỂN ĐỔI CHUYÊN MÔN ---
@st.cache_resource
def get_transformer():
    # Tham số VN2000 cho Sơn La (KTT 104, Múi 3 độ)
    vn2000_sonla_proj = (
        "+proj=tmerc +lat_0=0 +lon_0=104 +k=0.9999 +x_0=500000 +y_0=0 "
        "+ellps=WGS84 +towgs84=-191.90441429,-39.30318279,-111.45032835,"
        "-0.00928836,0.01975479,-0.00427372,0.252906278 +units=m +no_defs"
    )
    # Khởi tạo bộ chuyển đổi sang WGS 84 (EPSG:4326)
    return pyproj.Transformer.from_crs(vn2000_sonla_proj, "epsg:4326", always_xy=True)

def convert_df(df, col_x, col_y):
    transformer = get_transformer()
    lons, lats = [], []
    
    for index, row in df.iterrows():
        try:
            # Trắc địa VN: Y là tọa độ Đông (Easting), X là tọa độ Bắc (Northing).
            # Công cụ chuẩn quốc tế nhận (Easting, Northing)
            easting = float(row[col_y])
            northing = float(row[col_x])
            lon, lat = transformer.transform(easting, northing)
            lons.append(lon)
            lats.append(lat)
        except Exception:
            lons.append(None)
            lats.append(None)
    
    # Thêm 2 cột kết quả vào file Excel
    df["KinhDo_WGS84 (Longitude)"] = lons
    df["ViDo_WGS84 (Latitude)"] = lats
    return df

# --- GIAO DIỆN NGƯỜI DÙNG ---
st.title("🗺️ Ứng dụng chuyển HTĐ VN 2000 sang WGS 84 - VPĐKĐĐ tỉnh Sơn La")
st.markdown("Hệ quy chiếu mặc định: **VN 2000 Tỉnh Sơn La (Kinh tuyến trục 104°00', Múi 3°)**")

# 1. Nút upload file
uploaded_file = st.file_uploader("Tải lên file Excel chứa danh sách điểm (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 2. Đọc và hiển thị dữ liệu
        df = pd.read_excel(uploaded_file)
        st.success("Đã đọc file thành công! Bản xem trước:")
        st.dataframe(df.head(3)) # Hiện 3 dòng đầu
        
        columns = df.columns.tolist()
        st.write("### Cấu hình cột dữ liệu")
        
        # 3. Cho phép người dùng chọn cột X, Y tương ứng từ file của họ
        col1, col2 = st.columns(2)
        with col1:
            col_x = st.selectbox("Cột chứa Tọa độ X (Trục Bắc/Northing):", columns)
        with col2:
            col_y = st.selectbox("Cột chứa Tọa độ Y (Trục Đông/Easting):", columns)
        
        # 4. Xử lý chuyển đổi khi bấm nút
        if st.button("Bắt đầu chuyển đổi", type="primary"):
            with st.spinner('Đang tính toán chuyển đổi...'):
                result_df = convert_df(df.copy(), col_x, col_y)
            
            st.success("Chuyển đổi hoàn tất!")
            st.write("Xem trước kết quả:")
            st.dataframe(result_df.head(5))
            
            # 5. Tạo file tải về
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                result_df.to_excel(writer, index=False, sheet_name='KetQua_WGS84')
            
            st.download_button(
                label="📥 Tải file kết quả về máy",
                data=output.getvalue(),
                file_name="KetQua_ChuyenToaDo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Có lỗi xảy ra: {e}")