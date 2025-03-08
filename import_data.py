import json
import mysql.connector
from mysql.connector import Error
import os
from gemini_processor import process_character_data, translate_role, format_rating

# Cấu hình hướng xử lý nhân vật
PROCESS_REVERSE = True  # True: xử lý từ cuối lên đầu, False: xử lý từ đầu xuống cuối

def create_connection(host_name, user_name, user_password, db_name):
    """Tạo kết nối đến MySQL"""
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("Kết nối MySQL thành công")
    except Error as e:
        print(f"Lỗi: {e}")
    return connection

def execute_query(connection, query, data=None):
    """Thực thi truy vấn"""
    cursor = connection.cursor()
    try:
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)
        connection.commit()
        return cursor
    except Error as e:
        print(f"Lỗi: {e}")
        return None

def import_data_from_json(json_file_path, connection):
    """Nhập dữ liệu từ file JSON vào MySQL"""
    try:
        # Đọc file JSON
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Kiểm tra cấu trúc dữ liệu
        if 'characters' not in data:
            print("Lỗi: Không tìm thấy mục 'characters' trong file JSON")
            return
        
        # Xóa dữ liệu cũ (tùy chọn)
        execute_query(connection, "DELETE FROM characters")
        
        # Chuẩn bị câu truy vấn
        insert_query = """
        INSERT INTO characters (avatar, name, role, rating_below_6_stars, rating_6_stars)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        # Lấy danh sách nhân vật
        characters = data['characters']
        
        # Đảo ngược danh sách nếu cấu hình yêu cầu
        if PROCESS_REVERSE:
            characters = list(reversed(characters))
            print("Đang xử lý nhân vật theo thứ tự từ cuối lên đầu...")
        else:
            print("Đang xử lý nhân vật theo thứ tự từ đầu xuống cuối...")
        
        # Đếm số lượng nhân vật đã xử lý
        processed_count = 0
        total_count = len(characters)
        
        # Xử lý từng nhân vật
        for character in characters:
            # Bỏ qua mục không hợp lệ
            if character['name'] is None:
                continue
                
            # Chỉ chuyển tên tiếng Nhật sang romanji với Gemini
            processed_data = process_character_data(character)
            
            # Chuẩn bị dữ liệu để chèn vào CSDL
            avatar = character['avatar']
            name = processed_data.get('romanji_name', character['name'])  # Lấy tên romanji, nếu không có thì giữ nguyên
            
            # Dịch vai trò và định dạng đánh giá sử dụng các hàm ánh xạ
            role = translate_role(character['role'])  # Dịch vai trò sang tiếng Việt
            rating_below_6_stars = format_rating(character['rating_below_6_stars'])  # Định dạng đánh giá
            rating_6_stars = format_rating(character['rating_6_stars'])  # Định dạng đánh giá
            
            # Chèn dữ liệu vào CSDL
            data_tuple = (avatar, name, role, rating_below_6_stars, rating_6_stars)
            execute_query(connection, insert_query, data_tuple)
            
            processed_count += 1
            if processed_count % 10 == 0:
                print(f"Đã xử lý {processed_count}/{total_count} nhân vật")
        
        print(f"Hoàn thành! Đã nhập {processed_count} nhân vật vào cơ sở dữ liệu.")
    
    except Exception as e:
        print(f"Lỗi khi nhập dữ liệu: {e}")

def main():
    # Thông tin kết nối đến MySQL
    host = "localhost"
    user = "root"
    password = "tomisakae0000"  # Thay đổi mật khẩu của bạn
    db_name = "priconne"
    
    # Đường dẫn đến file JSON
    json_file_path = "data.json"
    
    # Kết nối đến MySQL
    connection = create_connection(host, user, password, db_name)
    
    if connection:
        # Nhập dữ liệu
        import_data_from_json(json_file_path, connection)
        
        # Đóng kết nối
        connection.close()
        print("Kết nối đã đóng")

if __name__ == "__main__":
    main() 